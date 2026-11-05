"""Builds the ``dsadmin`` template context (layout, theme, branding, navigation).

Used by ``DSAdminSite.each_context`` and, as a fallback, by the
``{% dsadmin_ui %}`` tag so that a plain ``AdminSite`` also renders with the
design system (automatic navigation, default theme).
"""

from __future__ import annotations

from django.templatetags.static import static
from django.urls import NoReverseMatch, reverse

from .conf import BUILTIN_THEMES, get_setting
from .navigation import _check_permission, build_navigation


def theme_url(theme):
    if not theme:
        return None
    theme = str(theme)
    if theme.startswith(("http://", "https://", "/")):
        return theme
    if theme.endswith(".css"):
        return static(theme)
    return static(f"dsadmin/css/themes/{theme}.css")


def asset_url(value):
    if not value:
        return None
    value = str(value)
    if value.startswith(("http://", "https://", "/", "data:")):
        return value
    return static(value)


def _call(value, request):
    return value(request) if callable(value) else value


ENV_TONES = {
    "neutral": "d-badge-ghost",
    "info": "d-badge-info",
    "success": "d-badge-success",
    "warning": "d-badge-warning",
    "error": "d-badge-error",
}


def build_ui(request, site=None, available_apps=None, has_permission=None, site_name=None):
    def s(key):
        return get_setting(key, site)

    if site_name is None:
        site_name = getattr(site, "name", None)
    if site_name is None:
        match = getattr(request, "resolver_match", None)
        site_name = (match.namespace if match and match.namespace else "admin")

    def url(name, **kw):
        try:
            return reverse(f"{site_name}:{name}", kwargs=kw or None)
        except NoReverseMatch:
            return None

    title = s("SITE_TITLE") or getattr(site, "site_title", None) or "Admin"
    header = s("SITE_HEADER") or getattr(site, "site_header", None) or title

    env = _call(s("ENVIRONMENT"), request)
    environment = None
    if env:
        label, tone = (env, "warning") if isinstance(env, str) else (env[0], env[1] if len(env) > 1 else "warning")
        environment = {"label": label, "class": ENV_TONES.get(tone, ENV_TONES["warning"])}

    dark = s("DARK_THEME")
    color_mode = s("COLOR_MODE") if s("COLOR_MODE") in ("auto", "light", "dark") else "auto"
    if not dark:
        color_mode = "light"

    if has_permission is None:
        has_permission = bool(site.has_permission(request)) if site is not None and request is not None else False

    navigation = []
    if has_permission:
        if available_apps is None:
            available_apps = site.get_app_list(request) if site is not None else []
        navigation = build_navigation(site, request, available_apps, s("NAVIGATION"), site_name=site_name)

    user_links = []
    for link in s("USER_LINKS") or []:
        if not _check_permission(request, link.get("permission")):
            continue
        href = link.get("url") or (url(link["view"]) if link.get("view") else None)
        if href:
            user_links.append({"label": link["label"], "url": href, "icon": link.get("icon", "link")})

    search_enabled = bool(s("SEARCH")) and has_permission and getattr(site, "_ds_search_enabled", False)

    return {
        "site_name": site_name,
        "title": title,
        "header": header,
        "subheader": s("SITE_SUBHEADER"),
        "logo": asset_url(_call(s("LOGO"), request)),
        "logo_dark": asset_url(_call(s("LOGO_DARK"), request)),
        "favicon": asset_url(s("FAVICON")),
        "environment": environment,
        "theme": str(s("THEME")),
        "theme_url": theme_url(s("THEME")),
        "dark_theme": str(dark) if dark else None,
        "dark_theme_url": theme_url(dark),
        "color_mode": color_mode,
        "show_theme_toggle": bool(s("SHOW_THEME_TOGGLE")) and bool(dark),
        "font_css": [asset_url(u) for u in s("FONT_CSS") or []],
        "extra_css": [asset_url(u) for u in s("EXTRA_CSS") or []],
        "extra_js": [asset_url(u) for u in s("EXTRA_JS") or []],
        "navigation": navigation,
        "sidebar_collapsible": bool(s("SIDEBAR_COLLAPSIBLE")),
        "search_url": url("dsadmin_search") if search_enabled else None,
        "index_url": url("index") or "/",
        "user_links": user_links,
        "builtin_themes": BUILTIN_THEMES,
        "is_dsadmin_site": bool(getattr(site, "_dsadmin_site", False)),
    }
