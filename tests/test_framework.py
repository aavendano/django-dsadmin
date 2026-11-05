"""FE-03 / FE-05 — configuration, extensibility and robustness of the framework itself."""

import pytest
from django.contrib import admin
from django.core.checks import Warning as CheckWarning
from django.template import Context, Template
from django.test import override_settings
from django.urls import reverse

from catalog.backoffice import backoffice
from dsadmin import DSAdminSite, PageView
from dsadmin import widgets as w
from dsadmin.apps import check_installed_apps_order, check_settings
from dsadmin.conf import get_setting

pytestmark = pytest.mark.django_db


class TestTwoConfigurations:
    """Same package version, two visually and functionally different admins."""

    def test_default_site_is_dsadmin(self):
        assert isinstance(admin.site, DSAdminSite)

    def test_different_theme_branding_navigation(self, admin_client, catalog):
        a = admin_client.get("/admin/").content.decode()
        b = admin_client.get("/backoffice/").content.decode()
        assert "dsadmin/css/themes/admin.css" in a and "dsadmin/css/themes/nocturne.css" in a
        assert "dsadmin/css/themes/workbench.css" in b and 'id="ds-theme-dark"' not in b
        assert "PLT Admin" in a and "Workbench Ops" in b
        assert "Staging" in b and "Demo" in a
        assert "Inventory report" in b and "Inventory report" not in a
        assert "Low stock" in b  # configured dashboard
        assert 'id="recent-actions-module"' in a  # default dashboard

    def test_same_model_admin_class_on_both_sites(self, admin_client, catalog):
        for site in ("admin", "backoffice"):
            r = admin_client.get(f"/{site}/catalog/category/")
            assert r.status_code == 200 and r.context["cl"].result_count == 2

    def test_custom_navigation_resolves_models_pages_links(self, admin_client):
        html = admin_client.get("/backoffice/catalog/product/").content.decode()
        nav = html[html.index('id="ds-sidebar"'):]
        assert nav.index("Inventory") < nav.index("Insights") < nav.index("Access")
        assert 'href="/backoffice/catalog/product/" class="d-menu-active" aria-current="page"' in nav
        assert 'target="_blank" rel="noopener"' in nav  # external link
        assert "/backoffice/p/inventory-report/" in nav

    def test_constructor_options_override_settings(self):
        assert get_setting("SITE_HEADER", backoffice) == "Workbench Ops"
        assert get_setting("SITE_HEADER", admin.site) == "PLT Admin"
        assert get_setting("THEME", backoffice) == "workbench"


class TestPagesAndIslands:
    def test_class_based_page(self, admin_client, catalog):
        r = admin_client.get("/backoffice/p/inventory-report/")
        assert r.status_code == 200
        html = r.content.decode()
        assert "Stock position by category" in html and "ds-sidebar" in html
        assert "Wellness" in html

    def test_function_page_with_island(self, admin_client, catalog):
        html = admin_client.get("/backoffice/p/stock-board/").content.decode()
        assert 'data-ds-island="stock-board"' in html
        assert "/static/catalog/islands/stock-board.js" in html
        assert '"threshold": 10' in html

    def test_register_page_api(self, rf, admin_user):
        site = DSAdminSite(name="tmp")

        @site.register_page(slug="hello", title="Hello", permission=lambda r: r.user.is_superuser)
        class Hello(PageView):
            pass

        assert "hello" in site.pages
        with pytest.raises(ValueError):
            site.register_page(Hello, slug="hello", title="Again")

    def test_unknown_option_rejected(self):
        with pytest.raises(TypeError):
            DSAdminSite(name="x", colour="red")

    def test_catch_all_stays_last(self):
        urls = backoffice.get_urls()
        assert "(?P<url>" in str(urls[-1].pattern)


class TestWidgets:
    def test_broken_widget_does_not_break_dashboard(self, rf, admin_user):
        def boom(request):
            raise RuntimeError("database on fire")

        request = rf.get("/backoffice/")
        request.user = admin_user
        html = w.render_dashboard([w.MetricCard("Broken", value=boom), w.MetricCard("Fine", value=7)], request, backoffice)
        assert "could not be loaded" in html
        assert "Fine" in html and ">7<" in html.replace(" ", "")

    def test_bar_list_scales(self, rf, admin_user):
        request = rf.get("/")
        request.user = admin_user
        html = w.BarList("Bars", data=[("a", 10), ("b", 5)]).render(request, backoffice)
        assert 'value="100"' in html and 'value="50"' in html

    def test_empty_states(self, rf, admin_user):
        request = rf.get("/")
        request.user = admin_user
        assert "No data yet." in w.BarList("Bars", data=[]).render(request, backoffice)
        assert "Nothing here yet." in w.TableWidget("T", ["A"], rows=[]).render(request, backoffice)


class TestTemplateTags:
    def test_icon_and_badge(self):
        html = Template('{% load dsadmin %}{% ds_icon "box" %}{% ds_badge "Hi" "success" %}').render(Context())
        assert 'href="#ds-i-box"' in html and "d-badge-success" in html

    def test_ds_field_on_plain_form(self):
        from django import forms

        class F(forms.Form):
            name = forms.CharField()
            when = forms.DateField(widget=forms.DateInput(attrs={"class": "keep"}))
            agree = forms.BooleanField()
            kind = forms.ChoiceField(choices=[("a", "A")], widget=forms.RadioSelect)

        f = F(data={})
        html = Template("{% load dsadmin %}{% for f in form %}{% ds_field f %}{% endfor %}").render(Context({"form": f}))
        assert 'class="d-input w-full max-w-xl d-input-error"' in html
        assert 'class="keep d-input w-full max-w-48 d-input-error"' in html
        assert "d-checkbox" in html and "d-radio" in html


class TestChecks:
    def test_wrong_app_order_warns(self):
        with override_settings(INSTALLED_APPS=["dsadmin.apps.AdminConfig", "dsadmin", "django.contrib.auth",
                                               "django.contrib.contenttypes"]):
            msgs = check_installed_apps_order()
        assert any(isinstance(m, CheckWarning) and m.id == "dsadmin.W001" for m in msgs)

    def test_unknown_setting_warns(self):
        with override_settings(DSADMIN={"THEMES": "x"}):
            assert check_settings()[0].id == "dsadmin.W002"

    def test_settings_dark_theme_disabled(self, admin_client):
        with override_settings(DSADMIN={"THEME": "workbench", "DARK_THEME": None}):
            html = admin_client.get("/admin/").content.decode()
        assert 'id="ds-theme-dark"' not in html and "Colour mode" not in html


def test_login_page(client):
    r = client.get(reverse("admin:login"))
    html = r.content.decode()
    assert r.status_code == 200
    assert 'class="d-input w-full max-w-xl"' in html or "d-input" in html
    assert "ds-sidebar" not in html
