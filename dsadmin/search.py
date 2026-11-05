"""Global admin search.

Searches every ModelAdmin registered on the site that declares
``search_fields`` and that the user may view or change, using the
ModelAdmin's own ``get_queryset`` and ``get_search_results`` — so custom
querysets, search lookups and row restrictions are respected. Each hit is
also checked with ``has_view_or_change_permission(request, obj)`` for
object-level permission backends.
"""

from django.template.response import TemplateResponse
from django.urls import NoReverseMatch, reverse
from django.utils.http import urlencode

from .conf import get_setting


def search_models(site, request, query, limit=None):
    limit = limit or get_setting("SEARCH_LIMIT", site)
    sections = []
    if not query:
        return sections
    for model, model_admin in site._registry.items():
        if not model_admin.search_fields:
            continue
        if not model_admin.has_view_or_change_permission(request):
            continue
        qs = model_admin.get_queryset(request)
        qs, may_have_duplicates = model_admin.get_search_results(request, qs, query)
        if may_have_duplicates:
            qs = qs.distinct()
        opts = model._meta
        hits = []
        for obj in qs[: limit + 1]:
            if not model_admin.has_view_or_change_permission(request, obj):
                continue
            try:
                url = reverse(f"{site.name}:{opts.app_label}_{opts.model_name}_change", args=[obj.pk])
            except NoReverseMatch:
                url = None
            hits.append({"object": obj, "label": str(obj), "url": url})
        if not hits:
            continue
        try:
            changelist = reverse(f"{site.name}:{opts.app_label}_{opts.model_name}_changelist")
            changelist += "?" + urlencode({"q": query})
        except NoReverseMatch:
            changelist = None
        sections.append(
            {
                "name": opts.verbose_name_plural,
                "app": opts.app_config.verbose_name,
                "hits": hits[:limit],
                "more": len(hits) > limit,
                "changelist_url": changelist,
            }
        )
    sections.sort(key=lambda s: str(s["name"]))
    return sections


def search_view(site, request):
    query = (request.GET.get("q") or "").strip()
    context = site.each_context(request)
    sections = search_models(site, request, query)
    context.update(
        title="Search",
        query=query,
        sections=sections,
        total=sum(len(s["hits"]) for s in sections),
    )
    return TemplateResponse(request, "dsadmin/search.html", context)
