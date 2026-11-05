"""Configuration #2 — a second admin site from the same dsadmin version.

Different theme (PLT "workbench"), branding, navigation, dashboard, a custom
page, a function page, a JavaScript island and object actions — all declared
here, without touching dsadmin's code.
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count, F, Sum

from dsadmin import DSAdminSite, DSModelAdmin, PageView, object_action
from dsadmin import widgets as w
from dsadmin.display import badge, progress

from .admin import CategoryAdmin, SupplierAdmin, TagAdmin, VariantInline
from .models import Category, Product, Supplier, Tag


def low_stock_count(request):
    return Product.objects.filter(stock__lt=10).exclude(status=Product.Status.ARCHIVED).count()


def inventory_value(request):
    total = Product.objects.aggregate(v=Sum(F("price") * F("stock")))["v"] or 0
    return f"${total:,.0f}"


def products_by_status(request):
    rows = Product.objects.values("status").annotate(n=Count("id")).order_by("status")
    labels = dict(Product.Status.choices)
    return [(labels.get(r["status"], r["status"]), r["n"]) for r in rows]


def products_by_category(request):
    return [
        (c.name, c.n)
        for c in Category.objects.annotate(n=Count("products")).filter(n__gt=0).order_by("-n")[:6]
    ]


def latest_products(request):
    return [
        ((p.name, f"/backoffice/catalog/product/{p.pk}/change/"), p.get_status_display(), p.stock)
        for p in Product.objects.order_by("-created_at")[:5]
    ]


backoffice = DSAdminSite(
    name="backoffice",
    site_header="Workbench Ops",
    site_title="Workbench Ops",
    site_subheader="Inventory desk",
    index_title="Overview",
    theme="workbench",
    dark_theme=None,
    environment=("Staging", "warning"),
    navigation=[
        {"label": "Inventory", "icon": "box", "items": [
            {"model": "catalog.product", "icon": "tag", "badge": low_stock_count},
            {"model": "catalog.category", "icon": "folder"},
            {"model": "catalog.supplier", "icon": "truck"},
            {"model": "catalog.tag", "icon": "tag"},
        ]},
        {"label": "Insights", "icon": "chart", "items": [
            {"page": "inventory-report"},
            {"page": "stock-board"},
        ]},
        {"label": "Access", "icon": "shield", "items": [
            {"model": "auth.user", "icon": "user"},
            {"model": "auth.group", "icon": "users"},
        ]},
        {"label": "Resources", "icon": "file", "items": [
            {"label": "Design system", "url": "https://github.com/aavendano/plt-design-system", "external": True},
        ]},
    ],
    dashboard=[
        w.ModelCountCard("catalog.product", icon="box"),
        w.MetricCard("Low stock", value=low_stock_count, icon="alert", tone="warning",
                     description="active or draft items under 10 units"),
        w.MetricCard("Inventory value", value=inventory_value, icon="chart", tone="success"),
        w.ModelCountCard("catalog.supplier", icon="truck"),
        w.BarList("Products by status", data=products_by_status, width=2),
        w.BarList("Top categories", data=products_by_category, tone="accent", width=2),
        w.TableWidget("Latest products", columns=["Product", "Status", "Stock"], rows=latest_products, width=2),
        w.QuickActions([
            {"label": "New product", "add": "catalog.product", "icon": "plus"},
            {"label": "New supplier", "add": "catalog.supplier", "icon": "truck"},
            {"label": "Inventory report", "view": "page_inventory-report", "icon": "chart"},
        ], width=1),
        w.RecentActions(width=1, mine=False),
    ],
    user_links=[{"label": "Main admin", "url": "/admin/", "icon": "home"}],
)


# ----------------------------------------------------------------- model admins
class ProductBackofficeAdmin(DSModelAdmin):
    list_display = ["name", "sku", badge("status", tones={"draft": "neutral", "active": "success",
                                                          "archived": "warning"}, description="Status"),
                    progress("stock", maximum=200, thresholds=[(10, "error"), (40, "warning")], tone="success",
                             description="Stock"),
                    "price"]
    list_filter = ["status", "category"]
    search_fields = ["name", "sku"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [VariantInline]
    autocomplete_fields = ["supplier", "category"]
    filter_horizontal = ["tags"]
    object_actions = ["publish", "archive_product"]
    list_object_actions = True

    def has_publish_permission(self, request, obj=None):
        return request.user.has_perm("catalog.publish_product") and (obj is None or obj.status != Product.Status.ACTIVE)

    @object_action(description="Publish", permissions=["publish"], tone="success", icon="check")
    def publish(self, request, obj):
        obj.status = Product.Status.ACTIVE
        obj.save(update_fields=["status", "updated_at"])
        self.message_user(request, f"“{obj}” is now active.", messages.SUCCESS)

    @object_action(description="Archive", permissions=["change"], tone="warning", icon="inbox",
                   confirm="Archived products disappear from the storefront. Continue?")
    def archive_product(self, request, obj):
        obj.status = Product.Status.ARCHIVED
        obj.save(update_fields=["status", "updated_at"])
        self.message_user(request, f"“{obj}” archived.", messages.WARNING)


backoffice.register(Product, ProductBackofficeAdmin)
backoffice.register(Category, CategoryAdmin)       # same ModelAdmin classes as /admin/
backoffice.register(Supplier, SupplierAdmin)
backoffice.register(Tag, TagAdmin)
backoffice.register(User, UserAdmin)
backoffice.register(Group, GroupAdmin)


# ----------------------------------------------------------------- custom pages
@backoffice.register_page(slug="inventory-report", title="Inventory report", icon="chart", group="Insights",
                          permission="catalog.view_product")
class InventoryReportPage(PageView):
    template_name = "catalog/inventory_report.html"
    subtitle = "Stock position by category"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rows"] = (
            Category.objects.annotate(
                products_count=Count("products"),
                units=Sum("products__stock"),
                value=Sum(F("products__price") * F("products__stock")),
            )
            .order_by("name")
        )
        ctx["low_stock"] = Product.objects.filter(stock__lt=10).select_related("category")[:10]
        return ctx


@backoffice.register_page(slug="stock-board", title="Stock board", icon="grid", group="Insights",
                          permission="catalog.change_product")
def stock_board(request, site):
    products = list(
        Product.objects.exclude(status=Product.Status.ARCHIVED)
        .order_by("stock")
        .values("id", "name", "sku", "stock", "status")[:24]
    )
    return site.render_page(
        request,
        "catalog/stock_board.html",
        {"island_props": {"products": products, "threshold": 10, "changeUrl": "/backoffice/catalog/product/"}},
        title="Stock board",
        subtitle="Independent JavaScript component mounted inside the admin layout",
    )
