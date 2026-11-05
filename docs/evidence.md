# Acceptance evidence

How each success factor of the objective is demonstrated. Everything listed is
reproducible from this repository.

| Factor | Evidence | Where |
| --- | --- | --- |
| **FE-01** Real ModelAdmin reuse | Conventional `catalog/admin.py` (no dsadmin imports except optional display helpers) passes list, create (with tabular + stacked inlines and M2M), edit, delete, search, filters, sorting, pagination, date hierarchy, bulk actions, `delete_selected`, `list_editable`, popups and autocomplete | `tests/test_modeladmin_compat.py` (22 tests) |
| | `shopify-django-md-cms` adopted with a settings overlay only: 12 ModelAdmins, 27 URLs, 0 problems | `docs/evidence/adoption-shopify-django-md-cms.txt` |
| **FE-02** Design-system fidelity | All UI is daisyUI `d-*` + PLT `theme-*`; stylesheets are compiled from `plt-design-system` themes; `dsadmin.css` holds no brand values; desktop/mobile × light/dark screenshots reviewed | `docs/theming.md`, `docs/screenshots/`, `tests/e2e/screens.py` |
| **FE-03** Customisation without touching the core | `/admin/` (settings-only: `admin`/`nocturne`, automatic nav, default dashboard) and `/backoffice/` (constructor options: `workbench`, custom nav, widgets, pages, island, object actions) run from the same package version in one process | `demo/`, `tests/test_framework.py::TestTwoConfigurations` |
| **FE-04** Functional compatibility | Forms, validation errors (`aria-invalid`, error classes), permissions, relations, filters, search, actions and CRUD verified; same suite green on Django 5.2, 6.0, 6.1 | `tests/`, `docs/evidence/test-matrix.txt` |
| **FE-05** Demonstrated extensibility | Class-based page, function page and an independent ES-module island inside the admin layout; ModelAdmin behaviour unchanged on the same site | `demo/catalog/backoffice.py`, `tests/test_framework.py::TestPagesAndIslands` |
| **FE-06** Consumer independence | Package contains no Shopify/KV/Agents-OS references; runs in a separate project using stock `django.contrib.admin` and no dsadmin code beyond `INSTALLED_APPS` | `tests/standalone/`, `tests/test_standalone.py` |
| **FE-07** User experience | Responsive drawer, mobile screenshots, keyboard-operable drawer/filters/menus, skip link, visible focus; axe-core WCAG 2.0/2.1/2.2 A+AA: **0 violations** on 12 screens × light/dark | `docs/screenshots/mobile.png`, `docs/evidence/axe-wcag22aa.txt`, `tests/e2e/a11y.py` |
| **FE-08** Quality & stability | `pip install` of the built wheel into a clean virtualenv runs the standalone project; 60 automated tests; system checks for misconfiguration; documented public API | `pyproject.toml`, `docs/`, wheel check in CHANGELOG |

## Security (RF-07)

| Check | Test |
| --- | --- |
| Anonymous → login, non-staff refused (admin pages and custom pages) | `test_security.py::test_anonymous_is_sent_to_login`, `test_non_staff_cannot_enter` |
| Navigation, dashboard widgets, quick actions and search hide what the user cannot access | `TestEditorPermissions` |
| Model and object permissions enforced on views; custom-page permissions | `TestEditorPermissions`, `test_custom_page_permission` |
| Object actions: permission hooks, POST-only, CSRF, open-redirect protection, 404 on unknown | `TestObjectActions` |
| CSRF enforced on admin forms | `test_csrf_enforced_on_admin_forms` |
| Island props cannot break out of `<script>`; user content escaped in list/form/search | `test_island_props_cannot_break_out_of_script`, `test_user_content_is_escaped` |

## Reproduce

```bash
pytest                                                    # functional + security + standalone
cd demo && python manage.py migrate && python manage.py seed_demo && python manage.py runserver 8765
python tests/e2e/screens.py http://127.0.0.1:8765 screens/
AXE_JS=…/axe-core/axe.min.js python tests/e2e/a11y.py http://127.0.0.1:8765
```
