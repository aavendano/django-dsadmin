#!/usr/bin/env python
"""Adoption probe: render every ModelAdmin of a project under dsadmin.

Run it from the project root with the project's settings (or an overlay that
adds "dsadmin" + "dsadmin.apps.AdminConfig" to INSTALLED_APPS):

    DJANGO_SETTINGS_MODULE=myproject.settings python /path/to/probe_admin.py [--site admin] [--migrate]

Reports status for index, global search, and changelist/add/change of each
registered model. 403 from a ModelAdmin's own permission hooks is expected and
reported as "denied by ModelAdmin".
"""
import argparse
import os
import sys

sys.path.insert(0, os.getcwd())

import django  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--site", default="admin", help="admin site namespace")
parser.add_argument("--migrate", action="store_true", help="run migrations first (use with a throwaway DB)")
args = parser.parse_args()

django.setup()
from django.contrib import admin  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402
from django.urls import NoReverseMatch, reverse  # noqa: E402

setup_test_environment()
if args.migrate:
    call_command("migrate", verbosity=0)

User = get_user_model()
username_field = User.USERNAME_FIELD
user = User.objects.filter(is_superuser=True).first()
if user is None:
    fields = {username_field: "dsadmin-probe@example.com" if username_field == "email" else "dsadmin-probe",
              "password": "probe"}
    if username_field != "email" and "email" in [f.name for f in User._meta.fields]:
        fields["email"] = "dsadmin-probe@example.com"
    user = User.objects.create_superuser(**fields)

client = Client()
client.force_login(user)
site = next(s for s in [admin.site] + [getattr(m, "admin_site", None) for m in admin.site._registry.values()]
            if s is not None and s.name == args.site)

rows = []


def probe(url, label):
    try:
        r = client.get(url, HTTP_HOST="localhost")
        shell = b"ds-sidebar" in r.content if r.status_code == 200 else None
        rows.append((r.status_code, shell, label, url))
    except Exception as exc:  # noqa: BLE001
        rows.append(("ERR", None, label, f"{url} -> {type(exc).__name__}: {exc}"))


probe(reverse(f"{site.name}:index"), "index")
try:
    probe(reverse(f"{site.name}:dsadmin_search") + "?q=a", "search")
except NoReverseMatch:
    pass
for model, ma in site._registry.items():
    o = model._meta
    for view in ("changelist", "add"):
        try:
            probe(reverse(f"{site.name}:{o.app_label}_{o.model_name}_{view}"), f"{o.label} {view}")
        except NoReverseMatch:
            pass
    obj = model._default_manager.first()
    if obj is not None:
        probe(reverse(f"{site.name}:{o.app_label}_{o.model_name}_change", args=[obj.pk]), f"{o.label} change")

problems = 0
for status, shell, label, url in rows:
    note = ""
    if status == 403:
        note = "denied by ModelAdmin (permission preserved)"
    elif status not in (200, 302) or shell is False:
        note = "PROBLEM"
        problems += 1
    print(f"{status!s:>4}  {'ds' if shell else '  '}  {label:<40} {url} {note}")
print(f"\n{len(site._registry)} ModelAdmins, {len(rows)} URLs, {problems} problems")
sys.exit(1 if problems else 0)
