# -*- coding: utf-8 -*-
"""
Regenerate the PINN Discovery showcase from the experiment repo.

Reads base dashboards from   <source_root>/runs/<app>/dashboard.html
and per-case metadata from    <source_root>/apps/<app>/problem.md
(see build/cases.json), then writes the presentation pages into this repo:

  <slug>/index.html   transformed dashboard  (retitled + dropdown switcher)
  index.html          overview landing page  (cards with live stats)

Auto-extracted per case:
  - tree node count + best metric  -> from the dashboard header
  - prescribed runtime (TRAIN_TIME) -> from apps/<app>/problem.md

Everything else (display titles, card text, order) lives in cases.json.

Usage:
  py build/build.py
then commit & push to deploy via GitHub Pages.
"""
import os, re, json, sys, hashlib

try:
    import numpy as _np
    import matplotlib as _mpl
    _mpl.use("Agg")
    import matplotlib.pyplot as _plt
    HAVE_MPL = True
    _MPL_ERR = ""
except Exception as _e:          # pragma: no cover
    HAVE_MPL = False
    _MPL_ERR = str(_e)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # E:\pinn_discovery_show
CFG  = json.load(open(os.path.join(HERE, "cases.json"), encoding="utf-8"))

SRC   = CFG["source_root"].replace("\\", "/")
SITE  = CFG["site_title"]
CASES = CFG["cases"]

NUMWORD = {1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",
           8:"eight",9:"nine",10:"ten",11:"eleven",12:"twelve"}

# ---------------------------------------------------------------- dropdown switcher
SWITCHER_STYLE = """
<style>
  .page-switcher{position:fixed;top:18px;right:18px;z-index:99999;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;}
  .page-switcher details{position:relative;}
  .page-switcher summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:7px;
    background:#1f2933;color:#fff;padding:8px 14px;border-radius:9px;font-size:13px;font-weight:600;
    box-shadow:0 2px 8px rgba(15,23,42,.22);user-select:none;white-space:nowrap;}
  .page-switcher summary::-webkit-details-marker{display:none;}
  .page-switcher summary::marker{content:"";}
  .page-switcher summary .chev{transition:transform .15s ease;font-size:11px;opacity:.85;}
  .page-switcher details[open] summary .chev{transform:rotate(180deg);}
  .page-switcher summary:hover{background:#2d3a47;}
  .page-switcher .ps-menu{position:absolute;right:0;top:calc(100% + 8px);background:#fff;
    border:1px solid #e2e6ea;border-radius:12px;box-shadow:0 12px 32px rgba(15,23,42,.18);
    min-width:264px;padding:7px;display:flex;flex-direction:column;gap:2px;}
  .page-switcher .ps-head{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
    color:#9aa3ad;padding:7px 10px 5px;}
  .page-switcher .ps-menu a{display:flex;flex-direction:column;gap:1px;padding:9px 11px;border-radius:8px;
    color:#1f2933;text-decoration:none;font-size:13.5px;line-height:1.25;}
  .page-switcher .ps-menu a small{color:#6b7280;font-size:11.5px;font-weight:400;}
  .page-switcher .ps-menu a[href]:hover{background:#f0f4f8;}
  .page-switcher .ps-menu a.active{background:#eaf4ff;color:#0b66c3;cursor:default;}
  .page-switcher .ps-menu a.active small{color:#5a93c7;}
  .page-switcher .ps-sep{height:1px;background:#eef1f4;margin:5px 4px;}
  .page-switcher .ps-home{font-weight:600;}
</style>
"""

def build_nav(cur, cases):
    rows = []
    for c in cases:
        sub = "%s · %s nodes" % (c["menu_desc"], c["nodes"])
        if c["slug"] == cur:
            rows.append('      <a class="active" aria-current="page">%s<small>%s</small></a>'
                        % (c["menu_label"], sub))
        else:
            rows.append('      <a href="../%s/index.html">%s<small>%s</small></a>'
                        % (c["slug"], c["menu_label"], sub))
    return (
        '<nav class="page-switcher" aria-label="Switch PINN problem">\n'
        '  <details>\n'
        '    <summary>Switch problem <span class="chev">▾</span></summary>\n'
        '    <div class="ps-menu">\n'
        '      <div class="ps-head">' + SITE + '</div>\n'
        + "\n".join(rows) + "\n"
        '      <div class="ps-sep"></div>\n'
        '      <a class="ps-home" href="../index.html">⌂ Overview</a>\n'
        '    </div>\n'
        '  </details>\n'
        '</nav>'
    )

