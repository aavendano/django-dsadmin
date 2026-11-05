from django.apps import AppConfig
from django.contrib.admin import apps as django_admin_apps
from django.core import checks


class DSAdminAppConfig(AppConfig):
    """The dsadmin app: templates, static files, template tags and checks.

    Must be listed *before* ``django.contrib.admin`` (or
    ``dsadmin.apps.AdminConfig``) so its ``admin/*`` templates take precedence.
    """

    name = "dsadmin"
    label = "dsadmin"
    verbose_name = "DS Admin"
    default = True

    def ready(self):
        checks.register(check_installed_apps_order, checks.Tags.admin)
        checks.register(check_settings, checks.Tags.admin)


class AdminConfig(django_admin_apps.AdminConfig):
    """Drop-in replacement for ``django.contrib.admin`` whose default site is a
    :class:`dsadmin.sites.DSAdminSite`.

    Every existing ``admin.site.register(...)`` / ``@admin.register(...)`` keeps
    working unchanged. Use it in ``INSTALLED_APPS`` instead of
    ``"django.contrib.admin"``.
    """

    default = False  # "dsadmin" itself resolves to DSAdminAppConfig
    default_site = "dsadmin.sites.DSAdminSite"


def check_installed_apps_order(app_configs=None, **kwargs):
    from django.conf import settings

    apps = list(settings.INSTALLED_APPS)
    ds_index = next((i for i, a in enumerate(apps) if a in ("dsadmin", "dsadmin.apps.DSAdminAppConfig")), None)
    admin_index = next(
        (i for i, a in enumerate(apps) if a in ("django.contrib.admin", "dsadmin.apps.AdminConfig")
         or a.endswith(".AdminConfig") and "admin" in a),
        None,
    )
    errors = []
    if ds_index is None and admin_index is not None and "dsadmin.apps.AdminConfig" in apps:
        errors.append(
            checks.Error(
                "'dsadmin' must be in INSTALLED_APPS when using dsadmin.apps.AdminConfig.",
                hint="Add 'dsadmin' before 'dsadmin.apps.AdminConfig'.",
                id="dsadmin.E001",
            )
        )
    if ds_index is not None and admin_index is not None and ds_index > admin_index:
        errors.append(
            checks.Warning(
                "'dsadmin' is listed after the admin app; its templates will not override admin templates.",
                hint="Move 'dsadmin' above 'django.contrib.admin' / 'dsadmin.apps.AdminConfig'.",
                id="dsadmin.W001",
            )
        )
    return errors


def check_settings(app_configs=None, **kwargs):
    from django.conf import settings

    from .conf import DEFAULTS

    errors = []
    user = getattr(settings, "DSADMIN", {}) or {}
    if not isinstance(user, dict):
        return [checks.Error("settings.DSADMIN must be a dict.", id="dsadmin.E002")]
    unknown = sorted(set(user) - set(DEFAULTS))
    if unknown:
        errors.append(
            checks.Warning(
                f"Unknown DSADMIN keys: {', '.join(unknown)}",
                hint=f"Valid keys: {', '.join(sorted(DEFAULTS))}",
                id="dsadmin.W002",
            )
        )
    return errors
