# Components

dsadmin renders daisyUI components with the `d-` prefix (`d-card`, `d-table`,
`d-btn`, `d-badge`, `d-alert`, `d-menu`, `d-drawer`, `d-stat`, `d-modal`…) and
PLT treatments (`theme-bordered`, `theme-elevated`, `theme-label-bold`). It
never introduces a parallel primitive (`ds-*` classes are layout hooks only).

## Template tags — `{% load dsadmin %}`

| Tag | |
| --- | --- |
| `{% ds_field bound_field %}` | Render a `BoundField` or admin `AdminField` with design-system classes (`d-input`, `d-select`, `d-textarea`, `d-checkbox`, `d-radio`, `d-file-input`, error variants). Existing widget classes are kept (Django's admin JS relies on `vDateField`, `vForeignKeyRawIdAdminField`…). `label="…"` adds `aria-label`. |
| `{% ds_icon "box" "size-5" %}` | Icon from the sprite; third argument gives it an accessible label. |
| `{% ds_badge "Active" "success" %}` | Tones: neutral primary secondary accent info success warning error outline. |
| `{% ds_island name src props %}` | JavaScript island mount point ([extensions.md](extensions.md)). |
| `{% dsadmin_ui as ui %}` | Layout context (theme, branding, navigation) — works on any AdminSite. |
| `{% ds_nonce %}` / `{% ds_media media %}` | CSP nonce attribute / `forms.Media` with nonces. |

## Includes

```django
{% include "dsadmin/components/empty_state.html" with icon="inbox" title="Nothing yet" text="…" action_url=url action_label="Add" %}
{% include "dsadmin/components/alert.html" with tone="warning" title="Heads up" text="…" %}
{% include "dsadmin/components/confirm_dialog.html" with id="x" title="Sure?" action=url confirm_label="Do it" %}
{% include "dsadmin/components/skeleton.html" %}
{% include "dsadmin/widgets/_app_cards.html" with app_list=app_list %}
```

## `list_display` helpers — `dsadmin.display`

```python
from dsadmin.display import badge, boolean_badge, progress

class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        badge("status", tones={"draft": "neutral", "active": "success", "archived": "warning"}),
        boolean_badge("is_featured", description="Featured", true_label="Featured", false_label="No"),
        progress("stock", maximum=200, thresholds=[(10, "error"), (40, "warning")], tone="success"),
    ]
```

They are ordinary `@admin.display` callables (ordering preserved) and work on
any ModelAdmin.

## Object actions

```python
from dsadmin import DSModelAdmin, object_action

class ProductAdmin(DSModelAdmin):
    object_actions = ["publish", "archive"]
    list_object_actions = True          # also a column of buttons in the change list

    def has_publish_permission(self, request, obj=None):
        return request.user.has_perm("catalog.publish_product")

    @object_action(description="Publish", permissions=["publish"], tone="success", icon="check")
    def publish(self, request, obj):
        obj.status = "active"; obj.save()
        self.message_user(request, "Published.")

    @object_action(description="Archive", permissions=["change"], tone="warning",
                   confirm="Archived products disappear from the storefront. Continue?")
    def archive(self, request, obj):
        ...
```

- URL: `<app>/<model>/<pk>/action/<name>/` (`<site>:<app>_<model>_object_action`).
- POST only (405 on GET unless a confirmation is configured, in which case GET shows a
  confirmation page — the no-JS fallback of the dialog). CSRF enforced by Django.
- `permissions` mirror Django admin actions: `"x"` requires `has_x_permission(request, obj)`.
  Failing checks → 403; buttons the user cannot use are not rendered.
- Each run is logged with `log_change` (visible in History). `next` redirects are restricted to
  the current host.
- Return an `HttpResponse` to take over the response; otherwise the user returns to the change form.

Bulk actions remain standard Django admin actions (`actions = [...]`), including
`delete_selected` and its confirmation page.
