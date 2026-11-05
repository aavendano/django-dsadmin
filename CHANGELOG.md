# Changelog

## 0.1.0 — 2026-11-05

First release.

- `DSAdminSite` (drop-in via `dsadmin.apps.AdminConfig`) with design-system layout,
  declarative navigation, dashboard widgets, custom pages, global search, light/dark modes.
- Design-system templates for every stock admin screen; Django block names and JS hooks preserved.
- `DSModelAdmin` object actions; `dsadmin.display` list helpers; `{% ds_island %}` JavaScript islands.
- Stylesheets for the PLT themes `admin`, `nocturne`, `workbench`, `unconventionals`,
  `playlovetoys` (plt-design-system main, daisyUI 5.7.50, Tailwind 4.3.4).

Verification for this release:

- pytest: 60/60 on Django 5.2.19, 6.0.10, 6.1.3.
- axe-core 4 (WCAG 2.0/2.1/2.2 A+AA): 0 violations, 12 screens × light/dark.
- Wheel installed into a clean virtualenv runs `tests/standalone` (stock `django.contrib.admin`).
- Adoption probe on `shopify-django-md-cms` (settings overlay only): 12 ModelAdmins, 27 URLs, 0 problems.
