"""Observatory dashboard — live FastAPI server over the SQLite spine.

Run it:
    .venv\\Scripts\\python.exe -m uvicorn observatory.server:app --port 8787
or use run_dashboard.ps1 from the repo root.

Answers, at a glance, the question Jay asked ("no more log-digging"):
  - Did the scanner run? When? How long? Did it succeed?
  - Which LLM tier actually served (and is the sovereign-local tier alive)?
  - What did it find — top opportunities by win-probability, red-team risk?
  - How is the knowledge store (corpus_docs) filling up (arc #3 readiness)?

The page auto-refreshes every 60s. JSON under /api/* for programmatic access.
"""

from __future__ import annotations

import json
from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from . import db

app = FastAPI(title="Primordial Observatory", docs_url="/api/docs")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    with db.session() as conn:
        return {"status": "ok", "counts": db.counts(conn)}


@app.get("/api/runs")
def api_runs(limit: int = 20) -> JSONResponse:
    with db.session() as conn:
        return JSONResponse([dict(r) for r in db.recent_runs(conn, limit)])


@app.get("/api/runs/latest")
def api_latest_run() -> JSONResponse:
    with db.session() as conn:
        r = db.latest_run(conn)
        return JSONResponse(dict(r) if r else {})


@app.get("/api/opportunities")
def api_opps(limit: int = 50, run_id: int | None = None) -> JSONResponse:
    with db.session() as conn:
        rows = db.top_opportunities(conn, run_id=run_id, limit=limit)
        return JSONResponse([dict(r) for r in rows])


@app.get("/api/corpus")
def api_corpus() -> JSONResponse:
    with db.session() as conn:
        return JSONResponse(db.corpus_stats(conn))


# ---------------------------------------------------------------------------
# HTML dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    with db.session() as conn:
        latest = db.latest_run(conn)
        runs = db.recent_runs(conn, 15)
        corpus = db.corpus_stats(conn)
        top = db.top_opportunities(conn, run_id=latest["run_id"], limit=25) if latest else []
        vuln = db.high_vuln_opportunities(conn, latest["run_id"]) if latest else []
        totals = db.counts(conn)
    return HTMLResponse(_render(latest, runs, top, vuln, corpus, totals))


# ---------------------------------------------------------------------------
# rendering (pure Python, no template engine)
# ---------------------------------------------------------------------------

_STATUS_COLOR = {"success": "#2ecc71", "partial": "#f1c40f", "failed": "#e74c3c"}


def _fmt_dt(s: str | None) -> str:
    if not s:
        return "—"
    return s.replace("T", " ")[:19]


def _fmt_dur(sec) -> str:
    if sec is None:
        return "—"
    sec = int(sec)
    m, s = divmod(sec, 60)
    return f"{m}m {s}s" if m else f"{s}s"


def _badge(text: str, color: str) -> str:
    return (f'<span style="background:{color};color:#0b0e14;padding:2px 10px;'
            f'border-radius:10px;font-weight:600;font-size:12px">{escape(text)}</span>')


