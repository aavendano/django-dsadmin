# Navigation, dashboard, pages and search

## Navigation

`NAVIGATION = None` builds one group per app from `AdminSite.get_app_list(request)`
(so ModelAdmin permissions and `get_app_list` overrides apply), plus one group
per page `group`.

Declared navigation is plain data:

```python
navigation = [
    {"label": "Inventory", "icon": "box", "items": [
        {"model": "catalog.product", "icon": "tag", "badge": low_stock_count},  # badge: value or callable(request)
        {"model": "catalog.category", "label": "Families"},
    ]},
    {"label": "Insights", "icon": "chart", "items": [
        {"page": "inventory-report"},
        {"label": "Grafana", "url": "https://grafana.example", "external": True,
         "permission": "catalog.view_product"},
        {"label": "Password", "view": "password_change", "icon": "key"},   # URL name in the site namespace
    ]},
    {"apps": "*"},                     # every app not referenced above
    {"apps": ["auth"]},                # or only some apps
]
```

| Item | Visible when |
| --- | --- |
| `model` | registered on the site and the user can view/change it |
| `page` | the page's `permission` passes |
| `url` / `view` | optional `permission` (perm string, list, or callable(request)) passes |

Groups also accept `permission` and `collapsible`. Empty groups disappear. The
active item is the longest URL prefix of the current path.

Icons: `{% ds_icon %}` names from the built-in sprite — `home dashboard box tag folder
users user shield settings chart file list grid search filter plus edit trash eye
history external logout key sun moon monitor menu x chevron-* arrow-* sort check
alert info error success inbox calendar clock star truck cart layers zap link dot
more sidebar play download upload`.

## Dashboard

```python
from dsadmin import widgets as w

dashboard = [
    w.ModelCountCard("catalog.product", icon="box"),                         # hidden without view permission
    w.MetricCard("Revenue", value=revenue_fn, delta=+12.5, icon="chart", tone="success", url="/admin/orders/"),
    w.BarList("By status", data=status_fn, width=2),                         # [(label, value)], d-progress bars
    w.TableWidget("Latest", columns=["Product", "Stock"], rows=rows_fn, width=2),  # cells: text or (text, url)
    w.QuickActions([{"label": "New product", "add": "catalog.product"},     # add links check has_add_permission
                    {"label": "Report", "view": "page_inventory-report", "icon": "chart"}]),
    w.RecentActions(mine=False),
    w.AppList(),
    w.TemplateWidget("myapp/widget.html", "Title", context=ctx_fn),
    w.IslandWidget("Live chart", name="chart", src="myapp/chart.js", props=props_fn),
]
```

Every widget accepts `title`, `width` (1–4 columns), `permission`,
`description`. Values may be callables taking `request`. Write your own by
subclassing `Widget` and returning a dict from `get_context(request, site)`
(return `None` to hide the widget for that request). Exceptions inside a widget
are logged (`dsadmin` logger) and replaced by an error card.

## Custom pages

```python
from dsadmin import PageView

@site.register_page(slug="inventory-report", title="Inventory report", icon="chart",
                    group="Insights", permission="catalog.view_product")
class InventoryReport(PageView):
    template_name = "catalog/inventory_report.html"   # {% extends "dsadmin/page.html" %}, fill {% block page_content %}
    subtitle = "Stock by category"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rows"] = ...
        return ctx


@site.register_page(slug="stock-board", title="Stock board", permission="catalog.change_product")
def stock_board(request, site):
    return site.render_page(request, "catalog/stock_board.html", {"items": ...}, title="Stock board")
```

Pages live at `<site>/p/<slug>/` (override with `path=`), are named
`<site>:page_<slug>`, are wrapped in `admin_view` (staff login, `never_cache`)
and then checked against `permission` (403 otherwise). `in_navigation=False`
keeps them out of the automatic sidebar.

## Global search

`<site>/search/?q=…` (navbar field, `/` shortcut) queries every ModelAdmin with
`search_fields` that the user may view or change, through the ModelAdmin's own
`get_queryset()` and `get_search_results()`, then filters hits with
`has_view_or_change_permission(request, obj)`. Each section links to the full
change list search.
