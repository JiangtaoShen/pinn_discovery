# build/ — showcase generator

This repo (`pinn_discovery`) is the **presentation layer**. The experiments,
data, and base dashboards live in a separate repo:

```
D:\discover_claudecode
├── apps/<app>/problem.md      # problem description + TRAIN_TIME (prescribed runtime)
├── apps/<app>/viz.json        # problem name / metric
└── runs/<app>/dashboard.html  # base dashboard, built by `discover dashboard <app>`
```

`build.py` reads those, applies the showcase styling, and regenerates every page here.

## Update workflow

1. Run / extend an experiment in `D:\discover_claudecode` and rebuild its dashboard:
   `discover dashboard <app>` (writes `runs/<app>/dashboard.html`).
2. Regenerate this site:
   ```
   py build/build.py
   ```
3. Deploy:
   ```
   git add -A && git commit -m "Update showcase" && git push
   ```
   GitHub Pages redeploys https://jiangtaoshen.github.io/pinn_discovery/ automatically.

## What is automatic vs. configured

Auto-extracted on every build (no edits needed):
- **tree node count** and **best metric** — from the dashboard header
- **prescribed runtime** — from `apps/<app>/problem.md` (`capped at **N s` / `TRAIN_TIME`)

Configured in `cases.json` (presentation only):
- `app` → `slug` (source app name → folder on this site)
- `title` (dashboard `<title>` + header, `PINN Discovery of …`)
- `card_title`, `card_tag` (overview card; `Re = NNNN` is auto-bolded blue)
- `menu_label`, `menu_desc` (dropdown switcher; ` · N nodes` appended automatically)
- **order** = array order in `cases.json`

## Adding a new case (e.g. KdV)

1. Make sure `D:\discover_claudecode\runs\pinnkdv\dashboard.html` exists.
2. Add an entry to `cases.json` (`app: "pinnkdv"`, `slug: "kdv"`, titles/tags, in the
   position you want). Runtime + stats are read automatically.
3. `py build/build.py` → commit → push.

A case whose dashboard is missing is skipped with a `SKIP` notice, so it's safe to
pre-add config before the run exists.

## Transformation applied to each base dashboard

- `<title>` and the `#problem-link` header → `PINN Discovery of …`
- a fixed top-right **dropdown switcher** injected after `<body>` (links to the other
  cases + the Overview, current one marked active)
- written to `<slug>/index.html`

The base dashboards themselves are **not** committed here — they are regenerated
artifacts; only the transformed pages + this toolkit live in the repo.