NAV_RE = re.compile(r'<nav class="page-switcher".*?</nav>', re.S)

# ---------------------------------------------------------------- overview page
OV_CSS = """  :root{
    --ink:#1f2933; --muted:#6b7280; --line:#e2e4e8; --bg:#eeeeee;
    --accent:#1f6feb; --chip:#eef2f7;
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;min-height:100%;color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;}
  body{background:
    radial-gradient(1100px 520px at 85% -5%, #e0ebfa 0%, rgba(238,238,238,0) 60%),
    radial-gradient(900px 460px at -10% 30%, #e8e6f7 0%, rgba(238,238,238,0) 55%),
    var(--bg);}
  .wrap{max-width:1120px;margin:0 auto;padding:64px 28px 80px;}
  header.page{margin-bottom:40px;}
  .eyebrow{font-size:15px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);}
  h1{font-size:40px;line-height:1.12;margin:12px 0 10px;font-weight:750;letter-spacing:-.01em;}
  .lede{font-size:17px;color:var(--muted);max-width:680px;line-height:1.55;margin:0;}

  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:22px;margin-top:40px;}
  @media (max-width:760px){.grid{grid-template-columns:1fr;} h1{font-size:32px;}}

  a.card{position:relative;display:flex;flex-direction:row;gap:18px;align-items:stretch;text-decoration:none;color:inherit;
    background:#fff;border-radius:16px;padding:24px 24px 22px;border:1px solid transparent;
    box-shadow:0 2px 10px rgba(15,23,42,.10),0 1px 3px rgba(15,23,42,.06);
    transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease;}
  a.card:hover{transform:translateY(-4px);
    box-shadow:0 14px 34px rgba(15,23,42,.16),0 3px 8px rgba(15,23,42,.08);
    border-color:#d4e2f7;}
  .card-main{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:14px;}
  .thumb{flex:0 0 auto;align-self:flex-start;margin-top:26px;width:128px;height:128px;border-radius:12px;overflow:hidden;
    background:#1b1f3a;box-shadow:inset 0 0 0 1px rgba(15,23,42,.12);}
  .thumb img{width:100%;height:100%;display:block;object-fit:cover;transition:transform .25s ease;}
  a.card:hover .thumb img{transform:scale(1.045);}
  @media (max-width:760px){.thumb{width:104px;height:104px;}}

  a.card.wide{grid-column:1 / -1;}
  a.card.wide .card-main{flex:1 1 auto;}
  a.card.wide .thumb{flex:0 0 auto;width:auto;height:128px;align-self:center;margin-top:0;margin-right:40px;}
  a.card.wide .thumb img{width:auto;height:100%;}
  @media (max-width:760px){
    a.card.wide{flex-direction:column;}
    a.card.wide .thumb{width:100%;height:auto;margin-right:0;}
    a.card.wide .thumb img{width:100%;height:auto;}
  }

  .card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;}
  .idx{font-size:15px;font-weight:700;color:#fff;background:var(--ink);
    width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;}
  .arrow{position:absolute;top:22px;right:24px;color:var(--muted);font-size:20px;transition:transform .16s ease,color .16s ease;}
  a.card:hover .arrow{transform:translateX(4px);color:var(--accent);}

  .ctitle{font-size:20px;font-weight:700;margin:0;line-height:1.2;}
  .ctag{font-size:15px;color:var(--muted);margin:4px 0 0;}
  .ctag .re{color:var(--accent);font-weight:700;}

  .stats{display:flex;gap:10px;margin-top:4px;flex-wrap:wrap;}
  .stat{background:var(--chip);border-radius:9px;padding:8px 12px;line-height:1.15;}
  .stat .k{display:block;font-size:15px;font-weight:700;letter-spacing:.02em;color:var(--muted);}
  .stat .v{display:block;font-size:15px;font-weight:700;color:var(--ink);
    font-feature-settings:"tnum";margin-top:2px;}
  .stat .v.good{color:var(--accent);}

  .soon{margin-top:26px;padding:24px;border:1.5px dashed #cfd6dd;border-radius:16px;text-align:center;
    color:var(--muted);font-size:15px;font-weight:600;background:rgba(255,255,255,.45);}"""

