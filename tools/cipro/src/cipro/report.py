"""Static HTML report (Plotly via CDN) for one or more workflows."""
from __future__ import annotations

import html
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .classify import CATEGORIES
from .compare import compare, to_markdown
from .logs import cache_hit_rate
from .metrics import RunMetrics, median, seconds, step_stats, summarize, ts

PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

CSS = """
:root{--bg:#fff;--fg:#1d2433;--muted:#5b6475;--line:#e3e6ec;--card:#f7f8fa;--accent:#2f6fde}
@media (prefers-color-scheme: dark){:root{--bg:#12151b;--fg:#e6e9ef;--muted:#9aa3b2;--line:#2a2f3a;--card:#1a1e26;--accent:#7aa7ff}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:36px 0 10px} .muted{color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:right;white-space:nowrap}
th:first-child,td:first-child,td.l,th.l{text-align:left}
th{color:var(--muted);font-weight:600}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card b{display:block;font-size:22px} .scroll{overflow-x:auto}
.chart{width:100%;height:420px} code{font-size:12.5px}
"""


def _fmt_s(v: float | None) -> str:
    if v is None:
        return "n/a"
    m, s = divmod(int(round(v)), 60)
    return f"{m}m {s:02d}s"


def _table(headers: list[str], rows: list[list[str]], left: int = 1) -> str:
    th = "".join(f'<th class="{"l" if i < left else ""}">{html.escape(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"l" if i < left else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
        for r in rows
    )
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def _median_run(runs: list[RunMetrics]) -> RunMetrics | None:
    xs = [r for r in runs if r.wall_clock_s is not None]
    if not xs:
        return None
    m = median([r.wall_clock_s for r in xs])
    return min(xs, key=lambda r: abs(r.wall_clock_s - m))


def _gantt(con: sqlite3.Connection, run: RunMetrics) -> dict:
    t0 = min(ts(j.created_at) for j in run.jobs if j.created_at)
    y, base, x, text, color = [], [], [], [], []
    palette = {c: i for i, c in enumerate(CATEGORIES)}
    from .classify import classify

    for j in sorted(run.jobs, key=lambda j: j.started_at or ""):
        if not j.started_at or not j.completed_at:
            continue
        y.append(f"[job] {j.name}")
        base.append((ts(j.started_at) - t0).total_seconds())
        x.append(j.duration_s)
        text.append(f"{j.name}: {_fmt_s(j.duration_s)} (queued {_fmt_s(j.queue_s)})")
        color.append(-1)
        for s in con.execute("SELECT * FROM steps WHERE job_id=? ORDER BY number", (j.id,)):
            d = seconds(s["started_at"], s["completed_at"])
            if not d or d < 1:
                continue
            y.append(f"{j.name} › {s['name']}")
            base.append((ts(s["started_at"]) - t0).total_seconds())
            x.append(d)
            text.append(f"{s['name']}: {_fmt_s(d)} [{classify(s['name'])}]")
            color.append(palette[classify(s["name"])])
    return {"y": y, "base": base, "x": x, "text": text, "color": color}


