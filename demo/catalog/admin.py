"""Configuration #1 — conventional Django admin code, unchanged.

Nothing here imports dsadmin except the optional ``display`` helpers used by
``ProductAdmin``. ``admin.site`` is a DSAdminSite only because settings use
``dsadmin.apps.AdminConfig``; these classes would work identically on stock
Django admin.
"""

from django.contrib import admin, messages

from dsadmin.display import badge, boolean_badge, progress

from .models import Category, Product, ProductNote, Supplier, Tag, Variant


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1


class ProductNoteInline(admin.StackedInline):
    model = ProductNote
    extra = 0
    fields = ["body", "internal", "author"]
    autocomplete_fields = []


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    list_filter = ["parent"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "country", "active"]
    list_filter = ["active", "country"]
    search_fields = ["name", "email"]
    list_editable = ["active"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.action(description="Mark selected products as active", permissions=["change"])
def make_active(modeladmin, request, queryset):
    updated = queryset.update(status=Product.Status.ACTIVE)
    modeladmin.message_user(request, f"{updated} product(s) marked active.", messages.SUCCESS)


@admin.action(description="Archive selected products", permissions=["change"])
def archive(modeladmin, request, queryset):
    updated = queryset.update(status=Product.Status.ARCHIVED)
    modeladmin.message_user(request, f"{updated} product(s) archived.", messages.WARNING)


status_badge = badge(
    "status",
    description="Status",
    tones={"draft": "neutral", "active": "success", "archived": "warning"},
)
featured_badge = boolean_badge("is_featured", description="Featured", true_label="Featured", false_label="No")
stock_bar = progress("stock", maximum=200, description="Stock", thresholds=[(10, "error"), (40, "warning")],
                     tone="success")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", status_badge, featured_badge, "price", stock_bar, "updated_at"]
    list_display_links = ["name"]
    list_filter = ["status", "is_featured", "category", "supplier", "launch_date"]
    search_fields = ["name", "sku", "description", "category__name"]
    date_hierarchy = "created_at"
    prepopulated_fields = {"slug": ["name"]}
    filter_horizontal = ["tags"]
    autocomplete_fields = ["supplier"]
    readonly_fields = ["created_at", "updated_at"]
    actions = [make_active, archive]
    inlines = [VariantInline, ProductNoteInline]
    list_per_page = 20
    save_on_top = False
    fieldsets = [
        (None, {"fields": ["name", "slug", "sku", "category", "supplier", "status"]}),
        ("Pricing & stock", {"fields": [("price", "stock"), "is_featured"],
                             "description": "Prices are in CAD."}),
        ("Content", {"fields": ["description", "tags", "launch_date"]}),
        ("Metadata", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, ProductNote) and obj.author_id is None:
                obj.author = request.user
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()