def highlight_re(tag):
    return re.sub(r"(Re = \d+)", r'<span class="re">\1</span>', tag)

def card_html(c, idx):
    thumb = ""
    fp = os.path.join(ROOT, c["slug"], "field.png")
    if os.path.isfile(fp):
        ver = hashlib.md5(open(fp, "rb").read()).hexdigest()[:8]   # cache-bust when the image changes
        style = ' style="height:%dpx"' % c["thumb_h"] if c.get("thumb_h") else ""
        thumb = ('        <div class="thumb"%s><img src="./%s/field.png?v=%s" '
                 'alt="%s reference solution field" loading="lazy"></div>\n'
                 % (style, c["slug"], ver, c["card_title"]))
    cls = "card wide" if c.get("wide") else "card"
    return (
        '      <a class="%s" href="./%s/index.html">\n' % (cls, c["slug"]) +
        '        <div class="card-main">\n'
        '          <div class="card-top">\n'
        '            <span class="idx">%d</span>\n' % idx +
        '            <span class="arrow">&rarr;</span>\n'
        '          </div>\n'
        '          <div>\n'
        '            <p class="ctitle">%s</p>\n' % c["card_title"] +
        '            <p class="ctag">%s</p>\n' % highlight_re(c["card_tag"]) +
        '          </div>\n'
        '          <div class="stats">\n'
        '            <span class="stat"><span class="k">Tree</span><span class="v">%s nodes</span></span>\n' % c["nodes"] +
        '            <span class="stat"><span class="k">Runtime</span><span class="v">%s s</span></span>\n' % c["runtime"] +
        '            <span class="stat"><span class="k">Best %s</span><span class="v good">%s</span></span>\n' % (c["metric"], c["rrmse"]) +
        '          </div>\n'
        '        </div>\n'
        + thumb +
        '      </a>'
    )

def build_overview(cases):
    nword = NUMWORD.get(len(cases), str(len(cases)))
    cards = "\n\n".join(card_html(c, i + 1) for i, c in enumerate(cases))
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="description" content="Fully automated PINN discovery via tree search over a curated '
        'knowledge base — ' + nword + ' PDE benchmark case studies with full search trees and convergence history.">\n'
        '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' '
        'viewBox=\'0 0 64 64\'%3E%3Crect width=\'64\' height=\'64\' rx=\'14\' fill=\'%231f6feb\'/%3E'
        '%3Cpath d=\'M8 38c6-14 10-14 16 0s10 14 16 0 10-14 16 0\' fill=\'none\' stroke=\'%23fff\' '
        'stroke-width=\'6\' stroke-linecap=\'round\'/%3E%3C/svg%3E">\n'
        '<title>' + SITE + ' · Overview</title>\n<style>\n' + OV_CSS + '\n</style>\n'
        '</head>\n<body>\n  <div class="wrap">\n    <header class="page">\n'
        '      <div class="eyebrow">Physics-Informed Neural Networks</div>\n'
        '      <h1>' + SITE + '</h1>\n'
        '      <p class="lede">Fully automated ' + SITE + ' driven by tree search over a curated knowledge base.\n'
        '        Rather than tuning PINN components in isolation, it designs a complete PINN method in a single pass —\n'
        '        loss formulation, network architecture, and training strategy together.\n'
        '        The ' + nword + ' case studies below demonstrate the approach.\n'
        '        Each dashboard shows the full search tree, knowledge matrix, and convergence history.</p>\n'
        '    </header>\n\n    <div class="grid">\n\n'
        + cards +
        '\n\n    </div>\n\n'
        '    <div class="soon">More case studies coming soon…</div>\n'
        '  </div>\n</body>\n</html>\n'
    )