def _render(latest, runs, top, vuln, corpus, totals) -> str:
    if latest is None:
        body = ('<div class="card"><h2>No runs recorded yet</h2>'
                '<p class="muted">The dashboard populates after the next scan '
                '(GovTechHunterDaily, 07:00) writes a run record.</p></div>')
        return _PAGE.format(body=body, generated=_fmt_dt(_now()))

    status = latest["status"] or "unknown"
    scolor = _STATUS_COLOR.get(status, "#7f8c8d")

    # --- LLM tier health ---
    tier = latest["tier_served"] or "—"
    local_used = bool(latest["local_tier_used"])
    if local_used:
        tier_badge = _badge(f"tier: {tier}  •  local LIVE", "#2ecc71")
    else:
        tier_badge = _badge(f"tier: {tier}  •  local DOWN (fell back)", "#e67e22")
    try:
        tier_bd = json.loads(latest["tier_breakdown_json"] or "{}")
    except Exception:
        tier_bd = {}
    tier_detail = " · ".join(f"{escape(k)}: {v}" for k, v in tier_bd.items()) or "—"

    # --- sources / errors ---
    try:
        sources = json.loads(latest["sources_json"] or "{}")
    except Exception:
        sources = {}
    try:
        errors = json.loads(latest["errors_json"] or "[]")
    except Exception:
        errors = []
    src_rows = "".join(
        f'<tr><td>{escape(str(k))}</td><td style="text-align:right">{v}</td></tr>'
        for k, v in sources.items()
    ) or '<tr><td colspan="2" class="muted">no per-source data</td></tr>'

    err_html = ""
    if errors:
        items = "".join(
            f'<li>{escape(str(e.get("module","?")))}: {escape(str(e.get("error",""))[:160])}</li>'
            for e in errors[:8]
        )
        err_html = f'<div class="card warn"><h3>⚠ Module errors ({len(errors)})</h3><ul>{items}</ul></div>'

    # --- hero card ---
    hero = f"""
    <div class="card hero">
      <div class="row">
        <div>
          <div class="muted">Latest scan — run #{latest['run_id']}</div>
          <h1 style="margin:6px 0">{_badge(status.upper(), scolor)}</h1>
          <div class="muted">{_fmt_dt(latest['started_at'])} &nbsp;·&nbsp; {_fmt_dur(latest['duration_sec'])} &nbsp;·&nbsp; commit {escape(latest['git_commit'] or '—')}</div>
          <div style="margin-top:10px">{tier_badge}</div>
          <div class="muted" style="margin-top:6px">served by: {tier_detail}</div>
        </div>
        <div class="kpis">
          <div class="kpi"><div class="n">{latest['total_scored'] or 0}</div><div class="l">scored</div></div>
          <div class="kpi"><div class="n" style="color:#2ecc71">{latest['high_count'] or 0}</div><div class="l">high fit</div></div>
          <div class="kpi"><div class="n" style="color:#f1c40f">{latest['medium_count'] or 0}</div><div class="l">medium</div></div>
          <div class="kpi"><div class="n" style="color:#7f8c8d">{latest['low_count'] or 0}</div><div class="l">low</div></div>
        </div>
      </div>
    </div>
    """

    # --- top opportunities ---
    opp_rows = ""
    for o in top:
        fit = o["fit_label"] or "?"
        fc = {"High": "#2ecc71", "Medium": "#f1c40f", "Low": "#7f8c8d"}.get(fit, "#7f8c8d")
        vs = o["vulnerability_score"]
        vcol = "#e74c3c" if (vs or 0) >= 70 else "#e67e22" if (vs or 0) >= 40 else "#7f8c8d"
        title = escape((o["title"] or "")[:90])
        link = escape(o["link"] or "#")
        opp_rows += f"""<tr>
          <td><a href="{link}" target="_blank" rel="noopener">{title}</a></td>
          <td>{escape(o['source'] or '')}</td>
          <td style="text-align:center"><b>{o['win_probability'] if o['win_probability'] is not None else '—'}</b></td>
          <td style="text-align:center">{_badge(fit, fc)}</td>
          <td style="text-align:center;color:{vcol};font-weight:600">{vs if vs is not None else '—'}</td>
          <td>{escape((o['primary_vector'] or '')[:40])}</td>
        </tr>"""
    opp_table = f"""
    <div class="card">
      <h3>Top opportunities — run #{latest['run_id']} (by win probability)</h3>
      <table>
        <thead><tr><th>Title</th><th>Source</th><th>Win %</th><th>Fit</th><th>Risk</th><th>Primary vector</th></tr></thead>
        <tbody>{opp_rows or '<tr><td colspan=6 class=muted>none</td></tr>'}</tbody>
      </table>
    </div>
    """

    # --- recent runs history ---
    hist_rows = ""
    for r in runs:
        rc = _STATUS_COLOR.get(r["status"] or "", "#7f8c8d")
        lu = "✓" if r["local_tier_used"] else "—"
        hist_rows += f"""<tr>
          <td>#{r['run_id']}</td>
          <td>{_fmt_dt(r['started_at'])}</td>
          <td>{_badge(r['status'] or '?', rc)}</td>
          <td style="text-align:right">{r['total_scored'] or 0}</td>
          <td style="text-align:right">{r['high_count'] or 0}</td>
          <td style="text-align:center">{escape(r['tier_served'] or '—')}</td>
          <td style="text-align:center">{lu}</td>
          <td style="text-align:right">{_fmt_dur(r['duration_sec'])}</td>
        </tr>"""
    hist = f"""
    <div class="card">
      <h3>Recent runs</h3>
      <table>
        <thead><tr><th>Run</th><th>Started</th><th>Status</th><th>Scored</th><th>High</th><th>Tier</th><th>Local</th><th>Dur</th></tr></thead>
        <tbody>{hist_rows}</tbody>
      </table>
    </div>
    """

    # --- vuln + sources + corpus side cards ---
    vuln_rows = "".join(
        f'<li><b style="color:#e74c3c">{v["vulnerability_score"]}</b> &nbsp;{escape((v["primary_vector"] or "")[:34])}'
        f'<div class="muted" style="font-size:12px">{escape((v["title"] or "")[:70])}</div></li>'
        for v in vuln
    ) or '<li class="muted">none ≥70</li>'

    corpus_rows = "".join(
        f'<tr><td>{escape(k)}</td><td style="text-align:right">{v}</td></tr>'
        for k, v in corpus["by_source"].items()
    ) or '<tr><td colspan=2 class="muted">empty — feed via govinfo ingest (arc #3)</td></tr>'

    side = f"""
    <div class="grid3">
      <div class="card">
        <h3>Sources this run</h3>
        <table>{src_rows}</table>
      </div>
      <div class="card">
        <h3>Top red-team risks</h3>
        <ul class="vuln">{vuln_rows}</ul>
      </div>
      <div class="card">
        <h3>Knowledge store</h3>
        <div class="muted" style="margin-bottom:8px">{corpus['total']} docs · {corpus['embedded']} embedded</div>
        <table>{corpus_rows}</table>
      </div>
    </div>
    """

    footer = (f'<div class="muted" style="margin-top:18px">'
              f'lifetime: {totals["runs"]} runs · {totals["opportunities"]} opportunities · '
              f'{totals["corpus_docs"]} corpus docs &nbsp;|&nbsp; auto-refresh 60s</div>')

    body = hero + err_html + side + opp_table + hist + footer
    return _PAGE.format(body=body, generated=_fmt_dt(_now()))


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Primordial Observatory</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#0b0e14; color:#e6e6e6; font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:24px; }}
  .top {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:18px; }}
  .top h2 {{ margin:0; font-weight:700; letter-spacing:.5px; }}
  .muted {{ color:#8b94a7; }}
  .card {{ background:#141925; border:1px solid #222a3a; border-radius:12px; padding:18px; margin-bottom:16px; }}
  .card.warn {{ border-color:#e67e22; }}
  .hero .row {{ display:flex; justify-content:space-between; gap:24px; flex-wrap:wrap; }}
  .kpis {{ display:flex; gap:20px; }}
  .kpi {{ text-align:center; }}
  .kpi .n {{ font-size:34px; font-weight:700; }}
  .kpi .l {{ color:#8b94a7; font-size:12px; text-transform:uppercase; letter-spacing:.5px; }}
  .grid3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }}
  @media(max-width:820px) {{ .grid3 {{ grid-template-columns:1fr; }} }}
  h1,h3 {{ margin:0 0 12px; }}
  table {{ width:100%; border-collapse:collapse; }}
  th,td {{ text-align:left; padding:7px 8px; border-bottom:1px solid #222a3a; vertical-align:top; }}
  th {{ color:#8b94a7; font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.4px; }}
  a {{ color:#5da9ff; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  ul {{ margin:0; padding-left:18px; }}
  ul.vuln {{ list-style:none; padding:0; }}
  ul.vuln li {{ padding:6px 0; border-bottom:1px solid #222a3a; }}
</style>
</head><body>
  <div class="wrap">
    <div class="top">
      <h2>🛰  PRIMORDIAL OBSERVATORY</h2>
      <div class="muted">GovTech Hunter · generated {generated}</div>
    </div>
    {body}
  </div>
</body></html>"""
