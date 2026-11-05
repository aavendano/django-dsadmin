"""Template tags for dsadmin templates and for project templates that want
design-system admin components.

    {% load dsadmin %}
    {% dsadmin_ui as ui %}            layout context (works on any AdminSite)
    {% ds_field bound_field %}        render a form field with d-* classes
    {% ds_icon "box" %}               inline icon from the sprite
    {% ds_badge "Active" "success" %}
    {% ds_island "name" src="app/island.js" props=some_dict %}
    {% ds_nonce %}                    CSP nonce attribute when available
"""

from __future__ import annotations

import copy
import json

from django import forms, template
from django.forms.boundfield import BoundField
from django.contrib.admin import widgets as admin_widgets
from django.contrib.admin.views.main import PAGE_VAR
from django.templatetags.static import static
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from ..display import BADGE_TONES
from ..ui import build_ui

register = template.Library()


# --------------------------------------------------------------------------- layout
@register.simple_tag(takes_context=True)
def dsadmin_ui(context):
    ui = context.get("dsadmin")
    if ui:
        return ui
    request = context.get("request")
    return build_ui(
        request,
        site=None,
        available_apps=context.get("available_apps"),
        has_permission=bool(context.get("has_permission")),
    )


@register.simple_tag(takes_context=True)
def ds_nonce(context):
    """``nonce="…"`` when Django's CSP nonce is available (Django 6 ``csp`` processor
    or a ``csp_nonce`` context variable)."""
    nonce = context.get("csp_nonce")
    if not nonce:
        request = context.get("request")
        nonce = getattr(request, "_csp_nonce", None) or getattr(request, "csp_nonce", None)
    if not nonce:
        return ""
    return format_html(' nonce="{}"', str(nonce))


@register.simple_tag(takes_context=True)
def ds_media(context, media):
    """Render ``forms.Media`` adding the CSP nonce to each tag if present."""
    if not media:
        return ""
    html = str(media)
    nonce = ds_nonce(context)
    if nonce:
        html = html.replace("<script ", f"<script{nonce} ").replace("<link ", f"<link{nonce} ")
    return mark_safe(html)


@register.simple_tag
def ds_icon(name, css_class="size-5", label=None):
    if label:
        return format_html(
            '<svg class="ds-icon {}" role="img" aria-label="{}"><use href="#ds-i-{}"></use></svg>', css_class, label, name
        )
    return format_html('<svg class="ds-icon {}" aria-hidden="true" focusable="false"><use href="#ds-i-{}"></use></svg>', css_class, name)


@register.simple_tag
def ds_badge(text, tone="neutral"):
    return format_html('<span class="{} theme-label-bold">{}</span>', BADGE_TONES.get(tone, BADGE_TONES["neutral"]), text)


MESSAGE_TONES = {
    "debug": ("d-alert", "info"),
    "info": ("d-alert d-alert-info", "info"),
    "success": ("d-alert d-alert-success", "success"),
    "warning": ("d-alert d-alert-warning", "alert"),
    "error": ("d-alert d-alert-error", "error"),
}


@register.filter
def ds_message_class(tags):
    for tag in str(tags or "").split():
        if tag in MESSAGE_TONES:
            return MESSAGE_TONES[tag][0]
    return MESSAGE_TONES["info"][0]


@register.filter
def ds_message_icon(tags):
    for tag in str(tags or "").split():
        if tag in MESSAGE_TONES:
            return MESSAGE_TONES[tag][1]
    return "info"


# --------------------------------------------------------------------------- forms
# Literal class strings (kept literal so Tailwind's scanner compiles them).
INPUT = "d-input w-full max-w-xl"
INPUT_SHORT = "d-input w-full max-w-48"
SELECT = "d-select w-full max-w-xl"
MULTI = "d-select ds-select-multiple w-full max-w-xl"
TEXTAREA = "d-textarea w-full max-w-3xl min-h-28"
CHECKBOX = "d-checkbox"
CHECKBOX_MULTI = "d-checkbox d-checkbox-sm"
RADIO = "d-radio d-radio-sm"
FILE = "d-file-input w-full max-w-xl"
ERROR_CLASSES = {
    INPUT: "d-input-error",
    INPUT_SHORT: "d-input-error",
    SELECT: "d-select-error",
    MULTI: "d-select-error",
    TEXTAREA: "d-textarea-error",
    CHECKBOX: "d-checkbox-error",
    CHECKBOX_MULTI: "d-checkbox-error",
    RADIO: "d-radio-error",
    FILE: "d-file-input-error",
}


def widget_class(widget):
    """Design-system class for a (leaf) widget, or None to leave it alone."""
    if isinstance(widget, forms.HiddenInput) or getattr(widget, "input_type", None) == "hidden":
        return None
    if isinstance(widget, (admin_widgets.AutocompleteSelect, admin_widgets.AutocompleteSelectMultiple)):
        return None  # select2 replaces the element
    if isinstance(widget, admin_widgets.FilteredSelectMultiple):
        return None  # SelectFilter2 builds its own UI (styled in dsadmin.css)
    if isinstance(widget, forms.CheckboxSelectMultiple):
        return CHECKBOX_MULTI
    if isinstance(widget, forms.RadioSelect):
        return RADIO
    if isinstance(widget, forms.CheckboxInput):
        return CHECKBOX
    if isinstance(widget, forms.SelectMultiple):
        return MULTI
    if isinstance(widget, forms.Select):
        return SELECT
    if isinstance(widget, forms.Textarea):
        return TEXTAREA
    if isinstance(widget, forms.FileInput):
        return FILE
    if isinstance(widget, (forms.DateInput, forms.TimeInput, forms.NumberInput, admin_widgets.ForeignKeyRawIdWidget)):
        return INPUT_SHORT
    if isinstance(widget, forms.widgets.Input):
        return INPUT
    return None


