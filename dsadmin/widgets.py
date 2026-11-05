"""Dashboard widgets.

A dashboard is a list of widgets (or ``callable(request) -> list``)::

    from dsadmin import widgets as w

    site = DSAdminSite(name="admin", dashboard=[
        w.ModelCountCard("catalog.product", icon="box"),
        w.MetricCard("Revenue (30d)", value=lambda request: "$12,400", tone="success"),
        w.BarList("Products by status", data=status_breakdown),
        w.RecentActions(width=2),
        w.AppList(width=4),
    ])

Widgets render server-side with design-system components (``d-card``,
``d-stat``, ``d-table`` …). A widget that raises while rendering is replaced by
an error card instead of breaking the page.
"""

from __future__ import annotations

import logging

from django.apps import apps
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe

from .navigation import _check_permission

logger = logging.getLogger("dsadmin")

# Literal class names so Tailwind keeps them in the compiled CSS.
WIDTH_CLASSES = {
    1: "md:col-span-1",
    2: "md:col-span-2",
    3: "md:col-span-2 xl:col-span-3",
    4: "md:col-span-2 xl:col-span-4",
}
TONE_TEXT = {
    "primary": "text-primary",
    "secondary": "text-secondary",
    "accent": "text-accent",
    "info": "text-info",
    "success": "text-success",
    "warning": "text-warning",
    "error": "text-error",
    "neutral": "text-base-content",
}
TONE_PROGRESS = {
    "primary": "d-progress-primary",
    "secondary": "d-progress-secondary",
    "accent": "d-progress-accent",
    "info": "d-progress-info",
    "success": "d-progress-success",
    "warning": "d-progress-warning",
    "error": "d-progress-error",
    "neutral": "",
}


def _call(value, request):
    return value(request) if callable(value) else value


class Widget:
    template_name = "dsadmin/widgets/card.html"
    title = ""
    width = 1

    def __init__(self, title=None, *, width=None, permission=None, description=None, template_name=None):
        if title is not None:
            self.title = title
        if width is not None:
            self.width = width
        if template_name is not None:
            self.template_name = template_name
        self.permission = permission
        self.description = description

    def is_visible(self, request, site):
        return _check_permission(request, self.permission)

    def get_context(self, request, site):
        return {}

    def render(self, request, site):
        if not self.is_visible(request, site):
            return ""
        try:
            context = {
                "widget": self,
                "title": _call(self.title, request),
                "description": _call(self.description, request),
                "width_class": WIDTH_CLASSES.get(self.width, WIDTH_CLASSES[1]),
                "request": request,
            }
            extra = self.get_context(request, site)
            if extra is None:  # widget opted out at render time
                return ""
            context.update(extra)
            return render_to_string(self.template_name, context, request=request)
        except Exception as exc:  # noqa: BLE001 — a broken widget must not break the dashboard
            logger.exception("dsadmin widget %r failed", self)
            if getattr(settings, "DEBUG", False) and getattr(settings, "DSADMIN_RAISE_WIDGET_ERRORS", False):
                raise
            return render_to_string(
                "dsadmin/widgets/error.html",
                {
                    "title": str(self.title) if not callable(self.title) else "",
                    "width_class": WIDTH_CLASSES.get(self.width, WIDTH_CLASSES[1]),
                    "detail": f"{type(exc).__name__}: {exc}" if settings.DEBUG else "",
                },
                request=request,
            )

    def __repr__(self):
        return f"<{type(self).__name__} {self.title!r}>"


class MetricCard(Widget):
    """A single number. ``value``/``delta`` may be callables taking ``request``."""

    template_name = "dsadmin/widgets/metric.html"

    def __init__(self, title, value, *, delta=None, delta_tone=None, icon=None, url=None, tone="primary", **kw):
        super().__init__(title, **kw)
        self.value, self.delta, self.delta_tone, self.icon, self.url, self.tone = value, delta, delta_tone, icon, url, tone

    def get_context(self, request, site):
        delta = _call(self.delta, request)
        delta_tone = self.delta_tone
        if delta_tone is None and isinstance(delta, (int, float)):
            delta_tone = "success" if delta >= 0 else "error"
        return {
            "value": _call(self.value, request),
            "delta": delta,
            "delta_tone_class": TONE_TEXT.get(delta_tone or "neutral"),
            "icon": self.icon,
            "url": _call(self.url, request),
            "tone_class": TONE_TEXT.get(self.tone, "text-primary"),
        }


class ModelCountCard(MetricCard):
    """Row count for a registered model; hidden when the user cannot view it."""

    def __init__(self, model, title=None, *, queryset=None, icon="list", **kw):
        self.model_label = model
        self.queryset = queryset
        super().__init__(title, value=None, icon=icon, **kw)

    def _model_admin(self, site):
        model = apps.get_model(self.model_label)
        return model, site._registry.get(model)

    def is_visible(self, request, site):
        if not super().is_visible(request, site):
            return False
        model, ma = self._model_admin(site)
        return ma is not None and ma.has_view_or_change_permission(request)

    def get_context(self, request, site):
        model, ma = self._model_admin(site)
        qs = self.queryset(request) if callable(self.queryset) else ma.get_queryset(request)
        if self.title is None or self.title == "":
            self.title = model._meta.verbose_name_plural.capitalize()
        ctx = super().get_context(request, site)
        ctx["title"] = self.title
        ctx["value"] = qs.count()
        try:
            ctx["url"] = ctx["url"] or reverse(f"{site.name}:{model._meta.app_label}_{model._meta.model_name}_changelist")
        except NoReverseMatch:
            pass
        return ctx


