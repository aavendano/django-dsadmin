"""Settings resolution.

Precedence (highest first):
  1. keyword options passed to ``DSAdminSite(name, **options)``
  2. class attributes on a ``DSAdminSite`` subclass (lower-case names)
  3. ``settings.DSADMIN`` (upper-case keys)
  4. ``DEFAULTS`` below
"""

from django.conf import settings

#: Built-in stylesheets shipped in ``dsadmin/static/dsadmin/css/themes/``.
#: Each one is a full build of a ``@playlovetoys/design-system`` theme.
BUILTIN_THEMES = ("admin", "nocturne", "workbench", "unconventionals", "playlovetoys")

DEFAULTS = {
    # Branding
    "SITE_TITLE": None,  # falls back to AdminSite.site_title
    "SITE_HEADER": None,  # falls back to AdminSite.site_header
    "SITE_SUBHEADER": "",
    "SITE_URL": None,  # falls back to AdminSite.site_url
    "LOGO": None,  # static path or absolute URL
    "LOGO_DARK": None,
    "FAVICON": None,
    "ENVIRONMENT": None,  # ("Staging", "warning") or callable(request) -> tuple | None
    # Theme (design-system theme names or full stylesheet URLs)
    "THEME": "admin",
    "DARK_THEME": "nocturne",  # None disables dark mode
    "COLOR_MODE": "auto",  # "auto" | "light" | "dark" (initial mode before user choice)
    "SHOW_THEME_TOGGLE": True,
    "FONT_CSS": [],  # stylesheet URLs for the theme's fonts (optional)
    "EXTRA_CSS": [],
    "EXTRA_JS": [],  # ES modules / scripts loaded on every admin page
    # Navigation
    "NAVIGATION": None,  # None -> automatic (apps + pages). See dsadmin.navigation
    "SIDEBAR_COLLAPSIBLE": True,
    "SHOW_APP_LIST_ON_DASHBOARD": True,
    # Dashboard
    "DASHBOARD": None,  # list of dsadmin.widgets.Widget, or callable(request) -> list
    # Search
    "SEARCH": True,
    "SEARCH_LIMIT": 5,
    # User menu extra links: [{"label", "url" | "view", "icon"}]
    "USER_LINKS": [],
}


def get_setting(key, site=None):
    """Resolve a dsadmin setting for ``site`` (may be None for plain AdminSite)."""
    key = key.upper()
    if key not in DEFAULTS:
        raise KeyError(f"Unknown dsadmin setting {key!r}")
    lower = key.lower()
    if site is not None:
        options = getattr(site, "ds_options", None) or {}
        if lower in options:
            return options[lower]
        # Only attributes declared on user subclasses count (Django's AdminSite
        # already defines site_title/site_header/site_url with its own defaults;
        # those are used as fallbacks by the UI builder instead).
        from django.contrib.admin import AdminSite

        for cls in type(site).__mro__:
            if cls is AdminSite or getattr(cls, "_dsadmin_base", False):
                break
            if lower in vars(cls):
                return vars(cls)[lower]
    user = getattr(settings, "DSADMIN", None) or {}
    if key in user:
        return user[key]
    return DEFAULTS[key]
