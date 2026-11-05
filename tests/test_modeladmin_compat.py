"""FE-01 / FE-04 — conventional ModelAdmin features keep working under dsadmin.

Everything here goes through catalog/admin.py, which is plain Django admin code
registered on ``admin.site`` (a DSAdminSite via dsadmin.apps.AdminConfig).
"""

from decimal import Decimal

import pytest
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.urls import reverse

from catalog.models import Product, Supplier, Variant

pytestmark = pytest.mark.django_db


def inline_mgmt(prefix, total=0, initial=0):
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": str(initial),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


def product_payload(catalog, **overrides):
    data = {
        "name": "New Thing",
        "slug": "new-thing",
        "sku": "NEW-1",
        "category": catalog["category"].pk,
        "supplier": catalog["supplier"].pk,
        "status": "draft",
        "price": "19.99",
        "stock": "5",
        "description": "",
        "launch_date": "",
        **inline_mgmt("variants"),
        **inline_mgmt("notes"),
    }
    data.update(overrides)
    return data


class TestChangeList:
    url = reverse("admin:catalog_product_changelist")

    def test_renders_with_design_system(self, admin_client, catalog):
        r = admin_client.get(self.url)
        assert r.status_code == 200
        html = r.content.decode()
        assert 'id="result_list" class="d-table' in html
        assert "d-drawer" in html and "ds-sidebar" in html
        assert 'class="d-badge d-badge-sm d-badge-success theme-label-bold">Active<' in html  # badge() helper
        assert "<progress" in html  # progress() helper
        assert r.context["cl"].result_count == 30

    def test_search_uses_search_fields(self, admin_client, catalog):
        r = admin_client.get(self.url, {"q": "Velvet"})
        assert r.context["cl"].result_count == 15
        assert 'value="Velvet"' in r.content.decode()

    def test_list_filter(self, admin_client, catalog):
        r = admin_client.get(self.url, {"status__exact": "draft"})
        assert r.context["cl"].result_count == Product.objects.filter(status="draft").count()
        assert 'class="d-menu-active" aria-current="true"' in r.content.decode()

    def test_pagination(self, admin_client, catalog):
        r = admin_client.get(self.url)
        html = r.content.decode()
        assert 'aria-current="page">1<' in html
        assert "?p=2" in html
        r2 = admin_client.get(self.url, {"p": 2})
        assert len(r2.context["cl"].result_list) == 10

    def test_sorting(self, admin_client, catalog):
        r = admin_client.get(self.url, {"o": "2"})  # sku ascending
        skus = [p.sku for p in r.context["cl"].result_list]
        assert skus == sorted(skus)
        assert 'aria-sort="ascending"' in r.content.decode()

    def test_date_hierarchy(self, admin_client, catalog):
        r = admin_client.get(self.url)
        assert 'class="toplinks' in r.content.decode()

    def test_empty_state_for_no_results(self, admin_client, catalog):
        r = admin_client.get(self.url, {"q": "zzz-nothing"})
        assert "No results" in r.content.decode()

    def test_bulk_action(self, admin_client, catalog):
        ids = [p.pk for p in catalog["products"] if p.status == "draft"]
        r = admin_client.post(self.url, {"action": "make_active", "_selected_action": ids, "index": 0}, follow=True)
        assert r.status_code == 200
        assert not Product.objects.filter(pk__in=ids, status="draft").exists()
        assert "marked active" in r.content.decode()
        assert "d-alert d-alert-success" in r.content.decode()

    def test_delete_selected_with_confirmation(self, admin_client, catalog):
        ids = [p.pk for p in catalog["products"][:3]]
        r = admin_client.post(self.url, {"action": "delete_selected", "_selected_action": ids})
        assert r.status_code == 200 and "Delete multiple objects" in r.content.decode()
        assert "d-btn d-btn-error" in r.content.decode()
        r = admin_client.post(self.url, {"action": "delete_selected", "_selected_action": ids, "post": "yes"})
        assert r.status_code == 302
        assert not Product.objects.filter(pk__in=ids).exists()

    def test_list_editable(self, admin_client, catalog):
        sup = catalog["supplier"]
        url = reverse("admin:catalog_supplier_changelist")
        data = {
            "form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "1", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000",
            "form-0-id": str(sup.pk), "_save": "Save",
        }  # active unchecked -> False
        r = admin_client.post(url, data)
        assert r.status_code == 302
        sup.refresh_from_db()
        assert sup.active is False


