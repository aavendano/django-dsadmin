# Theming — the design system is the authority

dsadmin does not define colours, type, radii or spacing. It compiles
`@playlovetoys/design-system` (daisyUI 5, prefix `d-`, `--plt-*` tokens, PLT
`theme-*` treatments) together with the admin templates:

```
Tailwind 4 + daisyUI 5 (prefix "d-")
  + plt-design-system themes/<theme>.css      ← tokens, typography, brand treatments
  + frontend/src/dsadmin.css                  ← admin shell + Django-markup bridge (no brand values)
  + frontend/src/theme-fixes/<theme>.css      ← temporary, documented upstream gaps (optional)
  scanned: dsadmin/templates, dsadmin/static/dsadmin/js, dsadmin/*.py
  = dsadmin/static/dsadmin/css/themes/<theme>.css
```

Only classes used by the templates end up in the output (~190 KB minified per
theme before gzip).

## Building

```bash
cd frontend
npm install
node build.mjs                                   # admin nocturne workbench unconventionals playlovetoys
node build.mjs --theme broadsheet                # any theme in plt-design-system/themes/
```

The design system is located through `$PLT_DESIGN_SYSTEM`, then
`node_modules/@playlovetoys/design-system`, then sibling checkouts
(`../plt-design-system/…`, `../CSS-Style/plt-design-system/…`).

## A project-specific build

When a project adds its own admin templates with utility classes dsadmin does
not use, or wants a theme that is not built in:

```bash
node build.mjs --theme broadsheet --out ../myproject/static/admin/broadsheet.css \
               --source ../myproject/templates/admin
```

```python
DSADMIN = {"THEME": "admin/broadsheet.css"}       # static path; a URL works too
```

## What `dsadmin.css` contains

- the admin shell (sidebar collapse, skip link, page header, form grid);
- styles for markup Django emits by itself (error lists, sortable headers, inline
  add/delete links, date/time shortcuts, file widgets, `list_editable` inputs);
- a **token bridge** mapping Django admin CSS variables (`--primary`, `--body-bg`,
  `--selected-row`…) to daisyUI tokens so Django's `widgets.css` (calendar, clock,
  selector, related links) and Django-styled third-party templates follow the theme;
- a few unlayered overrides, because daisyUI 5 ships inside the utilities layer
  and some PLT themes style bare `a` elements outside any layer: sidebar/menu link
  colours, link-buttons keep `--btn-fg`, and muted text raised from daisyUI's 60%
  to 78–82% of `base-content` so admin metadata meets 4.5:1.

## Theme fixes (upstream candidates)

`frontend/src/theme-fixes/workbench.css` — the Workbench theme draws badges as
transparent "stamps" but keeps daisyUI's `*-content` text colour, which is meant
for filled badges (1.1:1 contrast). The fix gives stamps their semantic ink.
It should move into `plt-design-system/themes/workbench.css`; delete the file
here when it does.