# ---------------------------------------------------------------- extraction helpers
def read_runtime(app):
    p = os.path.join(SRC, "apps", app, "problem.md")
    if not os.path.isfile(p):
        return "?"
    t = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"capped at \*\*\s*([0-9.]+)\s*s", t) or re.search(r"TRAIN_TIME\s*=\s*([0-9.]+)", t)
    if not m:
        return "?"
    v = float(m.group(1))
    return str(int(v)) if v == int(v) else ("%g" % v)

def extract_stats(html):
    nodes = re.search(r"tree:\s*<code>(\d+)</code>\s*nodes", html)
    met   = re.search(r"best\s+([A-Za-z]+)\s*<code>([0-9.eE+\-]+)</code>", html)
    nodes = nodes.group(1) if nodes else "?"
    metric = met.group(1) if met else "rRMSE"
    rr = ("%.5f" % float(met.group(2))) if met else "?"
    return nodes, metric, rr

# ---------------------------------------------------------------- reference-field thumbnail
def _render_smoke(case, ref, out, dpi=200):
    """Wildfire-smoke tile: u(t,x,y) snapshots at +24/+48/+72 h on the lon/lat map
    (Quebec, June 2023), fire-source marker, arrows between the three panels."""
    from matplotlib.colors import PowerNorm
    z = _np.load(ref)
    X, u = z["X"], z["u"].reshape(-1)
    tu, xu, yu = _np.unique(X[:, 0]), _np.unique(X[:, 1]), _np.unique(X[:, 2])
    G = _np.full((len(tu), len(yu), len(xu)), _np.nan, dtype=_np.float32)
    G[_np.searchsorted(tu, X[:, 0]), _np.searchsorted(yu, X[:, 2]), _np.searchsorted(xu, X[:, 1])] = u
    LON0, LON1, LAT0, LAT1 = -88, -58, 37, 56        # physical domain (problem.md)
    lon, lat = LON0 + xu * (LON1 - LON0), LAT0 + yu * (LAT1 - LAT0)
    norm = PowerNorm(0.45, vmin=0, vmax=float(_np.nanmax(G)))   # lift the faint plume tail
    fire = (-76.88, 49.00)                           # argmax of the GFAS emission field
    nyc = (-74.01, 40.71)                            # New York reference marker
    fig = _plt.figure(figsize=(5.4, 1.2234), dpi=dpi)  # same total aspect as the NACA tile (~4.41:1)
    gs = fig.add_gridspec(1, 3, left=0.058, right=0.995, top=0.965, bottom=0.13, wspace=0.06)
    for i, h in enumerate((24, 48, 72)):
        ax = fig.add_subplot(gs[0, i])
        ax.pcolormesh(lon, lat, G[int(round(h / 72 * (len(tu) - 1)))],
                      cmap="turbo", norm=norm, shading="gouraud")
        ax.set_xlim(LON0, LON1); ax.set_ylim(LAT0, LAT1)
        ax.set_xticks([-85, -75, -65])
        ax.set_xticklabels(["85°W", "75°W", "65°W"], fontsize=6.5)
        ax.set_yticks([40, 45, 50, 55])
        if i == 0:
            ax.set_yticklabels(["40°N", "45°N", "50°N", "55°N"], fontsize=6.5)
        else:
            ax.tick_params(labelleft=False)
        ax.tick_params(length=1.5, pad=1.5, colors="#475569")
        ax.set_axisbelow(False)                       # graticule over the field
        ax.grid(True, color="white", alpha=0.45, linewidth=0.55, linestyle="--")
        for s in ax.spines.values():
            s.set_color("#94a3b8"); s.set_linewidth(0.6)
        ax.text(0.045, 0.93, "+%d h" % h, transform=ax.transAxes, fontsize=8,
                fontweight="bold", color="#0f172a", va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="none", alpha=0.92))
        ax.plot(*fire, marker="^", ms=4.5, mfc="#ff3b30", mec="white", mew=0.5, ls="none")
        ax.plot(*nyc, marker="o", ms=3.6, mfc="white", mec="#0f172a", mew=0.7, ls="none")
        if i == 0:
            ax.annotate("Québec fires", xy=fire, xytext=(fire[0] + 1.2, fire[1] + 2.6),
                        fontsize=6.3, color="white", fontweight="bold")
        ax.annotate("New York", xy=nyc, xytext=(nyc[0] + 1.1, nyc[1] + 1.2),
                    fontsize=6.6, color="white", fontweight="bold")
    fig.savefig(out, dpi=dpi, facecolor="white")
    _plt.close(fig)