class TestChangeForm:
    def test_add_with_inline(self, admin_client, catalog):
        url = reverse("admin:catalog_product_add")
        data = product_payload(catalog, **{
            **inline_mgmt("variants", total=1),
            "variants-0-name": "Large", "variants-0-sku": "NEW-1-L", "variants-0-price": "", "variants-0-stock": "3",
        })
        data["tags"] = [catalog["tag"].pk]
        r = admin_client.post(url, data)
        assert r.status_code == 302, r.context["adminform"].form.errors if r.context else r
        p = Product.objects.get(sku="NEW-1")
        assert p.variants.get().sku == "NEW-1-L"
        assert list(p.tags.all()) == [catalog["tag"]]
        assert LogEntry.objects.filter(object_id=str(p.pk), action_flag=ADDITION).exists()

    def test_form_renders_design_system_widgets(self, admin_client, catalog):
        p = catalog["products"][1]
        html = admin_client.get(reverse("admin:catalog_product_change", args=[p.pk])).content.decode()
        assert 'class="vTextField d-input w-full max-w-xl"' in html          # admin class preserved
        assert 'class="vDateField d-input w-full max-w-48"' in html          # DateTimeShortcuts still finds it
        assert 'class="d-select w-full max-w-xl"' in html
        assert "d-textarea" in html
        assert 'class="related-widget-wrapper ds-related-widget' in html    # related links template
        assert 'data-inline-type="tabular"' in html and 'data-inline-type="stacked"' in html
        assert 'aria-label="Name"' in html                                   # tabular inline cells are named
        assert "admin/js/inlines.js" in html                                 # ModelAdmin media untouched
        assert "SelectFilter2.js" in html                                    # filter_horizontal
        assert "<details" in html                                            # collapsible fieldset

    def test_validation_errors(self, admin_client, catalog):
        url = reverse("admin:catalog_product_add")
        r = admin_client.post(url, product_payload(catalog, name="", price="abc"))
        assert r.status_code == 200
        html = r.content.decode()
        assert "errornote d-alert d-alert-error" in html
        assert "d-input-error" in html
        assert 'aria-invalid="true"' in html
        assert 'class="errorlist' in html

    def test_change(self, admin_client, catalog):
        p = catalog["products"][2]
        url = reverse("admin:catalog_product_change", args=[p.pk])
        data = product_payload(catalog, name="Renamed", slug=p.slug, sku=p.sku, price="99.00")
        r = admin_client.post(url, {**data, "_continue": "1"})
        assert r.status_code == 302 and r.url == url
        p.refresh_from_db()
        assert p.name == "Renamed" and p.price == Decimal("99.00")
        assert LogEntry.objects.filter(object_id=str(p.pk), action_flag=CHANGE).exists()

    def test_inline_delete(self, admin_client, catalog):
        p = catalog["products"][3]
        v = Variant.objects.create(product=p, name="S", sku="V-S", stock=1)
        url = reverse("admin:catalog_product_change", args=[p.pk])
        data = product_payload(catalog, name=p.name, slug=p.slug, sku=p.sku, **{
            **inline_mgmt("variants", total=1, initial=1),
            "variants-0-id": v.pk, "variants-0-product": p.pk, "variants-0-name": "S", "variants-0-sku": "V-S",
            "variants-0-stock": "1", "variants-0-DELETE": "on",
        })
        assert admin_client.post(url, data).status_code == 302
        assert not Variant.objects.filter(pk=v.pk).exists()

    def test_delete_view(self, admin_client, catalog):
        p = catalog["products"][4]
        url = reverse("admin:catalog_product_delete", args=[p.pk])
        r = admin_client.get(url)
        assert "Are you sure" in r.content.decode() and "cancel-link" in r.content.decode()
        assert admin_client.post(url, {"post": "yes"}).status_code == 302
        assert not Product.objects.filter(pk=p.pk).exists()
        assert LogEntry.objects.filter(action_flag=DELETION).exists()

    def test_history(self, admin_client, catalog):
        p = catalog["products"][5]
        r = admin_client.get(reverse("admin:catalog_product_history", args=[p.pk]))
        assert r.status_code == 200 and "No history" in r.content.decode()

    def test_popup_add_related(self, admin_client, catalog):
        url = reverse("admin:catalog_supplier_add") + "?_popup=1&_to_field=id"
        r = admin_client.get(url)
        assert r.status_code == 200
        assert "ds-sidebar" not in r.content.decode()  # popups have no shell
        r = admin_client.post(url, {"name": "Popup Co", "country": "CA", "_popup": "1", "_to_field": "id", "active": "on"})
        assert r.status_code == 200 and "popup_response" in r.content.decode()
        assert Supplier.objects.filter(name="Popup Co").exists()

    def test_autocomplete_endpoint(self, admin_client, catalog):
        r = admin_client.get(reverse("admin:autocomplete"), {
            "term": "North", "app_label": "catalog", "model_name": "product", "field_name": "supplier"})
        assert r.status_code == 200 and r.json()["results"][0]["text"] == "Northwind"
