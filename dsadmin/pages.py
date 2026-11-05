"""Custom admin pages rendered inside the admin layout.

Class-based::

    from dsadmin import PageView

    @site.register_page(slug="reports", title="Reports", icon="chart", group="Insights",
                        permission="catalog.view_product")
    class ReportsPage(PageView):
        template_name = "myapp/reports.html"   # extends "dsadmin/page.html"

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx["rows"] = ...
            return ctx

Function-based::

    @site.register_page(slug="health", title="Health")
    def health(request, site):
        return site.render_page(request, "myapp/health.html", {"ok": True}, title="Health")

Pages are always wrapped in ``AdminSite.admin_view`` (staff login, never
cached, CSRF as usual) and then checked against ``permission``.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.views.generic import TemplateView

from .navigation import _check_permission


class PageView(TemplateView):
    """Base class for class-based admin pages.

    ``site`` and ``page`` are injected by ``DSAdminSite.register_page``.
    Templates should extend ``"dsadmin/page.html"``.
    """

    site = None
    page = None
    template_name = "dsadmin/page.html"
    title = None
    subtitle = None

    def get_title(self):
        return self.title or (self.page.title if self.page else "")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.site.each_context(self.request))
        context.update(
            title=self.get_title(),
            subtitle=self.subtitle,
            ds_page=self.page,
        )
        return context


@dataclass
class AdminPage:
    slug: str
    title: str
    view: Any
    icon: str | None = "file"
    group: str | None = None
    permission: Any = None
    order: int = 0
    in_navigation: bool = True
    path: str | None = None  # URL path below the site root; default "p/<slug>/"
    extra: dict = field(default_factory=dict)

    @property
    def url_name(self):
        return f"page_{self.slug}"

    def url(self, site):
        return reverse(f"{site.name}:{self.url_name}")

    def has_permission(self, request):
        return _check_permission(request, self.permission)

    def build_view(self, site) -> Callable:
        page = self
        view = self.view
        if inspect.isclass(view) and issubclass(view, PageView):
            inner = view.as_view(site=site, page=page)
        elif callable(view):
            def inner(request, *args, **kwargs):
                return view(request, site, *args, **kwargs)
        else:
            raise ImproperlyConfigured(f"Page {self.slug!r}: view must be a PageView subclass or callable")

        def guarded(request, *args, **kwargs):
            if not page.has_permission(request):
                raise PermissionDenied
            return inner(request, *args, **kwargs)

        guarded.__name__ = f"dsadmin_page_{self.slug}"
        return site.admin_view(guarded)

    def urlpattern(self, site):
        route = self.path or f"p/{self.slug}/"
        return path(route, self.build_view(site), name=self.url_name)


def render_page(site, request, template_name, context=None, *, title="", subtitle=None, status=200):
    ctx = site.each_context(request)
    ctx.update(title=title, subtitle=subtitle)
    ctx.update(context or {})
    return TemplateResponse(request, template_name, ctx, status=status)
