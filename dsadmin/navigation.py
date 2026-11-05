"""Sidebar navigation.

Navigation is declared as plain data (dicts) so it can live in settings::

    DSADMIN = {
        "NAVIGATION": [
            {"label": "Overview", "items": [
                {"label": "Dashboard", "view": "index", "icon": "dashboard"},
                {"page": "reports"},                       # registered AdminPage
            ]},
            {"label": "Catalog", "icon": "box", "items": [
                {"model": "catalog.product"},              # label/url/permission from the admin
                {"model": "catalog.category", "icon": "folder"},
            ]},
            {"apps": "*"},                                 # remaining apps, automatic
            {"label": "Help", "items": [
                {"label": "Docs", "url": "https://example.com", "external": True},
            ]},
        ],
    }

Rules:

* ``model`` items appear only if the model is registered on the site *and* the
  user can view/change it (they are resolved from ``AdminSite.get_app_list``,
  so ModelAdmin permission hooks apply).
* ``page`` items appear only if the page's ``permission`` check passes.
* ``url``/``view`` items accept ``permission`` (a perm string or
  ``callable(request) -> bool``).
* ``{"apps": "*"}`` splices one group per app not already referenced;
  ``{"apps": ["auth", "sites"]}`` limits it to those apps.
* Groups with no visible items are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.urls import NoReverseMatch, reverse

APP_ICONS = {
    "auth": "shield",
    "sites": "external",
    "admin": "history",
}


@dataclass
class NavItem:
    label: str
    url: str
    icon: str | None = None
    badge: Any = None
    external: bool = False
    active: bool = False
    key: str = ""


@dataclass
class NavGroup:
    label: str
    items: list[NavItem] = field(default_factory=list)
    icon: str | None = None
    key: str = ""
    collapsible: bool = True

    @property
    def active(self):
        return any(i.active for i in self.items)


def _check_permission(request, permission) -> bool:
    if permission is None:
        return True
    if callable(permission):
        return bool(permission(request))
    if isinstance(permission, (list, tuple)):
        return request.user.has_perms(permission)
    return request.user.has_perm(permission)


def _resolve(value, request):
    return value(request) if callable(value) else value


class NavigationBuilder:
    def __init__(self, site, request, app_list, site_name=None):
        self.site = site
        self.site_name = site_name or getattr(site, "name", "admin")
        self.request = request
        self.app_list = app_list or []
        self.models = {}
        for app in self.app_list:
            for model in app["models"]:
                key = f"{app['app_label']}.{model['object_name']}".lower()
                self.models[key] = (app, model)
        self.used_models = set()

    # -- items -------------------------------------------------------------
    def model_item(self, spec):
        key = spec["model"].lower()
        if key not in self.models:
            return None
        app, model = self.models[key]
        url = model.get("admin_url")
        if not url:
            return None
        self.used_models.add(key)
        return NavItem(
            label=str(spec.get("label") or model["name"]),
            url=url,
            icon=spec.get("icon"),
            badge=_resolve(spec.get("badge"), self.request),
            key=key,
        )

    def page_item(self, spec):
        pages = getattr(self.site, "_ds_pages", {})
        page = pages.get(spec["page"])
        if page is None or not page.has_permission(self.request):
            return None
        return NavItem(
            label=str(spec.get("label") or page.title),
            url=page.url(self.site),
            icon=spec.get("icon") or page.icon,
            badge=_resolve(spec.get("badge"), self.request),
            key=f"page:{page.slug}",
        )

    def link_item(self, spec):
        if not _check_permission(self.request, spec.get("permission")):
            return None
        url = spec.get("url")
        if url is None and spec.get("view"):
            view = spec["view"]
            if ":" not in view:
                view = f"{self.site_name}:{view}"
            try:
                url = reverse(view, kwargs=spec.get("kwargs") or None)
            except NoReverseMatch:
                return None
        if url is None:
            return None
        return NavItem(
            label=str(spec["label"]),
            url=str(_resolve(url, self.request)),
            icon=spec.get("icon"),
            badge=_resolve(spec.get("badge"), self.request),
            external=bool(spec.get("external")),
            key=spec.get("key") or str(spec["label"]),
        )

    def item(self, spec):
        if isinstance(spec, NavItem):
            return spec
        if "model" in spec:
            return self.model_item(spec)
        if "page" in spec:
            return self.page_item(spec)
        return self.link_item(spec)

    # -- groups --------------------------------------------------------------
    def app_groups(self, apps="*"):
        groups = []
        for app in self.app_list:
            if apps != "*" and app["app_label"] not in apps:
                continue
            items = []
            for model in app["models"]:
                key = f"{app['app_label']}.{model['object_name']}".lower()
                if key in self.used_models or not model.get("admin_url"):
                    continue
                items.append(NavItem(label=str(model["name"]), url=model["admin_url"], key=key))
            if items:
                groups.append(
                    NavGroup(
                        label=str(app["name"]),
                        items=items,
                        icon=APP_ICONS.get(app["app_label"], "folder"),
                        key=f"app:{app['app_label']}",
                    )
                )
        return groups

    def page_groups(self, exclude=()):
        pages = [
            p
            for p in getattr(self.site, "_ds_pages", {}).values()
            if p.slug not in exclude and p.in_navigation and p.has_permission(self.request)
        ]
        grouped: dict[str, list] = {}
        for page in sorted(pages, key=lambda p: (p.order, str(p.title))):
            grouped.setdefault(str(page.group or "Pages"), []).append(page)
        return [
            NavGroup(
                label=label,
                items=[
                    NavItem(label=str(p.title), url=p.url(self.site), icon=p.icon, key=f"page:{p.slug}")
                    for p in items
                ],
                icon="layers",
                key=f"pages:{label}",
            )
            for label, items in grouped.items()
        ]

    def build(self, spec):
        if spec is None:
            groups = self.page_groups() + self.app_groups()
        else:
            groups = []
            deferred = []  # app splices resolve after explicit model items are claimed
            referenced_pages = set()
            for group_spec in spec:
                if "apps" in group_spec:
                    placeholder = NavGroup(label="__apps__")
                    groups.append(placeholder)
                    deferred.append((placeholder, group_spec["apps"]))
                    continue
                if not _check_permission(self.request, group_spec.get("permission")):
                    continue
                items = []
                for item_spec in group_spec.get("items", []):
                    if isinstance(item_spec, dict) and "page" in item_spec:
                        referenced_pages.add(item_spec["page"])
                    item = self.item(item_spec)
                    if item is not None:
                        items.append(item)
                groups.append(
                    NavGroup(
                        label=str(group_spec.get("label", "")),
                        items=items,
                        icon=group_spec.get("icon"),
                        key=group_spec.get("key") or str(group_spec.get("label", "")),
                        collapsible=group_spec.get("collapsible", True),
                    )
                )
            expanded = []
            for g in groups:
                match = next((d for d in deferred if d[0] is g), None)
                if match:
                    expanded.extend(self.app_groups(match[1]))
                else:
                    expanded.append(g)
            groups = expanded
        groups = [g for g in groups if g.items]
        self.mark_active(groups)
        return groups

    def mark_active(self, groups):
        """Highlight the item whose URL is the longest prefix of the current path.

        The site index only matches exactly (every admin URL starts with it).
        """
        path = self.request.path
        index = self._index_url()
        best, best_len = None, -1
        for g in groups:
            for item in g.items:
                if item.external or not item.url:
                    continue
                url = item.url.split("?")[0]
                matches = path == url or (url != index and url.endswith("/") and path.startswith(url))
                if matches and len(url) > best_len:
                    best, best_len = item, len(url)
        if best is not None:
            best.active = True

    def _index_url(self):
        try:
            return reverse(f"{self.site_name}:index")
        except NoReverseMatch:
            return "/"


def build_navigation(site, request, app_list, spec=None, site_name=None):
    spec = _resolve(spec, request)
    return NavigationBuilder(site, request, app_list, site_name=site_name).build(spec)
