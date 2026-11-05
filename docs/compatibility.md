# Compatibility

## Django

Tested on Django **5.2.19, 6.0.10, 6.1.3** (Python 3.13): 60/60 tests each
([evidence/test-matrix.txt](evidence/test-matrix.txt)). Version-specific admin
features are used only when present:

| Feature | Behaviour |
| --- | --- |
| Change-form admin actions (6.1) | rendered when Django provides them |
| `delete_confirmation_max_display` (6.1) | honoured on 6.1, full list before |
| `to_object_display_value` (6.1) | used on 6.1, `str()` fallback before |
| CSP nonces (6.0+) | added to every script/link when a nonce exists |

## What dsadmin overrides

Templates (all keep Django's block names and the ids/classes Django's JS uses):

`admin/base.html`, `base_site.html`, `index.html`, `app_index.html`,
`app_list.html`, `change_list.html`, `change_list_results.html`,
`change_list_object_tools.html`, `actions.html`, `filter.html`,
`search_form.html`, `pagination.html`, `date_hierarchy.html`,
`change_form.html`, `change_form_actions.html`, `change_form_object_tools.html`,
`submit_line.html`, `includes/fieldset.html`, `includes/object_delete_summary.html`,
`edit_inline/tabular.html`, `edit_inline/stacked.html`,
`delete_confirmation.html`, `delete_selected_confirmation.html`,
`object_history.html`, `login.html`, `widgets/related_widget_wrapper.html`,
`color_theme_toggle.html`, `nav_sidebar.html`; `registration/logged_out.html`,
`password_change_form.html`, `password_change_done.html`.

Not overridden (render inside the dsadmin shell with the compatibility layer):
`auth/user/change_password.html`, `auth/user/add_form.html`, password reset
pages, `popup_response.html`, `invalid_setup.html`, `404/500`.

Python: no Django internals are monkey-patched. `DSAdminSite` overrides only
public `AdminSite` methods (`each_context`, `get_urls`, `index`);
`DSModelAdmin` overrides `get_urls`, `render_change_form`, `changelist_view`,
`get_list_display`, all calling `super()`.

Django's admin JavaScript (`actions.js`, `inlines.js`, `SelectFilter2.js`,
`DateTimeShortcuts.js`, `RelatedObjectLookups.js`, `prepopulate.js`,
`filters.js`, autocomplete/select2) is used as-is. `dsadmin.js` adds two
accessibility patches on top: `role="img"` for SelectFilter2's labelled
tooltips and an accessible name for select2 comboboxes.

## Design system

Requires `@playlovetoys/design-system` with daisyUI ≥ 5.7.8 and Tailwind 4
only at build time. The shipped CSS was built from `plt-design-system` main,
daisyUI 5.7.50, Tailwind 4.3.4.

## Known limitations

- Global search runs one query per searchable ModelAdmin (limit per model). For
  very large registries, disable it (`SEARCH: False`) or narrow `search_fields`.
- Themes are whole stylesheets; switching theme at runtime between more than a
  light/dark pair is not built in.
- `auth/user/change_password.html` keeps Django's markup (styled via the
  compatibility layer), so it is visually plainer than overridden pages.
- The sticky submit row reserves `scroll-padding-bottom` so focused fields are
  never hidden behind it; projects that set their own `scroll-padding` should keep
  ≥ 6rem on change forms.
