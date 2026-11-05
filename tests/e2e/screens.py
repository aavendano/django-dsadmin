"""Capture screenshots of the main admin screens (desktop + mobile, light + dark).

    python tests/e2e/screens.py http://127.0.0.1:8765 out_dir
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "screens")
OUT.mkdir(parents=True, exist_ok=True)
CHROME = "/usr/bin/google-chrome"

PAGES = [
    ("admin-dashboard", "/admin/"),
    ("admin-changelist", "/admin/catalog/product/"),
    ("admin-change", "/admin/catalog/product/{pk}/change/"),
    ("admin-search", "/admin/search/?q=kit"),
    ("bo-dashboard", "/backoffice/"),
    ("bo-changelist", "/backoffice/catalog/product/"),
    ("bo-change", "/backoffice/catalog/product/{pk}/change/"),
    ("bo-report", "/backoffice/p/inventory-report/"),
    ("bo-island", "/backoffice/p/stock-board/"),
]


def login(page, site):
    page.goto(f"{BASE}/{site}/login/")
    if not page.locator("#id_username").count():
        return  # same session already authenticated
    page.fill("#id_username", "admin")
    page.fill("#id_password", "admin")
    page.click("input[type=submit]")
    page.wait_for_load_state("networkidle")


def run(pk, only=None, viewports=("desktop", "mobile"), schemes=("light", "dark")):
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        for vp in viewports:
            size = {"width": 1440, "height": 1000} if vp == "desktop" else {"width": 390, "height": 844}
            for scheme in schemes:
                ctx = browser.new_context(viewport=size, color_scheme=scheme, device_scale_factor=1)
                page = ctx.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                login(page, "admin")
                login(page, "backoffice")
                for name, url in PAGES:
                    if only and name not in only:
                        continue
                    page.goto(BASE + url.format(pk=pk))
                    page.wait_for_load_state("networkidle")
                    page.screenshot(path=str(OUT / f"{name}-{vp}-{scheme}.png"), full_page=(vp == "desktop"))
                if errors:
                    print(vp, scheme, "JS errors:", errors)
                ctx.close()
        browser.close()


if __name__ == "__main__":
    pk = sys.argv[3] if len(sys.argv) > 3 else "48"
    only = sys.argv[4].split(",") if len(sys.argv) > 4 else None
    run(pk, only)
    print("ok")