def _decorate(widget, has_errors):
    """Append design-system classes to every leaf widget of a widget tree, in place."""
    if isinstance(widget, admin_widgets.RelatedFieldWidgetWrapper):
        _decorate(widget.widget, has_errors)
        return
    if isinstance(widget, forms.MultiWidget):
        for sub in widget.widgets:
            _decorate(sub, has_errors)
        return
    cls = widget_class(widget)
    if not cls:
        return
    if has_errors and cls in ERROR_CLASSES:
        cls = f"{cls} {ERROR_CLASSES[cls]}"
    existing = widget.attrs.get("class", "")
    widget.attrs["class"] = f"{existing} {cls}".strip()


@register.simple_tag
def ds_field(bound_field, label=None):
    """Render a BoundField (or AdminField) with design-system classes.

    ``label`` sets ``aria-label`` (used where no visible <label> exists).
    Existing widget classes are preserved (``vDateField``, ``vForeignKeyRawIdAdminField``…)
    because Django's admin JavaScript relies on them.
    """
    bound = _bound(bound_field)
    if bound is None:
        return bound_field
    widget = copy.deepcopy(bound.field.widget)
    _decorate(widget, bool(bound.errors))
    attrs = {}
    if label and not widget.is_hidden:
        # Tabular inlines have no <label> per cell; name the control explicitly.
        attrs["aria-label"] = str(label)
    return bound.as_widget(widget=widget, attrs=attrs or None)


def _bound(value):
    """Accept a BoundField or an admin helper (AdminField) wrapping one."""
    if isinstance(value, BoundField):
        return value
    inner = getattr(value, "field", None)
    return inner if isinstance(inner, BoundField) else None


@register.filter
def ds_widget_kind(bound_field):
    bound = _bound(bound_field)
    widget = getattr(getattr(bound, "field", None), "widget", None)
    if isinstance(widget, admin_widgets.RelatedFieldWidgetWrapper):
        widget = widget.widget
    if isinstance(widget, forms.CheckboxInput):
        return "checkbox"
    if isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
        return "choices"
    return "input"


# --------------------------------------------------------------------------- change list
@register.simple_tag
def ds_page_url(cl, page):
    return escape(cl.get_query_string({PAGE_VAR: page}))


@register.filter
def ds_obj_display(value):
    """Fallback for Django 6.1's ``to_object_display_value``."""
    try:
        from django.contrib.admin.templatetags.admin_filters import to_object_display_value

        return to_object_display_value(value)
    except ImportError:  # Django < 6.1
        text = str(value)
        return text if text.strip() else "-"


@register.simple_tag(takes_context=True)
def ds_change_form_actions(context):
    """Render change-form admin actions on Django versions that support them (6.1+)."""
    from django.contrib.admin.templatetags import admin_modify
    from django.template.loader import get_template

    if "change_form_admin_actions" not in admin_modify.register.tags or not context.get("action_form"):
        return ""
    flat = context.flatten()
    flat["action_index"] = 0
    return get_template("admin/change_form_actions.html").render(flat, context.get("request"))


# --------------------------------------------------------------------------- islands
@register.simple_tag(takes_context=True)
def ds_island(context, name, src, props=None, css_class="", loading_label="Loading…"):
    """Mount point for an independent JS component (vanilla, Lit, React, Puck…).

    ``src`` is a static path (or URL) to an ES module exporting
    ``mount(element, props, context) -> optional unmount function``.
    """
    url = src if str(src).startswith(("http://", "https://", "/")) else static(src)
    payload = json.dumps(props or {}, default=str).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return format_html(
        '<div class="ds-island {}" data-ds-island="{}" data-ds-src="{}" aria-busy="true">'
        '<script type="application/json" data-ds-props>{}</script>'
        '<div class="ds-island-loading flex items-center gap-2 text-sm ds-muted" role="status">'
        '<span class="d-loading d-loading-spinner d-loading-sm"></span>{}</div>'
        "<noscript><div class=\"d-alert d-alert-warning\">This component requires JavaScript.</div></noscript>"
        "</div>",
        css_class,
        name,
        url,
        mark_safe(payload),
        loading_label,
    )


@register.filter
def ds_json(value):
    return mark_safe(json.dumps(value, default=str).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


@register.simple_tag(takes_context=True)
def ds_object_list(context, value):
    """Nested object list for delete confirmations; honours Django 6.1's
    ``ModelAdmin.delete_confirmation_max_display`` when available."""
    return ds_unordered_list(value, context.get("delete_confirmation_max_display"))


def ds_unordered_list(value, max_display=None):
    """``truncated_unordered_list`` on Django 6.1+, ``unordered_list`` otherwise."""
    try:
        from django.contrib.admin.templatetags.admin_filters import truncated_unordered_list

        return truncated_unordered_list(value, max_display)
    except ImportError:
        from django.template.defaultfilters import unordered_list

        return unordered_list(value, autoescape=True)
