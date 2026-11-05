"""Optional ModelAdmin extensions.

Plain ``admin.ModelAdmin`` classes render with the design system as-is.
``DSModelAdmin`` only adds opt-in capabilities:

* **object actions** — per-object operations (buttons on the change form and,
  optionally, a column in the change list), permission-checked, CSRF-protected,
  logged to the admin history, with an optional confirmation step::

      class ProductAdmin(DSModelAdmin):
          object_actions = ["publish", "archive"]
          list_object_actions = True

          @object_action(description="Publish", permissions=["change"], tone="success", icon="check")
          def publish(self, request, obj):
              obj.status = "active"; obj.save()
              self.message_user(request, f"{obj} published.")

          @object_action(description="Archive", permissions=["change"], confirm="Archive this product?",
                         tone="warning")
          def archive(self, request, obj):
              ...
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass

from django.contrib import admin, messages
from django.contrib.admin.utils import quote, unquote
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.http import url_has_allowed_host_and_scheme, urlencode

_current_request = contextvars.ContextVar("dsadmin_request", default=None)

BUTTON_TONES = {
    "neutral": "d-btn d-btn-sm",
    "primary": "d-btn d-btn-sm d-btn-primary",
    "secondary": "d-btn d-btn-sm d-btn-secondary",
    "success": "d-btn d-btn-sm d-btn-success",
    "warning": "d-btn d-btn-sm d-btn-warning",
    "error": "d-btn d-btn-sm d-btn-error",
    "ghost": "d-btn d-btn-sm d-btn-ghost",
}


def object_action(description=None, *, permissions=None, confirm=None, tone="neutral", icon=None):
    """Mark a ``ModelAdmin`` method ``(self, request, obj)`` as an object action.

    ``permissions`` works like Django admin actions: each name ``"x"`` requires
    ``has_x_permission(request, obj)`` on the ModelAdmin to be true.
    ``confirm`` (text) adds a confirmation step.
    The method may return an ``HttpResponse``; otherwise the user is redirected
    back to the change form.
    """

    def decorator(func):
        func.ds_object_action = {
            "description": description or func.__name__.replace("_", " ").capitalize(),
            "permissions": list(permissions or []),
            "confirm": confirm,
            "tone": tone,
            "icon": icon,
        }
        return func

    return decorator


@dataclass
class BoundObjectAction:
    name: str
    description: str
    url: str
    confirm: str | None
    tone: str
    icon: str | None

    @property
    def button_class(self):
        return BUTTON_TONES.get(self.tone, BUTTON_TONES["neutral"])


class DSModelAdminMixin:
    object_actions: list[str] | tuple = ()
    list_object_actions = False

    # -- discovery -----------------------------------------------------------
    def _object_action_func(self, name):
        func = getattr(self, name, None)
        if func is None or not hasattr(func, "ds_object_action"):
            return None
        return func

    def _object_action_allowed(self, request, func, obj):
        for perm in func.ds_object_action["permissions"]:
            checker = getattr(self, f"has_{perm}_permission", None)
            if checker is None or not checker(request, obj):
                return False
        return True

    def get_object_actions(self, request, obj):
        info = self.opts.app_label, self.opts.model_name
        out = []
        for name in self.object_actions:
            func = self._object_action_func(name)
            if func is None or not self._object_action_allowed(request, func, obj):
                continue
            meta = func.ds_object_action
            out.append(
                BoundObjectAction(
                    name=name,
                    description=str(meta["description"]),
                    url=reverse(
                        f"{self.admin_site.name}:%s_%s_object_action" % info, args=[quote(obj.pk), name]
                    ),
                    confirm=meta["confirm"],
                    tone=meta["tone"],
                    icon=meta["icon"],
                )
            )
        return out

    # -- urls / views --------------------------------------------------------
    def get_urls(self):
        info = self.opts.app_label, self.opts.model_name
        custom = [
            path(
                "<path:object_id>/action/<str:action>/",
                self.admin_site.admin_view(self.object_action_view),
                name="%s_%s_object_action" % info,
            )
        ]
        return custom + super().get_urls()

    def object_action_view(self, request, object_id, action):
        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            raise Http404
        func = self._object_action_func(action)
        if func is None or action not in self.object_actions:
            raise Http404
        if not self._object_action_allowed(request, func, obj):
            raise PermissionDenied
        meta = func.ds_object_action
        change_url = reverse(
            f"{self.admin_site.name}:{self.opts.app_label}_{self.opts.model_name}_change", args=[quote(obj.pk)]
        )
        next_url = request.POST.get("next") or request.GET.get("next")
        if not next_url or not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            next_url = change_url
        if request.method == "GET":
            if not meta["confirm"]:
                return HttpResponseNotAllowed(["POST"])
            context = {
                **self.admin_site.each_context(request),
                "title": meta["description"],
                "opts": self.opts,
                "object": obj,
                "action_name": action,
                "confirm_text": meta["confirm"],
                "tone_class": BUTTON_TONES.get(meta["tone"], BUTTON_TONES["neutral"]).replace("d-btn-sm", ""),
                "next_url": next_url,
                "change_url": change_url,
                "has_view_permission": self.has_view_permission(request, obj),
            }
            return TemplateResponse(request, "dsadmin/object_action_confirm.html", context)
        if request.method != "POST":
            return HttpResponseNotAllowed(["GET", "POST"])
        response = func(request, obj)
        self.log_change(request, obj, [{"action": {"name": str(meta["description"])}}])
        if response is not None:
            return response
        if not messages.get_messages(request):
            self.message_user(request, f"{meta['description']}: {obj}", messages.SUCCESS)
        return HttpResponseRedirect(next_url)

    # -- rendering hooks -----------------------------------------------------
    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        if obj is not None and not add:
            context["ds_object_actions"] = self.get_object_actions(request, obj)
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)

    def changelist_view(self, request, extra_context=None):
        token = _current_request.set(request)
        try:
            response = super().changelist_view(request, extra_context)
            if (
                self.list_object_actions
                and hasattr(response, "render")
                and not getattr(response, "is_rendered", True)
            ):
                response.render()  # render while the request is bound for ds_row_actions
            return response
        finally:
            _current_request.reset(token)

    def get_list_display(self, request):
        display = list(super().get_list_display(request))
        if self.list_object_actions and self.object_actions and "ds_row_actions" not in display:
            display.append("ds_row_actions")
        return display

    @admin.display(description="Actions")
    def ds_row_actions(self, obj):
        request = _current_request.get()
        if request is None:
            return ""
        actions = self.get_object_actions(request, obj)
        if not actions:
            return ""
        # The change list table already sits inside <form id="changelist-form">,
        # so row buttons target a sibling form (#ds-row-action-form, rendered by
        # admin/change_list.html) through the HTML `form`/`formaction` attributes.
        # Actions with a confirmation link to their confirmation page instead.
        parts = []
        for a in actions:
            if a.confirm:
                parts.append(
                    format_html('<a class="{} d-btn-xs" href="{}?{}">{}</a>', a.button_class, a.url,
                                urlencode({"next": request.get_full_path()}), a.description)
                )
            else:
                parts.append(
                    format_html(
                        '<button type="submit" form="ds-row-action-form" formaction="{}" class="{} d-btn-xs">{}</button>',
                        a.url, a.button_class, a.description,
                    )
                )
        return format_html('<div class="flex flex-wrap gap-1">{}</div>', format_html_join("", "{}", ((p,) for p in parts)))


class DSModelAdmin(DSModelAdminMixin, admin.ModelAdmin):
    """``admin.ModelAdmin`` + dsadmin extensions. Fully compatible with ModelAdmin."""


class DSStackedInline(admin.StackedInline):
    pass


class DSTabularInline(admin.TabularInline):
    pass
