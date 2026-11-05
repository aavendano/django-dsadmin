/*!
 * dsadmin.js — progressive enhancements for the dsadmin layout.
 * Everything here is optional: the admin works without JavaScript
 * (except Django's own admin widgets, which already require it).
 */
(function () {
  "use strict";

  var STORE_MODE = "dsadmin:color-mode";
  var STORE_SIDEBAR = "dsadmin:sidebar";

  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch (e) { /* storage disabled */ }
    return null;
  }

  function on(root, event, selector, handler) {
    root.addEventListener(event, function (e) {
      var el = e.target.closest ? e.target.closest(selector) : null;
      if (el && root.contains(el)) handler(e, el);
    });
  }

  /* ---------------------------------------------------------------- colour mode */
  function applyMode(mode) {
    var light = document.getElementById("ds-theme-light");
    var dark = document.getElementById("ds-theme-dark");
    if (!light || !dark) return;
    if (mode === "light") { light.media = "all"; dark.media = "not all"; }
    else if (mode === "dark") { light.media = "not all"; dark.media = "all"; }
    else { mode = "auto"; light.media = "(prefers-color-scheme: light)"; dark.media = "(prefers-color-scheme: dark)"; }
    document.documentElement.dataset.colorMode = mode;
    document.querySelectorAll("[data-ds-color-mode]").forEach(function (btn) {
      var active = btn.getAttribute("data-ds-color-mode") === mode;
      btn.setAttribute("aria-checked", active ? "true" : "false");
      btn.classList.toggle("d-menu-active", active);
    });
  }

  /* ---------------------------------------------------------------- sidebar */
  function setSidebar(collapsed) {
    if (collapsed) document.documentElement.dataset.sidebar = "collapsed";
    else delete document.documentElement.dataset.sidebar;
    store(STORE_SIDEBAR, collapsed ? "collapsed" : null);
    document.querySelectorAll("[data-ds-sidebar-toggle]").forEach(function (b) {
      b.setAttribute("aria-pressed", collapsed ? "true" : "false");
    });
  }

  function syncDrawerToggle() {
    var drawer = document.getElementById("ds-drawer");
    if (!drawer) return;
    document.querySelectorAll("[data-ds-drawer-toggle]").forEach(function (t) {
      t.setAttribute("aria-expanded", drawer.checked ? "true" : "false");
    });
  }

  /* ---------------------------------------------------------------- islands */
  function mountIsland(el) {
    if (el.dataset.dsMounted) return;
    el.dataset.dsMounted = "1";
    var src = el.getAttribute("data-ds-src");
    var propsEl = el.querySelector("script[data-ds-props]");
    var props = {};
    try { props = propsEl ? JSON.parse(propsEl.textContent || "{}") : {}; } catch (e) { props = {}; }
    var csrf = (document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/) || [])[1] || "";
    var ctx = {
      csrfToken: decodeURIComponent(csrf),
      colorMode: document.documentElement.dataset.colorMode || "auto",
      site: document.documentElement.dataset.site || "admin",
    };
    import(src).then(function (mod) {
      var mount = mod.mount || (mod.default && mod.default.mount) || mod.default;
      if (typeof mount !== "function") throw new Error("Island module has no mount() export: " + src);
      var loading = el.querySelector(".ds-island-loading");
      if (loading) loading.remove();
      var target = document.createElement("div");
      target.className = "ds-island-root";
      el.appendChild(target);
      var unmount = mount(target, props, ctx);
      el.removeAttribute("aria-busy");
      if (typeof unmount === "function") el._dsUnmount = unmount;
      el.dispatchEvent(new CustomEvent("ds:island-mounted", { bubbles: true, detail: { name: el.dataset.dsIsland } }));
    }).catch(function (err) {
      el.removeAttribute("aria-busy");
      var loading = el.querySelector(".ds-island-loading");
      if (loading) loading.remove();
      var alert = document.createElement("div");
      alert.setAttribute("role", "alert");
      alert.className = "d-alert d-alert-error text-sm";
      alert.textContent = "This component failed to load.";
      el.appendChild(alert);
      if (window.console) console.error("[dsadmin] island", el.dataset.dsIsland, err);
    });
  }

  function mountIslands(root) {
    (root || document).querySelectorAll("[data-ds-island]").forEach(mountIsland);
  }

  /* ---------------------------------------------------------------- init */
  function init() {
    applyMode(store(STORE_MODE) || document.documentElement.dataset.colorMode || "auto");
    if (document.documentElement.dataset.sidebar === "collapsed") setSidebar(true);
    syncDrawerToggle();

    on(document, "click", "[data-ds-color-mode]", function (e, btn) {
      var mode = btn.getAttribute("data-ds-color-mode");
      store(STORE_MODE, mode);
      applyMode(mode);
      var menu = btn.closest("details");
      if (menu) menu.removeAttribute("open");
    });

    on(document, "click", "[data-ds-sidebar-toggle]", function () {
      setSidebar(document.documentElement.dataset.sidebar !== "collapsed");
    });

    var drawer = document.getElementById("ds-drawer");
    if (drawer) drawer.addEventListener("change", syncDrawerToggle);

    // <label role="button"> elements (drawer, filters) are keyboard-operable.
    on(document, "keydown", "[data-ds-drawer-toggle], [data-ds-label-button]", function (e, el) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        el.click();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (drawer && drawer.checked) { drawer.checked = false; syncDrawerToggle(); }
        document.querySelectorAll("details.d-dropdown[open]").forEach(function (d) { d.removeAttribute("open"); });
      }
      // "/" focuses the global search (unless typing in a field).
      if (e.key === "/" && !/^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName || "")) && !e.target.isContentEditable) {
        var input = document.querySelector("[data-ds-search-input]");
        if (input && input.offsetParent !== null) { e.preventDefault(); input.focus(); }
      }
    });

    // Close open dropdowns when clicking elsewhere.
    document.addEventListener("click", function (e) {
      document.querySelectorAll("details.d-dropdown[open]").forEach(function (d) {
        if (!d.contains(e.target)) d.removeAttribute("open");
      });
    });

    on(document, "click", "[data-ds-dismiss]", function (e, btn) {
      var msg = btn.closest("[data-ds-message]");
      if (msg) msg.remove();
    });

    // Confirmation dialogs: links degrade to their href (a confirmation page).
    on(document, "click", "[data-ds-dialog-open]", function (e, el) {
      var dialog = document.getElementById(el.getAttribute("data-ds-dialog-open"));
      if (dialog && typeof dialog.showModal === "function") {
        e.preventDefault();
        dialog.showModal();
      }
    });
    on(document, "click", "[data-ds-dialog-close]", function (e, el) {
      var dialog = el.closest("dialog");
      if (dialog) dialog.close();
    });

    mountIslands(document);
  }

  /* ---------------------------------------------------------------- Django widget a11y patches
   * Django's SelectFilter2 puts aria-label on a role-less <span>, and the
   * select2 autocomplete combobox has no accessible name. Both run on
   * window "load", so patch afterwards. */
  function patchAdminWidgets() {
    document.querySelectorAll(".selector .help-tooltip[aria-label]:not([role])").forEach(function (el) {
      el.setAttribute("role", "img");
    });
    document.querySelectorAll("select.admin-autocomplete[id]").forEach(function (select) {
      var label = document.querySelector('label[for="' + select.id + '"]');
      var container = select.nextElementSibling;
      var box = container && container.querySelector(".select2-selection");
      if (!label || !box) return;
      if (!label.id) label.id = select.id + "_label";
      // select2 points aria-labelledby at its value text, which is empty when
      // nothing is selected; lead with the field's own label.
      var ids = (box.getAttribute("aria-labelledby") || "").split(/\s+/).filter(Boolean);
      if (ids.indexOf(label.id) === -1) box.setAttribute("aria-labelledby", [label.id].concat(ids).join(" "));
      var rendered = box.querySelector('[role="textbox"]');
      if (rendered && !rendered.hasAttribute("aria-labelledby")) rendered.setAttribute("aria-labelledby", label.id);
    });
  }
  window.addEventListener("load", function () { setTimeout(patchAdminWidgets, 0); });
  document.addEventListener("formset:added", function () { setTimeout(patchAdminWidgets, 0); });

  window.dsadmin = { applyMode: applyMode, setSidebar: setSidebar, mountIslands: mountIslands };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
