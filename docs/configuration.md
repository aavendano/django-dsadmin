# Configuration

## Precedence

1. keyword options to `DSAdminSite(name, **options)` (lower-case keys)
2. lower-case class attributes on a `DSAdminSite` subclass
3. `settings.DSADMIN` (upper-case keys)
4. defaults (`dsadmin.conf.DEFAULTS`)

`site_title`, `site_header`, `site_url` and `index_title` passed to the
constructor behave like Django's `AdminSite` attributes and win over settings.

## Settings

| Key | Default | |
| --- | --- | --- |
| `SITE_TITLE` | `AdminSite.site_title` | `<title>` suffix |
| `SITE_HEADER` | `AdminSite.site_header` | Sidebar / login brand |
| `SITE_SUBHEADER` | `""` | Small line under the brand |
| `LOGO`, `LOGO_DARK` | `None` | Static path or URL; callable(request) allowed |
| `FAVICON` | `None` | Static path or URL |
| `ENVIRONMENT` | `None` | `("Staging", "warning")`, a string, or callable(request) |
| `THEME` | `"admin"` | Built-in theme name, static path ending in `.css`, or URL |
| `DARK_THEME` | `"nocturne"` | Same; `None` disables dark mode and the toggle |
| `COLOR_MODE` | `"auto"` | Initial mode: `auto` / `light` / `dark` (user choice persists in localStorage) |
| `SHOW_THEME_TOGGLE` | `True` | |
| `FONT_CSS` | `[]` | Stylesheets for the theme fonts (themes name fonts; loading is the app's choice) |
| `EXTRA_CSS` | `[]` | Extra stylesheets on every admin page |
| `EXTRA_JS` | `[]` | Extra ES modules on every admin page |
| `NAVIGATION` | `None` | Automatic, or list of groups; callable(request) allowed |
| `SIDEBAR_COLLAPSIBLE` | `True` | Desktop icon-rail toggle |
| `DASHBOARD` | `None` | Default widgets, or list; callable(request) allowed |
| `SEARCH` | `True` | Global search in the navbar (`DSAdminSite` only) |
| `SEARCH_LIMIT` | `5` | Hits per model |
| `USER_LINKS` | `[]` | Extra user-menu links: `{"label", "url" or "view", "icon", "permission"}` |

## Colour modes

Each theme is a complete stylesheet. With a dark theme configured, both are
linked with `media` queries; the toggle switches `media` attributes (an inline
script applies the stored choice before first paint, nonce-aware). Without
JavaScript the system preference applies.

## Content-Security-Policy

Inline scripts and every `<script>`/`<link>` dsadmin renders carry the request
nonce when one is available (`csp_nonce` context variable — Django 6's
`django.template.context_processors.csp` — or `request.csp_nonce`). dsadmin
loads nothing from third-party origins.

## Several sites, one project

```python
# urls.py
urlpatterns = [
    path("admin/", admin.site.urls),          # DSADMIN settings
    path("backoffice/", backoffice.urls),     # DSAdminSite(name="backoffice", ...)
]
```

Each site has its own theme, branding, navigation, dashboard and pages. The
demo runs both side by side.
