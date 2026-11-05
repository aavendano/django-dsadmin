"""RF-07 — access control, permissions, CSRF and output escaping."""

import json

import pytest
from django.contrib.auth.models import Permission
from django.template import Context, Template
from django.test import Client
from django.urls import reverse

from catalog.models import Product

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("url", [
    "/admin/", "/admin/catalog/product/", "/admin/search/?q=a",
    "/backoffice/", "/backoffice/p/inventory-report/", "/backoffice/p/stock-board/",
])
def test_anonymous_is_sent_to_login(client, url):
    r = client.get(url)
    assert r.status_code == 302 and "/login/" in r.url


def test_non_staff_cannot_enter(client, django_user_model):
    user = django_user_model.objects.create_user("joe", password="pw")
    client.force_login(user)
    assert client.get("/admin/").status_code == 302
    assert client.get("/backoffice/p/inventory-report/").status_code == 302


class TestEditorPermissions:
    def test_navigation_only_lists_permitted_models(self, client, editor):
        client.force_login(editor)
        html = client.get("/admin/").content.decode()
        nav = html[html.index('id="ds-sidebar"'):]
        assert "/admin/catalog/product/" in nav
        assert "/admin/catalog/category/" in nav
        assert "/admin/catalog/supplier/" not in nav
        assert "/admin/auth/" not in nav

    def test_model_permissions_enforced(self, client, editor, catalog):
        client.force_login(editor)
        assert client.get(reverse("admin:catalog_product_add")).status_code == 403
        assert client.get(reverse("admin:catalog_supplier_changelist")).status_code == 403
        p = catalog["products"][0]
        assert client.get(reverse("admin:catalog_product_delete", args=[p.pk])).status_code == 403
        html = client.get(reverse("admin:catalog_product_changelist")).content.decode()
        assert "Add product" not in html  # object tools hidden without add permission

    def test_dashboard_widgets_respect_permissions(self, client, editor, catalog):
        client.force_login(editor)
        html = client.get("/backoffice/").content.decode()
        assert 'aria-label="Products"' in html          # ModelCountCard for a permitted model
        assert 'aria-label="Suppliers"' not in html     # hidden: no view_supplier
        assert "New supplier" not in html               # QuickActions add link hidden
        assert "New product" not in html                # editor cannot add products

    def test_search_respects_permissions(self, client, editor, catalog):
        client.force_login(editor)
        r = client.get("/admin/search/", {"q": "North"})
        names = [str(s["name"]) for s in r.context["sections"]]
        assert "suppliers" not in names
        r = client.get("/admin/search/", {"q": "Velvet"})
        assert [str(s["name"]) for s in r.context["sections"]] == ["products"]

    def test_custom_page_permission(self, client, viewer):
        client.force_login(viewer)
        assert client.get("/backoffice/p/inventory-report/").status_code == 200   # needs view_product
        assert client.get("/backoffice/p/stock-board/").status_code == 403        # needs change_product
        html = client.get("/backoffice/").content.decode()
        assert "/backoffice/p/stock-board/" not in html                           # and is not linked


class TestObjectActions:
    def url(self, product, action):
        return reverse("backoffice:catalog_product_object_action", args=[product.pk, action])

    def test_requires_permission(self, client, editor, catalog):
        p = catalog["products"][0]  # draft
        client.force_login(editor)  # has change_product but not publish_product
        assert client.post(self.url(p, "publish")).status_code == 403
        editor.user_permissions.add(Permission.objects.get(codename="publish_product"))
        assert client.post(self.url(p, "publish")).status_code == 302
        p.refresh_from_db()
        assert p.status == "active"

    def test_requires_post_and_csrf(self, admin_user, catalog):
        p = catalog["products"][0]
        c = Client(enforce_csrf_checks=True)
        c.force_login(admin_user)
        assert c.get(self.url(p, "publish")).status_code == 405        # no confirmation -> POST only
        assert c.post(self.url(p, "publish")).status_code == 403       # missing CSRF token
        p.refresh_from_db()
        assert p.status == "draft"

    def test_confirmation_flow(self, admin_client, catalog):
        p = catalog["products"][1]
        r = admin_client.get(self.url(p, "archive_product"))
        assert r.status_code == 200 and "Archived products disappear" in r.content.decode()
        r = admin_client.post(self.url(p, "archive_product"), {"next": "https://evil.example/"})
        assert r.status_code == 302 and r.url.startswith("/backoffice/")  # open redirect blocked
        p.refresh_from_db()
        assert p.status == "archived"

    def test_unknown_action_is_404(self, admin_client, catalog):
        assert admin_client.post(self.url(catalog["products"][0], "delete_everything")).status_code == 404

    def test_row_actions_rendered_with_sibling_form(self, admin_client, catalog):
        html = admin_client.get("/backoffice/catalog/product/").content.decode()
        assert 'id="ds-row-action-form"' in html
        assert 'form="ds-row-action-form"' in html

    def test_change_form_buttons(self, admin_client, catalog):
        p = catalog["products"][0]
        html = admin_client.get(f"/backoffice/catalog/product/{p.pk}/change/").content.decode()
        assert 'data-ds-dialog-open="ds-action-archive_product"' in html
        assert '<dialog id="ds-action-archive_product"' in html
        assert "csrfmiddlewaretoken" in html


def test_csrf_enforced_on_admin_forms(admin_user, catalog):
    c = Client(enforce_csrf_checks=True)
    c.force_login(admin_user)
    p = catalog["products"][0]
    r = c.post(reverse("admin:catalog_product_delete", args=[p.pk]), {"post": "yes"})
    assert r.status_code == 403
    assert Product.objects.filter(pk=p.pk).exists()


def test_island_props_cannot_break_out_of_script(rf):
    t = Template('{% load dsadmin %}{% ds_island "x" src="a/b.js" props=props %}')
    html = t.render(Context({"props": {"evil": "</script><script>alert(1)</script>"}, "request": rf.get("/")}))
    assert "</script><script>" not in html
    payload = html.split("data-ds-props>")[1].split("</script>")[0]
    assert json.loads(payload)["evil"].startswith("</script>")


def test_user_content_is_escaped(admin_client, catalog):
    p = catalog["products"][0]
    p.name = '<img src=x onerror="alert(1)">'
    p.save()
    for url in ["/admin/catalog/product/", f"/admin/catalog/product/{p.pk}/change/", "/admin/search/?q=img"]:
        html = admin_client.get(url).content.decode()
        assert '<img src=x onerror="alert(1)">' not in html
