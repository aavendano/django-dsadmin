"""django-dsadmin — Django admin presentation framework on the PLT design system.

Public API::

    from dsadmin import DSAdminSite, DSModelAdmin, PageView, object_action
    from dsadmin import widgets as dashboard   # MetricCard, ModelCountCard, ...
    from dsadmin.display import badge, boolean_badge, progress
"""

__version__ = "0.1.0"

__all__ = [
    "DSAdminSite",
    "DSModelAdmin",
    "PageView",
    "object_action",
    "__version__",
]


def __getattr__(name):  # lazy imports keep `import dsadmin` safe before apps load
    if name == "DSAdminSite":
        from .sites import DSAdminSite

        return DSAdminSite
    if name == "DSModelAdmin":
        from .options import DSModelAdmin

        return DSModelAdmin
    if name == "object_action":
        from .options import object_action

        return object_action
    if name == "PageView":
        from .pages import PageView

        return PageView
    raise AttributeError(name)
