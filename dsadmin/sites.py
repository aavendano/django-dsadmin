"""``DSAdminSite`` — an ``AdminSite`` with design-system layout, navigation,
dashboard, custom pages and global search.

It changes *presentation* only: registration, ``ModelAdmin`` behaviour, URLs,
permissions, CSRF and authentication are Django's.

    from dsadmin import DSAdminSite, widgets as w

    site = DSAdminSite(
        name="backoffice",
        site_header="Backoffice",
        theme="workbench",
        dark_theme=None,
        navigation=[...],
        dashboard=[w.ModelCountCard("catalog.product"), w.RecentActions()],
    )
    site.register(Product, ProductAdmin)

Any key from ``dsadmin.conf.DEFAULTS`` may be passed in lower case.
"""

from __future__ import annotations

from django.contrib import admin
from django.urls import path

from .conf import DEFAULTS, get_setting
from .pages import AdminPage, render_page
from .ui import build_ui
from .widgets import default_dashboard, render_dashboard


class DSAdminSite(admin.AdminSite):
    _dsadmin_base = True
    _dsadmin_site = True
    _ds_search_enabled = True

    def __init__(self, name="admin", **options):
        site_title = options.pop("site_title", None)
        site_header = options.pop("site_header", None)
        site_url = options.pop("site_url", None)
        index_title = options.pop("index_title", None)
        unknown = set(options) - {k.lower() for k in DEFAULTS}
        if unknown:
            raise TypeError(f"Unknown DSAdminSite options: {', '.join(sorted(unknown))}")
        super().__init__(name=name)
        if site_title is not None:
            self.site_title = site_title
        if site_header is not None:
            self.site_header = site_header
        if site_url is not None:
            self.site_url = site_url
        if index_title is not None:
            self.index_title = index_title
        # Constructor branding wins over settings.DSADMIN (most specific first).
        for key, value in (("site_title", site_title), ("site_header", site_header), ("site_url", site_url)):
            if value is not None:
                options[key] = value
        self.ds_options = options
        self._ds_pages: dict[str, AdminPage] = {}

    # -- settings --------------------------------------------------------------
    def ds_setting(self, key):
        return get_setting(key, self)

    # -- context ------------------------------------------------------------------
    def each_context(self, request):
        context = super().each_context(request)
        context["dsadmin"] = build_ui(
            request, self, context.get("available_apps"), has_permission=context.get("has_permission")
        )
        return context

    # -- pages -----------------------------------------------------------------------
    def register_page(self, view=None, *, slug, title, icon="file", group=None, permission=None,
                      order=0, in_navigation=True, path=None):
        """Register a custom page. Usable as a decorator or a plain call."""

        def decorator(v):
            if slug in self._ds_pages:
                raise ValueError(f"Page {slug!r} is already registered on {self.name!r}")
            self._ds_pages[slug] = AdminPage(
                slug=slug, title=title, view=v, icon=icon, group=group, permission=permission,
                order=order, in_navigation=in_navigation, path=path,
            )
            return v

        return decorator(view) if view is not None else decorator

    def unregister_page(self, slug):
        self._ds_pages.pop(slug, None)

    @property
    def pages(self):
        return dict(self._ds_pages)

    def render_page(self, request, template_name, context=None, **kwargs):
        return render_page(self, request, template_name, context, **kwargs)

    # -- urls --------------------------------------------------------------------------
    def get_urls(self):
        urls = super().get_urls()
        extra = [page.urlpattern(self) for page in self._ds_pages.values()]
        extra.append(path("search/", self.admin_view(self.search_view), name="dsadmin_search"))
        # Django's catch-all (final_catch_all_view) must stay last.
        catch_all = [u for u in urls if getattr(u, "name", None) is None and "(?P<url>" in str(getattr(u, "pattern", ""))]
        head = [u for u in urls if u not in catch_all]
        return extra + head + catch_all

    def search_view(self, request):
        from .search import search_view

        return search_view(self, request)

    # -- dashboard ---------------------------------------------------------------------
    def get_dashboard(self, request):
        widgets = self.ds_setting("DASHBOARD")
        if widgets is None:
            widgets = default_dashboard(self)
        return widgets

    def index(self, request, extra_context=None):
        extra_context = dict(extra_context or {})
        extra_context.setdefault("dashboard_html", render_dashboard(self.get_dashboard(request), request, self))
        return super().index(request, extra_context)