def _naca0012_polygon(aoa=-7.0, thickness=0.12, n=250):
    """Analytic NACA0012 outline (chord [0,1]), rotated by `aoa` deg about (0.5, 0)."""
    xs = _np.linspace(0.0, 1.0, n)
    th = 5 * thickness * (0.2969*_np.sqrt(xs) - 0.1260*xs - 0.3516*xs**2 + 0.2843*xs**3 - 0.1015*xs**4)
    a = _np.radians(aoa); cx, cy = 0.5, 0.0
    def _rot(px, py):
        dx, dy = px - cx, py - cy
        return cx + dx*_np.cos(a) - dy*_np.sin(a), cy + dx*_np.sin(a) + dy*_np.cos(a)
    xu_, yu_ = _rot(xs, th); xl_, yl_ = _rot(xs, -th)
    return _np.concatenate([xu_, xl_[::-1]]), _np.concatenate([yu_, yl_[::-1]])

def generate_field(case):
    """Render the ground-truth solution field to <slug>/field.png (square, turbo).
    1-D PDEs (t,x,u) -> u(t,x) heatmap;
    LDC (x,y,u,v,p)  -> velocity magnitude |U| + streamlines (shows the Re-dependent vortices)."""
    if not HAVE_MPL:
        return False
    app = case.get("ref_app", case["app"])
    base = os.path.join(SRC, "apps", app)
    csv, npz = os.path.join(base, "ref_data.csv"), os.path.join(base, "ref_data.npz")
    ref = csv if os.path.isfile(csv) else (npz if os.path.isfile(npz) else None)
    if ref is None:
        return False
    out = os.path.join(ROOT, case["slug"], "field.png")
    fresh = max(os.path.getmtime(ref), os.path.getmtime(__file__))   # rebuild if data OR this script changed
    if os.path.isfile(out) and os.path.getmtime(out) >= fresh:
        return True                                   # already up to date
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if case.get("renderer") == "smoke":               # 2D+t tracer -> 24/48/72 h map panels
        _render_smoke(case, ref, out)
        return True
    if ref.endswith(".npz"):                          # X=(N,2) coords + u=(N,1) scalar field
        z = _np.load(ref)
        X = z["X"]; d = _np.column_stack([X[:, 0], X[:, 1], z["u"].reshape(-1)])
    else:
        d = _np.loadtxt(ref, delimiter=",", skiprows=1)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wide = bool(case.get("wide"))                     # render at true (wide) aspect instead of square
    dpi = 320 if wide else 200                        # higher resolution for the featured wide tile
    if d.shape[1] == 3:                               # t,x,u  -> u(t,x)  (rows=x vert, cols=t horiz)
        a, b, u = d[:, 0], d[:, 1], d[:, 2]
        au, bu = _np.unique(a), _np.unique(b)
        G = _np.full((len(bu), len(au)), _np.nan)
        G[_np.searchsorted(bu, b), _np.searchsorted(au, a)] = u
        fig = _plt.figure(figsize=(1.8, 1.8), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
        ax.imshow(G, origin="lower", aspect="auto", cmap="turbo", interpolation="bilinear")
    else:                                             # x,y,u,v,p -> speed magnitude + streamlines
        x, y, u, v = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
        xu, yu = _np.unique(x), _np.unique(y)
        U = _np.full((len(yu), len(xu)), _np.nan); U[_np.searchsorted(yu, y), _np.searchsorted(xu, x)] = u
        V = _np.full((len(yu), len(xu)), _np.nan); V[_np.searchsorted(yu, y), _np.searchsorted(xu, x)] = v
        sp = _np.hypot(U, V)                          # |U| = sqrt(u^2 + v^2): the physical flow field
        airfoil = case.get("airfoil")
        if airfoil and _np.isnan(sp).any():           # fill body hole (no jagged halo); polygon covers it
            try:
                from scipy import ndimage as _ndi
                _idx = _ndi.distance_transform_edt(_np.isnan(sp), return_distances=False, return_indices=True)
                sp = sp[tuple(_idx)]                   # nearest-neighbour fill
            except Exception:
                sp = _np.nan_to_num(sp)
        cmap = _plt.get_cmap("turbo").copy(); cmap.set_bad("#0b0f1e")
        if wide:                                       # figure at the data's aspect -> elongated, undistorted
            xr, yr = float(xu[-1] - xu[0]), float(yu[-1] - yu[0])
            fig = _plt.figure(figsize=(3.6, max(0.7, 3.6 * yr / xr)), dpi=dpi)
        else:
            fig = _plt.figure(figsize=(1.8, 1.8), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
        ax.imshow(sp, origin="lower", aspect="auto", cmap=cmap, interpolation="bilinear",
                  extent=[xu[0], xu[-1], yu[0], yu[-1]])
        ax.streamplot(xu, yu, _np.nan_to_num(U), _np.nan_to_num(V),
                      density=0.8, color="white", linewidth=0.4, arrowstyle="-")
        if airfoil == "naca0012":                      # draw the body: white fill + black outline
            px, py = _naca0012_polygon(aoa=float(case.get("aoa", -7.0)))
            ax.fill(px, py, facecolor="white", edgecolor="black", linewidth=1.4, zorder=5)
        ax.set_xlim(xu[0], xu[-1]); ax.set_ylim(yu[0], yu[-1])
    fig.savefig(out, dpi=dpi)
    _plt.close(fig)
    return True

# ---------------------------------------------------------------- main
def main():
    avail = []
    for c in CASES:
        dash = os.path.join(SRC, "runs", c["app"], "dashboard.html")
        if not os.path.isfile(dash):
            print("SKIP  %-20s (no dashboard at %s)" % (c["app"], dash))
            continue
        html = open(dash, "rb").read().decode("utf-8")
        c["nodes"], c["metric"], c["rrmse"] = extract_stats(html)
        c["runtime"] = read_runtime(c["app"])
        c["_html"] = html
        avail.append(c)

    if not avail:
        print("No source dashboards found under %s/runs — nothing to build." % SRC)
        sys.exit(1)

    # transformed dashboards
    for c in avail:
        raw = c.pop("_html")
        raw = re.sub(r"<title>.*?</title>",
                     lambda m: "<title>%s</title>" % c["title"], raw, count=1, flags=re.S)
        raw = re.sub(r'(<strong id="problem-link"[^>]*>).*?(</strong>)',
                     lambda m: m.group(1) + c["title"] + m.group(2), raw, count=1, flags=re.S)
        raw = raw.replace("<body>", "<body>\n" + SWITCHER_STYLE + build_nav(c["slug"], avail) + "\n", 1)
        outdir = os.path.join(ROOT, c["slug"])
        os.makedirs(outdir, exist_ok=True)
        open(os.path.join(outdir, "index.html"), "wb").write(raw.encode("utf-8"))

    # reference-field thumbnails
    if not HAVE_MPL:
        print("WARN  numpy/matplotlib unavailable (%s) — skipping field thumbnails" % _MPL_ERR)
    nthumb = sum(1 for c in avail if generate_field(c))

    # overview
    open(os.path.join(ROOT, "index.html"), "wb").write(build_overview(avail).encode("utf-8"))

    print("\nBuilt %d case(s) · %d field thumbnail(s):" % (len(avail), nthumb))
    print("  %-22s %-6s %-8s %-9s %s" % ("slug", "nodes", "runtime", "metric", "best"))
    for i, c in enumerate(avail):
        print("  %d. %-19s %-6s %-8s %-9s %s"
              % (i + 1, c["slug"], c["nodes"], c["runtime"] + "s", c["metric"], c["rrmse"]))
    print("\nWrote %d dashboards + index.html into %s" % (len(avail), ROOT))

if __name__ == "__main__":
    main()
