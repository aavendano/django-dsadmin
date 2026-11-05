# Extensions

## JavaScript islands

An island is an independent ES module mounted inside a server-rendered admin
page. The admin stays a multi-page Django app; islands are for the screens that
genuinely need client-side interaction (an editor, a board, a live chart).

```django
{% load dsadmin %}
{% ds_island "stock-board" src="catalog/islands/stock-board.js" props=island_props %}
```

```js
// static/catalog/islands/stock-board.js
export function mount(element, props, context) {
  // context: { csrfToken, colorMode, site }
  element.innerHTML = `<button class="d-btn d-btn-primary">…</button>`;
  return () => { element.innerHTML = ""; };      // optional unmount
}
```

- `props` are serialised as JSON inside `<script type="application/json">` with `<`, `>`, `&`
  escaped — user data cannot break out of the script element.
- While the module loads the island shows a `d-loading` spinner (`aria-busy`); if the import
  fails or `mount` is missing it shows a `d-alert-error` and logs to the console.
- Islands are found on `DOMContentLoaded`; call `window.dsadmin.mountIslands(root)` for markup
  inserted later.
- Use design-system classes and the island follows the active theme and colour mode.

### React / Puck

Build the island as an ES module (Vite library mode) into a static directory
and export `mount`:

```js
// src/puck-island.jsx  ->  vite build --lib  ->  static/myapp/puck-island.js
import { createRoot } from "react-dom/client";
import { Puck } from "@puckeditor/core";
import config from "./puck.config";

export function mount(el, props, ctx) {
  const root = createRoot(el);
  root.render(
    <Puck config={config} data={props.data} onPublish={(data) =>
      fetch(props.saveUrl, { method: "POST", headers: { "X-CSRFToken": ctx.csrfToken,
        "Content-Type": "application/json" }, body: JSON.stringify(data) })} />
  );
  return () => root.unmount();
}
```

```python
@site.register_page(slug="home-editor", title="Home editor", permission="content.change_page")
def home_editor(request, site):
    return site.render_page(request, "content/home_editor.html",
                            {"props": {"data": load_home(), "saveUrl": reverse("content:save_home")}},
                            title="Home editor")
```

React is only loaded on that page. The save endpoint is a normal Django view
(protect it with `staff_member_required` / permissions and CSRF).

### Islands on the dashboard

```python
w.IslandWidget("Live orders", name="orders", src="orders/live.js", props=lambda request: {...})
```

## Overriding templates

dsadmin's templates are ordinary admin templates. Override them the Django way:

- per project: `templates/admin/change_list.html` (project `DIRS` win over app templates);
- per app / model: `admin/<app_label>/change_form.html`, `admin/<app>/<model>/change_list.html`;
- per ModelAdmin: `change_form_template`, `change_list_template`, … (`{% extends "admin/change_form.html" %}`
  to keep dsadmin's markup and add to its blocks).

Layout fragments live in `dsadmin/layout/` (`navbar.html`, `sidebar.html`,
`messages.html`, `user_menu.html`, `theme_toggle.html`); widgets in
`dsadmin/widgets/`; reusable components in `dsadmin/components/`.

## Extra assets

`EXTRA_CSS` / `EXTRA_JS` add stylesheets and ES modules to every admin page;
`ModelAdmin.Media` keeps working per model.
