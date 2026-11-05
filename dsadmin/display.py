"""``list_display`` / ``readonly_fields`` helpers that emit design-system markup.

    from dsadmin.display import badge, boolean_badge, progress

    class ProductAdmin(admin.ModelAdmin):
        list_display = ["name", status, published, stock_level]

    status = badge("status", tones={"draft": "neutral", "active": "success", "archived": "warning"})
    published = boolean_badge("is_published", description="Published")
    stock_level = progress("stock", maximum=500)

They are ordinary callables decorated with ``django.contrib.admin.display``, so
they work on any ModelAdmin (dsadmin site or not).
"""

from django.contrib import admin
from django.utils.html import format_html

# Literal class names — keep them literal so Tailwind compiles them.
BADGE_TONES = {
    "neutral": "d-badge d-badge-sm d-badge-ghost",
    "primary": "d-badge d-badge-sm d-badge-primary",
    "secondary": "d-badge d-badge-sm d-badge-secondary",
    "accent": "d-badge d-badge-sm d-badge-accent",
    "info": "d-badge d-badge-sm d-badge-info",
    "success": "d-badge d-badge-sm d-badge-success",
    "warning": "d-badge d-badge-sm d-badge-warning",
    "error": "d-badge d-badge-sm d-badge-error",
    "outline": "d-badge d-badge-sm d-badge-outline",
}
PROGRESS_TONES = {
    "primary": "d-progress d-progress-primary",
    "success": "d-progress d-progress-success",
    "warning": "d-progress d-progress-warning",
    "error": "d-progress d-progress-error",
    "info": "d-progress d-progress-info",
}


def badge_html(text, tone="neutral"):
    return format_html('<span class="{} theme-label-bold">{}</span>', BADGE_TONES.get(tone, BADGE_TONES["neutral"]), text)


def _value(obj, field):
    value = getattr(obj, field)
    return value() if callable(value) else value


def badge(field, *, tones=None, description=None, ordering=None, default="neutral"):
    """Render a field as a coloured badge. ``tones`` maps raw values to tones.

    For fields with ``choices`` the display label is shown.
    """
    tones = tones or {}

    @admin.display(description=description or field.replace("_", " "), ordering=ordering or field)
    def _badge(obj):
        raw = _value(obj, field)
        getter = getattr(obj, f"get_{field}_display", None)
        text = getter() if callable(getter) else raw
        if raw is None or raw == "":
            return "—"
        return badge_html(text, tones.get(raw, default))

    _badge.__name__ = f"{field}_badge"
    return _badge


def boolean_badge(field, *, description=None, true_label="Yes", false_label="No",
                  true_tone="success", false_tone="neutral", ordering=None):
    @admin.display(description=description or field.replace("_", " "), ordering=ordering or field)
    def _bool(obj):
        value = _value(obj, field)
        if value is None:
            return "—"
        return badge_html(true_label if value else false_label, true_tone if value else false_tone)

    _bool.__name__ = f"{field}_bool_badge"
    return _bool


def progress(field, *, maximum=100, description=None, tone="primary", thresholds=None, ordering=None):
    """``<progress>`` bar. ``thresholds`` e.g. ``[(10, "error"), (50, "warning")]``
    picks the tone of the first threshold the value is below."""

    @admin.display(description=description or field.replace("_", " "), ordering=ordering or field)
    def _progress(obj):
        value = _value(obj, field) or 0
        chosen = tone
        for limit, t in thresholds or []:
            if value < limit:
                chosen = t
                break
        return format_html(
            '<span class="inline-flex items-center gap-2"><progress class="{} w-24" value="{}" max="{}" '
            'aria-label="{}"></progress><span class="tabular-nums text-sm">{}</span></span>',
            PROGRESS_TONES.get(chosen, PROGRESS_TONES["primary"]),
            min(value, maximum),
            maximum,
            f"{value} / {maximum}",
            value,
        )

    _progress.__name__ = f"{field}_progress"
    return _progress
