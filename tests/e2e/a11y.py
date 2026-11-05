"""Run axe-core (WCAG 2.x A/AA rules) against the main admin screens.

    AXE_JS=/path/to/axe.min.js python tests/e2e/a11y.py http://127.0.0.1:8765
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
AXE = open(os.environ["AXE_JS"]).read()
PK = os.environ.get("PK", "48")
PAGES = [
    "/admin/", "/admin/catalog/product/", f"/admin/catalog/product/{PK}/change/", "/admin/catalog/product/add/",
    "/admin/search/?q=kit", f"/admin/catalog/product/{PK}/delete/",
    "/backoffice/", "/backoffice/catalog/product/", f"/backoffice/catalog/product/{PK}/change/",
    "/backoffice/p/inventory-report/", "/backoffice/p/stock-board/",
]


def main():
    total = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        for scheme in ("light", "dark"):
            page = browser.new_page(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
            page.goto(f"{BASE}/admin/login/")
            # login page itself
            page.add_script_tag(content=AXE)
            r = page.evaluate("axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']})")
            total += report(f"[{scheme}] /admin/login/", r)
            page.fill("#id_username", "admin"); page.fill("#id_password", "admin"); page.click("input[type=submit]")
            page.wait_for_load_state("networkidle")
            for url in PAGES:
                page.goto(BASE + url); page.wait_for_load_state("networkidle")
                page.add_script_tag(content=AXE)
                r = page.evaluate("axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']})")
                total += report(f"[{scheme}] {url}", r)
            page.close()
        browser.close()
    print("TOTAL violations:", total)
    return total


def report(label, result):
    v = result["violations"]
    if v:
        print(label)
        for item in v:
            nodes = item["nodes"]
            print(f"   {item['id']} ({item['impact']}) x{len(nodes)}: {nodes[0]['target']} :: {nodes[0]['failureSummary'][:160]!r}")
    return sum(len(i["nodes"]) for i in v)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
