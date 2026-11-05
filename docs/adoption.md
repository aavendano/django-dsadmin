# Adopting dsadmin in an existing project

This is the path used to validate dsadmin against `shopify-django-md-cms`
(12 real ModelAdmins, no code changes — see
[evidence/adoption-shopify-django-md-cms.txt](evidence/adoption-shopify-django-md-cms.txt)).

## 1. Install

```bash
pip install -e ../django-dsadmin        # or a tagged wheel / git URL
```

## 2. INSTALLED_APPS

```diff
 INSTALLED_APPS = [
-    "django.contrib.admin",
+    "dsadmin",
+    "dsadmin.apps.AdminConfig",
     "django.contrib.auth",
     ...
 ]
```

`dsadmin.apps.AdminConfig` is Django's documented way to swap the default admin
site (`AdminConfig.default_site`). Your `admin.py` files, `admin.site.urls`,
custom `AdminSite` subclasses and third-party admin integrations are untouched.

`manage.py check` warns (`dsadmin.W001`) if `dsadmin` sits below the admin app
(its templates would not take precedence), and `dsadmin.W002` for unknown
`DSADMIN` keys.

## 3. Pick a theme

```python
DSADMIN = {"THEME": "admin", "DARK_THEME": "nocturne", "SITE_HEADER": "My Admin"}
```

Built-in stylesheets: `admin`, `nocturne`, `workbench`, `unconventionals`,
`playlovetoys` — full builds of the corresponding `plt-design-system` themes.
Any other theme: build it ([theming.md](theming.md)) and point `THEME` at the
stylesheet.

## 4. Verify

```bash
DJANGO_SETTINGS_MODULE=myproject.settings python ../django-dsadmin/scripts/probe_admin.py
```

The probe renders the index, the global search and the changelist / add /
change view of every registered ModelAdmin and fails if any of them errors or
renders outside the dsadmin shell. 403 responses produced by a ModelAdmin's own
`has_*_permission` hooks are reported as *permission preserved*, not as failures.

To try without touching the project, use a settings overlay (this is the exact
file used for the CMS run):

```python
# dsadmin_overlay.py — PYTHONPATH=.:/path/to/overlay DJANGO_SETTINGS_MODULE=dsadmin_overlay
from config.settings import *  # noqa
INSTALLED_APPS = ["dsadmin", "dsadmin.apps.AdminConfig"] + [a for a in INSTALLED_APPS if a != "django.contrib.admin"]
```

## 5. Opt into extras when needed

- `DSModelAdmin` for object actions ([components.md](components.md#object-actions))
- `dsadmin.display` helpers in `list_display`
- dashboard widgets, navigation groups, custom pages
  ([navigation-dashboard-pages.md](navigation-dashboard-pages.md))
- islands for interactive tools ([extensions.md](extensions.md))

None of these is required; a plain `admin.ModelAdmin` is a first-class citizen.

## Projects with their own admin templates

Project templates that extend `admin/base_site.html` (or `change_form.html`,
`change_list.html`) keep working: dsadmin keeps every Django block name
(`content`, `object-tools-items`, `field_sets`, `submit_buttons_bottom`,
`extrahead`, `breadcrumbs`…). Markup those templates emit with Django's classes
(`.module`, `.errornote`, `.object-tools`, `input[type=submit]`) is styled by a
compatibility layer, and Django's admin CSS variables are mapped to the theme's
tokens, so any Django stylesheet such a template pulls in follows the theme.