def build(
    con: sqlite3.Connection,
    workflows: dict[str, list[RunMetrics]],
    out_dir: Path,
    title: str = "CI pipeline profile",
    repo: str = "",
    pairs: list[tuple[str, str]] | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    figures: list[tuple[str, dict]] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    parts.append(f"<h1>{html.escape(title)}</h1>")
    parts.append(f'<p class="muted">{html.escape(repo)} · generated {now} by cipro · '
                 "successful runs only · durations from the GitHub Actions REST API</p>")

    # Summary
    rows = []
    summaries = {}
    for wf, runs in workflows.items():
        s = summarize(runs)
        summaries[wf] = s
        rows.append([
            f"<code>{html.escape(wf)}</code>", str(s["runs"]), _fmt_s(s["wall_clock_p50_s"]),
            _fmt_s(s["wall_clock_p95_s"]), _fmt_s(s["time_to_first_job_p50_s"]),
            f"{s['billable_min_p50'] or 0:.0f}", f"${s['cost_usd_p50'] or 0:.3f}",
            f"${s['cost_usd_per_1000_runs_p50']:.2f}",
            f"{(s['overhead_share_p50'] or 0) * 100:.0f}%",
        ])
    parts.append("<h2>Summary</h2>")
    parts.append(_table(
        ["Workflow", "Runs", "Wall p50", "Wall p95", "Queue p50", "Billable min p50", "Cost/run p50",
         "Cost/1000 runs", "Overhead share"], rows))
    parts.append('<p class="muted">Overhead share = time in runner overhead, checkout, cache, toolchain '
                 "setup and dependency install, as a fraction of all step time. Cost uses GitHub-hosted "
                 "per-minute prices with per-job rounding up to whole minutes (see pricing.toml).</p>")

    # Category breakdown
    cats = [c for c in CATEGORIES if any(summaries[w]["category_p50_s"].get(c) for w in workflows)]
    traces = [
        {"type": "bar", "name": c, "x": list(workflows),
         "y": [round(summaries[w]["category_p50_s"].get(c) or 0, 1) for w in workflows]}
        for c in cats
    ]
    figures.append(("cat", {"data": traces, "layout": {"barmode": "stack", "yaxis": {"title": "seconds (p50)"},
                                                        "title": "Where the time goes (median step time by category)"}}))
    parts.append('<h2>Waste breakdown</h2><div id="cat" class="chart"></div>')

    # Trend
    traces = []
    for wf, runs in workflows.items():
        traces.append({"type": "scatter", "mode": "markers+lines", "name": wf,
                       "x": [r.created_at for r in runs], "y": [round((r.wall_clock_s or 0) / 60, 2) for r in runs]})
    figures.append(("trend", {"data": traces, "layout": {"yaxis": {"title": "minutes"},
                                                          "title": "Wall-clock per run"}}))
    parts.append('<h2>Trend</h2><div id="trend" class="chart"></div>')

    # Per workflow detail
    for i, (wf, runs) in enumerate(workflows.items()):
        parts.append(f"<h2>Detail: <code>{html.escape(wf)}</code></h2>")
        mr = _median_run(runs)
        if mr is None:
            parts.append('<p class="muted">No successful runs.</p>')
            continue
        g = _gantt(con, mr)
        fid = f"gantt{i}"
        figures.append((fid, {
            "data": [{"type": "bar", "orientation": "h", "y": g["y"], "x": g["x"], "base": g["base"],
                      "hovertext": g["text"], "hoverinfo": "text",
                      "marker": {"color": g["color"], "colorscale": "Viridis"}}],
            "layout": {"title": f"Median run #{mr.id} ({_fmt_s(mr.wall_clock_s)}) — seconds from first job queued",
                       "yaxis": {"autorange": "reversed", "automargin": True}, "height": max(360, 22 * len(g["y"]))},
        }))
        parts.append(f'<div id="{fid}" class="chart" style="height:{max(360, 22 * len(g["y"]))}px"></div>')
        parts.append("<p><b>Critical path (heuristic):</b> " + " → ".join(html.escape(n) for n in mr.critical_path) + "</p>")
        stats = step_stats(con, [r.id for r in runs])[:30]
        parts.append(_table(
            ["Job › step", "Category", "n", "p50", "p95"],
            [[html.escape(f"{s['job']} › {s['step']}"), s["category"], str(s["n"]), _fmt_s(s["p50_s"]), _fmt_s(s["p95_s"])]
             for s in stats], left=2))
        ids = [j.id for r in runs for j in r.jobs]
        if ids:
            q = ",".join("?" * len(ids))
            ev = [(r["kind"], r["detail"], r["value"]) for r in
                  con.execute(f"SELECT kind, detail, value FROM log_events WHERE job_id IN ({q})", ids)]
            rate = cache_hit_rate(ev)
            fetched = con.execute(f"SELECT COUNT(*) FROM logs_fetched WHERE job_id IN ({q})", ids).fetchone()[0]
            parts.append(f'<p class="muted">Logs parsed for {fetched} of {len(ids)} jobs. Cache hit rate: '
                         f'{"n/a (no cache events)" if rate is None else f"{rate * 100:.0f}%"}.</p>')

    # Comparisons
    for a, b in pairs or []:
        if a in workflows and b in workflows:
            res = compare(workflows[a], workflows[b])
            md = to_markdown(res, a, b)
            parts.append(f"<h2>Paired comparison: <code>{html.escape(a)}</code> vs <code>{html.escape(b)}</code></h2>")
            parts.append(f"<pre>{html.escape(md)}</pre>")

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}</style><script src="{PLOTLY}"></script></head><body><main>
{''.join(parts)}
</main><script>
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const base = {{paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{{color: dark ? '#e6e9ef' : '#1d2433'}}, margin:{{l:60,r:20,t:50,b:60}}}};
const figs = {json.dumps(dict(figures))};
for (const [id, f] of Object.entries(figs)) {{
  Plotly.newPlot(id, f.data, Object.assign({{}}, base, f.layout), {{responsive:true, displaylogo:false}});
}}
</script></body></html>"""
    path = out_dir / "index.html"
    path.write_text(page, encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    return path