class BarList(Widget):
    """Horizontal bars (label, value) drawn with ``d-progress`` — no JavaScript."""

    template_name = "dsadmin/widgets/bar_list.html"

    def __init__(self, title, data, *, tone="primary", value_format="{}", empty_text="No data yet.", **kw):
        super().__init__(title, **kw)
        self.data, self.tone, self.value_format, self.empty_text = data, tone, value_format, empty_text

    def get_context(self, request, site):
        rows = list(_call(self.data, request) or [])
        top = max((float(v) for _, v in rows), default=0) or 1
        return {
            "rows": [
                {"label": label, "value": value, "display": self.value_format.format(value), "pct": round(float(value) * 100 / top)}
                for label, value in rows
            ],
            "progress_class": TONE_PROGRESS.get(self.tone, ""),
            "empty_text": self.empty_text,
        }


class TableWidget(Widget):
    """Small table. ``rows`` is ``callable(request) -> iterable of sequences``.

    Cells may be strings or ``(text, url)`` tuples.
    """

    template_name = "dsadmin/widgets/table.html"

    def __init__(self, title, columns, rows, *, empty_text="Nothing here yet.", **kw):
        super().__init__(title, **kw)
        self.columns, self.rows, self.empty_text = columns, rows, empty_text

    def get_context(self, request, site):
        rows = []
        for row in _call(self.rows, request) or []:
            cells = []
            for cell in row:
                if isinstance(cell, tuple) and len(cell) == 2:
                    cells.append({"text": cell[0], "url": cell[1]})
                else:
                    cells.append({"text": cell, "url": None})
            rows.append(cells)
        return {"columns": self.columns, "rows": rows, "empty_text": self.empty_text}


class RecentActions(Widget):
    template_name = "dsadmin/widgets/recent_actions.html"
    title = "Recent actions"

    def __init__(self, title=None, *, limit=8, mine=True, **kw):
        super().__init__(title, **kw)
        self.limit, self.mine = limit, mine

    def get_context(self, request, site):
        from django.contrib.admin.models import LogEntry

        qs = LogEntry.objects.select_related("content_type", "user")
        if self.mine:
            qs = qs.filter(user=request.user)
        return {"entries": list(qs[: self.limit])}


class AppList(Widget):
    """The classic admin app/model index, as cards."""

    template_name = "dsadmin/widgets/app_list.html"
    title = "Applications"
    width = 4

    def get_context(self, request, site):
        return {"app_list": site.get_app_list(request)}


class QuickActions(Widget):
    """Shortcut buttons. Items: ``{"label", "url"|"view"|"add": "app.Model", "icon"}``."""

    template_name = "dsadmin/widgets/quick_actions.html"
    title = "Quick actions"

    def __init__(self, items, title=None, **kw):
        super().__init__(title, **kw)
        self.items = items

    def get_context(self, request, site):
        out = []
        for item in self.items:
            if not _check_permission(request, item.get("permission")):
                continue
            url = _call(item.get("url"), request)
            if "add" in item:
                model = apps.get_model(item["add"])
                ma = site._registry.get(model)
                if ma is None or not ma.has_add_permission(request):
                    continue
                url = reverse(f"{site.name}:{model._meta.app_label}_{model._meta.model_name}_add")
            elif "view" in item:
                view = item["view"] if ":" in item["view"] else f"{site.name}:{item['view']}"
                url = reverse(view)
            if url:
                out.append({"label": item["label"], "url": url, "icon": item.get("icon", "plus")})
        if not out:
            return None
        return {"items": out}


class TemplateWidget(Widget):
    """Render any template; ``context`` is a dict or ``callable(request) -> dict``."""

    def __init__(self, template_name, title="", *, context=None, **kw):
        super().__init__(title, template_name=template_name, **kw)
        self.context = context

    def get_context(self, request, site):
        return _call(self.context, request) or {}


class IslandWidget(Widget):
    """Mount an independent JS component (see ``{% ds_island %}``) inside a card."""

    template_name = "dsadmin/widgets/island.html"

    def __init__(self, title, *, name, src, props=None, **kw):
        super().__init__(title, **kw)
        self.name, self.src, self.props = name, src, props

    def get_context(self, request, site):
        return {"island_name": self.name, "island_src": self.src, "island_props": _call(self.props, request) or {}}


def render_dashboard(widgets, request, site):
    widgets = _call(widgets, request) or []
    html = [w.render(request, site) for w in widgets]
    return mark_safe("".join(h for h in html if h))


def default_dashboard(site):
    return [AppList(width=3), RecentActions(width=1)]


__all__ = [
    "Widget",
    "MetricCard",
    "ModelCountCard",
    "BarList",
    "TableWidget",
    "RecentActions",
    "AppList",
    "QuickActions",
    "TemplateWidget",
    "IslandWidget",
]
