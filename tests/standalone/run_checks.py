"""Executed in a subprocess by tests/test_standalone.py (separate settings)."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if os.environ.get("DSADMIN_FROM_REPO", "1") == "1":  # set to 0 to test an installed wheel
    sys.path.insert(1, str(HERE.parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "standalone_project.settings"

import django  # noqa: E402

django.setup()
from django.contrib import admin  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402

from dsadmin.sites import DSAdminSite  # noqa: E402
from shopapp.models import Ticket  # noqa: E402

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)
assert not isinstance(admin.site, DSAdminSite), "standalone must use stock AdminSite"
call_command("check", fail_level="WARNING")

User.objects.create_superuser("s", "s@example.com", "pw")
Ticket.objects.create(title="Printer on fire", priority=3)
c = Client()
c.login(username="s", password="pw")

checks = {
    "/staff/": ["d-drawer", "ds-sidebar", "/staff/shopapp/ticket/", "dsadmin/css/themes/admin.css"],
    "/staff/shopapp/ticket/": ['class="d-table', "Printer on fire", "d-menu"],
    "/staff/shopapp/ticket/add/": ["d-input", "d-checkbox", "d-btn d-btn-primary"],
    "/staff/shopapp/ticket/1/change/": ["Printer on fire", "History"],
}
for url, needles in checks.items():
    r = c.get(url)
    assert r.status_code == 200, (url, r.status_code)
    html = r.content.decode()
    for n in needles:
        assert n in html, (url, n)

r = c.post("/staff/shopapp/ticket/add/", {"title": "New", "priority": "1", "open": "on"})
assert r.status_code == 302, r.status_code
assert Ticket.objects.count() == 2
r = c.post("/staff/shopapp/ticket/", {"action": "delete_selected", "_selected_action": ["1"], "post": "yes"})
assert r.status_code == 302 and Ticket.objects.count() == 1
print("STANDALONE OK")
