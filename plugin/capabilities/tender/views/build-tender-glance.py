#!/usr/bin/env python3
"""build-tender-glance — the tender desk at a glance, as a self-contained HTML report.

    python3 build-tender-glance.py <facility-dir> [--out FILE] [--as-of YYYY-MM-DD] [--json FILE]

Reads (all optional except tenders/):
    tenders/*.yaml            tender entities (workflow.status, dates.closing_at, matching, buyer …)
    tenders/profiles/*.yaml   capability profiles (enabled)
    state/tender.json         tender_connectors — cursors and health per connector
    tenders/events.ndjson     recent typed events (amendments, deadline changes, status changes)
    manifest.yaml             capabilities.tender (sources, mailbox_label)

Writes ONE file (default <facility>/tenders/reports/at-a-glance.html) and nothing else. Read-only
toward the substrate otherwise — a lens, not a writer. Declared to the app in surfaces.yaml
(`reports:`) so the Tender page renders it in place; no scripts, no external resources, so it
holds under the app's content-security policy. Encodings follow the house rules: status colours
always carry a label, a closing-soon ring is critical, stages are lanes, connectors are dots.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("build-tender-glance: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

LANES = [
    ("Discovered", ["discovered", "preliminary_match"]),
    ("Reviewing", ["documents_required", "under_review", "qualified"]),
    ("Bid / no-bid", ["bid_no_bid_pending"]),
    ("Pursuing", ["pursue", "preparing_response", "submitted"]),
    ("Watching", ["watch", "partner_opportunity"]),
]
CLOSED = {"awarded", "unsuccessful", "dismissed", "cancelled", "expired"}
HEALTH_OK = {"healthy"}
HEALTH_WARN = {"delayed", "parsing_error", "stale"}


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def yload(p: Path):
    try:
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def to_date(v) -> dt.date | None:
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).date()
    except Exception:
        try:
            return dt.date.fromisoformat(str(v)[:10])
        except Exception:
            return None


def to_dt(v) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def money(v) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"${n/1e6:.1f}M" if n >= 1e6 else (f"${n/1e3:.0f}K" if n >= 1e3 else f"${n:.0f}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("facility")
    ap.add_argument("--out")
    ap.add_argument("--as-of")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    fac = Path(a.facility).resolve()
    today = dt.date.fromisoformat(a.as_of) if a.as_of else dt.datetime.utcnow().date()
    now = dt.datetime(today.year, today.month, today.day, 5, 30) if a.as_of else dt.datetime.utcnow().replace(microsecond=0)
    if not (fac / "tenders").is_dir():
        print(f"build-tender-glance: {fac}/tenders not found — is the tender capability enabled here?", file=sys.stderr)
        return 1
    manifest = yload(fac / "manifest.yaml") or {}
    cap = (manifest.get("capabilities") or {}).get("tender") or {}
    name = ((manifest.get("project") or {}).get("name")) or fac.parent.name

    tenders = []
    for p in sorted((fac / "tenders").glob("t-*.yaml")):
        t = yload(p)
        if isinstance(t, dict):
            t["_path"] = f"tenders/{p.name}"
            tenders.append(t)
    profiles = [x for x in (yload(p) for p in sorted((fac / "tenders" / "profiles").glob("*.yaml"))) if isinstance(x, dict)]
    try:
        state = json.loads((fac / "state" / "tender.json").read_text())
    except Exception:
        state = {}
    connectors = state.get("tender_connectors") or {}
    events = []
    for raw in (fac / "tenders" / "events.ndjson").read_text().splitlines() if (fac / "tenders" / "events.ndjson").exists() else []:
        try:
            e = json.loads(raw)
        except json.JSONDecodeError:
            continue
        ts = to_dt(e.get("ts"))
        if ts and (now - ts).days <= 14:
            e["_ts"] = ts
            events.append(e)

    # ── derive ───────────────────────────────────────────────────────────────
    def status(t):
        return str(((t.get("workflow") or {}).get("status")) or "discovered")
    open_t = [t for t in tenders if status(t) not in CLOSED]
    closing = lambda t: to_date((t.get("dates") or {}).get("closing_at"))
    soon = [t for t in open_t if closing(t) and 0 <= (closing(t) - today).days <= 7]
    queue = sorted([t for t in open_t if status(t) in ("qualified", "bid_no_bid_pending")], key=lambda t: closing(t) or dt.date.max)
    by_status = Counter(status(t) for t in tenders)
    healthy = sum(1 for c in connectors.values() if str(c.get("health", "")) in HEALTH_OK and not c.get("paused"))
    window = 60

    # ── 1. pipeline lanes ────────────────────────────────────────────────────
    x0, x1, lane_h, top = 170, 936, 58, 60
    px = (x1 - x0) / window
    def X(d: dt.date) -> float:
        return x0 + max(0, min(window, (d - today).days)) * px
    h = top + lane_h * len(LANES) + 16
    svg = [f'<svg viewBox="0 0 960 {h}" role="img" aria-label="Tender pipeline by stage over the next {window} days">']
    svg.append(f'<line class="rule" x1="{x0}" y1="44" x2="{x1}" y2="44"/><text x="{x0}" y="30" class="mono">{today.strftime("%b %-d")} · today</text>')
    for k in (7, 14, 30, 45, 60):
        d = today + dt.timedelta(days=k)
        svg.append(f'<text x="{X(d):.0f}" y="30" class="mono" text-anchor="middle">+{k} d</text><line class="grid" x1="{X(d):.0f}" y1="44" x2="{X(d):.0f}" y2="{h-16}"/>')
    svg.append(f'<rect x="{x0}" y="46" width="{7*px:.0f}" height="{h-62}" fill="var(--crit-soft)" opacity=".6"/><text x="{x0+7*px/2:.0f}" y="{h-4}" class="tiny" text-anchor="middle" fill="var(--crit)">closes within 7 days</text>')
    svg.append(f'<line class="today" x1="{x0}" y1="44" x2="{x0}" y2="{h-16}"/>')
    for i, (label, statuses) in enumerate(LANES):
        y = top + i * lane_h
        rows = [t for t in open_t if status(t) in statuses]
        svg.append(f'<g transform="translate(0,{y})"><text x="12" y="16" class="lbl">{esc(label)}</text><text x="12" y="32" class="mut">{len(rows)} tender{"" if len(rows)==1 else "s"}</text><line class="grid" x1="{x0}" y1="26" x2="{x1}" y2="26"/>')
        placed = []
        for t in sorted(rows, key=lambda t: closing(t) or dt.date.max):
            c = closing(t)
            if not c:
                continue
            days = (c - today).days
            if days < 0 or days > window:
                # off the axis: park at the right edge, hollow
                svg.append(f'<circle cx="{x1-6}" cy="26" r="5" fill="none" stroke="var(--faint)"><title>{esc(t["id"])} · {esc(t.get("title"))} · closes {c} (beyond {window} d)</title></circle>')
                continue
            score = ((t.get("matching") or {}).get("relevance_score"))
            fill = "var(--accent)" if score is not None else "var(--paper)"
            stroke = "var(--crit)" if days <= 7 else "var(--accent)"
            sw = 3 if days <= 7 else 1.5
            cx = X(c)
            # nudge overlapping dots down a little
            dy = 0
            while any(abs(cx - p[0]) < 12 and p[1] == dy for p in placed):
                dy += 10
            placed.append((cx, dy))
            val = (t.get("procurement") or {}).get("estimated_value")
            svg.append(f'<circle cx="{cx:.0f}" cy="{26+dy}" r="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"><title>{esc(t["id"])} · {esc(t.get("title"))} · {esc((t.get("buyer") or {}).get("name"))} · closes {c} ({days} d) · score {score if score is not None else "—"} · {money(val)}</title></circle>')
            if days <= 7 or dy == 0 and len(rows) <= 3:
                svg.append(f'<text x="{cx+10:.0f}" y="{22+dy}" class="tiny">{esc(t["id"])}</text>')
        svg.append("</g>")
    svg.append("</svg>")
    lanes_svg = "".join(svg)

    # ── 2. bid / no-bid queue ────────────────────────────────────────────────
    qrows = []
    for t in queue[:8]:
        c = closing(t); days = (c - today).days if c else None
        m = t.get("matching") or {}; q = t.get("qualification") or {}
        score = m.get("relevance_score"); score_s = str(score) if score is not None else "—"
        qual_s = ('<span class="chip">' + esc(q.get("status")) + "</span>") if q.get("status") else "—"
        if q.get("possible_disqualifiers"):
            qual_s += ' <span class="chip bad">' + str(len(q["possible_disqualifiers"])) + " disqualifier(s)</span>"
        if days is None:
            close_s = "—"
        elif days <= 7:
            close_s = '<span class="chip bad">' + str(days) + " d</span>"
        else:
            close_s = str(days) + " d"
        st = status(t); st_cls = "warn" if st == "bid_no_bid_pending" else ""
        buyer = esc((t.get("buyer") or {}).get("name")); ptype = esc((t.get("procurement") or {}).get("type") or "")
        val = money((t.get("procurement") or {}).get("estimated_value"))
        qrows.append('<tr><td class="lbl">' + esc(t["id"]) + "</td><td>" + esc(t.get("title")) + '<div class="tiny">' + buyer + " · " + ptype + " · " + val + "</div></td>"
                     + '<td class="num">' + score_s + "</td><td>" + qual_s + '</td><td class="num">' + close_s + '</td><td><span class="chip ' + st_cls + '">' + esc(st).replace("_", " ") + "</span></td></tr>")
    queue_html = "".join(qrows) or '<tr><td colspan="6" class="mut">nothing qualified is waiting on a decision</td></tr>'

    # ── 3. connectors ────────────────────────────────────────────────────────
    crows = []
    for cid, c in sorted(connectors.items()):
        hl = str(c.get("health") or "unknown"); paused = bool(c.get("paused"))
        last = to_dt(c.get("last_success") or c.get("last_run"))
        age = (now - last).days if last else None
        dot = "var(--faint)" if paused else ("var(--ok)" if hl in HEALTH_OK else ("var(--warn)" if hl in HEALTH_WARN else "var(--crit)"))
        crows.append(f'<tr><td><i class="dot" style="background:{dot}"></i> <span class="lbl">{esc(cid)}</span></td><td><span class="chip {"ok" if hl in HEALTH_OK and not paused else ("warn" if hl in HEALTH_WARN else "bad")}">{esc("paused" if paused else hl)}</span></td>'
                     f'<td class="num">{age if age is not None else "—"} d</td><td class="num">{c.get("new_records_last_run", c.get("last_new_count", "—"))}</td><td class="num">{c.get("consecutive_failures", 0)}</td><td class="mono tiny">{esc(str(c.get("cursor") or c.get("gmail_cursor") or "")[:19])}</td></tr>')
    conn_html = "".join(crows) or '<tr><td colspan="6" class="mut">no connectors initialized — run the first harvest</td></tr>'

    # ── 4. what changed (14 d) ───────────────────────────────────────────────
    ev_counts = Counter(e.get("event") for e in events)
    ev_html = "".join(f'<span class="chip">{esc(k.replace("tender.",""))} <b>{v}</b></span> ' for k, v in sorted(ev_counts.items(), key=lambda kv: -kv[1])) or '<span class="mut">no events in 14 days</span>'
    recent = sorted(events, key=lambda e: e["_ts"], reverse=True)[:6]
    parts = []
    for e in recent:
        line = '<li><span class="mono tiny">' + e["_ts"].strftime("%b %-d") + "</span> " + esc(str(e.get("event", "")).replace("tender.", "")) + ' · <span class="lbl">' + esc(e.get("id")) + "</span>"
        if e.get("new_value"):
            line += " — " + esc(e.get("new_value"))
        if e.get("shortened"):
            line += ' <span class="chip bad">shortened</span>'
        parts.append(line + "</li>")
    recent_html = "".join(parts)

    counts = [(len(open_t), "open tenders"), (len(soon), "close within 7 d"), (len(queue), "awaiting bid / no-bid"), (f"{healthy}<small>/{len(connectors)}</small>", "connectors healthy"), (sum(1 for p in profiles if p.get("enabled", True)), "profiles enabled")]
    counts_html = '<div class="counts">' + "".join(f'<div class="c"><b>{v}</b><span>{k}</span></div>' for v, k in counts) + "</div>"
    lifecycle = " · ".join(f"{esc(k)} {v}" for k, v in sorted(by_status.items(), key=lambda kv: -kv[1]))

    page = PAGE.format(title=esc(name), now=esc(now.strftime("%Y-%m-%d %H:%M")), window=window, lanes=lanes_svg, counts=counts_html, queue=queue_html,
                       conns=conn_html, ev=ev_html, recent=recent_html, lifecycle=lifecycle, label=esc(cap.get("mailbox_label") or "—"), ntend=len(tenders))
    out = Path(a.out) if a.out else fac / "tenders" / "reports" / "at-a-glance.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    summary = dict(facility=str(fac), as_of=str(today), tenders=len(tenders), open=len(open_t), closing_7d=len(soon), queue=len(queue), connectors=len(connectors), healthy=healthy, out=str(out))
    if a.json:
        Path(a.json).write_text(json.dumps(summary, indent=2))
    print(f"tender-glance → {out}\n  as of {today} · {len(tenders)} tenders ({len(open_t)} open) · {len(soon)} closing ≤7 d · {len(queue)} awaiting decision · connectors {healthy}/{len(connectors)} healthy")
    return 0


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — tender desk at a glance</title>
<style>
:root{{--ground:#F5F7F4;--paper:#FFFFFF;--ink:#1B2230;--muted:#6B7480;--faint:#A9B1B8;--line:#DDE3DE;--rule:#B9C2BC;--accent:#1F5F6B;--accent-soft:#E3EEF0;--crit:#d03b3b;--crit-soft:#F6E0E0;--warn:#c98500;--warn-soft:#F7ECD6;--ok:#2E7D4F;--ok-soft:#E1F0E6;--bad-soft:#F6E0E0;
--mono:ui-monospace,Menlo,monospace;--sans:system-ui,-apple-system,"Segoe UI",sans-serif;--serif:Georgia,"Times New Roman",serif}}
@media (prefers-color-scheme:dark){{:root{{--ground:#12181E;--paper:#1A222A;--ink:#E7EBEE;--muted:#A3ACB4;--faint:#5B6670;--line:#2C3640;--rule:#465262;--accent:#6FBFC9;--accent-soft:#1E3238;--crit:#e66767;--crit-soft:#3E2222;--warn:#e0b463;--warn-soft:#3A2F17;--ok:#6CC58F;--ok-soft:#1D3327;--bad-soft:#3E2222}}}}
*{{box-sizing:border-box}}body{{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0}}
.wrap{{max-width:1000px;margin:0 auto;padding:28px 20px 64px}}h1{{font-family:var(--serif);font-weight:600;font-size:2rem;line-height:1.1;margin:0}}
.eyebrow{{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}.lede{{color:var(--muted);max-width:66ch;margin:8px 0 28px}}
section{{margin-bottom:52px}}section>header .q{{font-family:var(--serif);font-size:1.5rem;font-weight:600}}section>header .w{{color:var(--muted);font-size:.92rem;margin-top:2px}}
.fig{{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:18px 20px 14px;margin-top:14px}}svg{{width:100%;height:auto;display:block;font-family:var(--sans)}}
svg text{{fill:var(--ink);font-size:12.5px}}svg .mut{{fill:var(--muted);font-size:11px}}svg .tiny{{fill:var(--muted);font-size:10px}}svg .mono{{font-family:var(--mono);font-size:10.5px;fill:var(--muted)}}
svg .lbl{{font-weight:600;font-size:13px}}svg .grid{{stroke:var(--line);stroke-width:1}}svg .rule{{stroke:var(--rule);stroke-width:1}}svg .today{{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:3 3}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.8rem;color:var(--muted);margin-top:10px}}.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}}
.counts{{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}}.counts .c{{border:1px solid var(--line);border-radius:8px;background:var(--paper);padding:10px 14px;min-width:96px}}.counts .c b{{display:block;font-family:var(--serif);font-size:1.6rem;font-weight:600;line-height:1}}.counts .c small{{font-size:.9rem;color:var(--muted)}}.counts .c span{{font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.tbl{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-family:var(--mono);font-size:.7rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}td.lbl,.lbl{{font-weight:600}}.mut{{color:var(--muted)}}.tiny{{font-size:.78rem;color:var(--muted)}}.mono{{font-family:var(--mono)}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;vertical-align:-1px;margin-right:4px}}
.chip{{display:inline-block;border-radius:3px;padding:1px 7px;font-family:var(--mono);font-size:.74rem;white-space:nowrap;background:var(--accent-soft);color:var(--accent)}}.chip.bad{{background:var(--bad-soft);color:var(--crit)}}.chip.warn{{background:var(--warn-soft);color:var(--warn)}}.chip.ok{{background:var(--ok-soft);color:var(--ok)}}
ul.ev{{margin:8px 0 0;padding-left:1.1em}}ul.ev li{{margin-bottom:4px}}
.cites{{font-family:var(--mono);font-size:.74rem;color:var(--muted);margin:10px 0 0;line-height:1.7}}.cites b{{color:var(--accent);font-weight:500}}
</style></head><body><div class="wrap">
  <div class="eyebrow">tender capability · generated by build-tender-glance · {now}</div>
  <h1>{title} — tender desk at a glance</h1>
  <p class="lede">Drawn from tenders/, the capability profiles, the connector state and the last 14 days of typed events. Every mark carries its source; nothing is narrated. Regenerate after each harvest.</p>

  <section><header><div class="q">What is in the pipeline, and what closes when?</div><div class="w">One lane per stage · the next {window} days · a dot is a tender on its closing date · filled when scored · ringed when it closes within 7 days</div></header>
  <div class="fig">{lanes}
  <div class="legend"><span><i style="background:var(--accent)"></i>scored</span><span><i style="background:var(--paper);border:1.5px solid var(--accent)"></i>not yet scored</span><span><i style="background:var(--paper);border:3px solid var(--crit)"></i>closes within 7 days</span><span><i style="background:none;border:1px solid var(--faint)"></i>beyond the window</span></div></div>
  {counts}</section>

  <section><header><div class="q">What is waiting on a bid / no-bid?</div><div class="w">Qualified tenders and those already at the decision, closing soonest first</div></header>
  <div class="fig"><div class="tbl"><table><thead><tr><th>Tender</th><th>Title · buyer · type · value</th><th class="num">Score</th><th>Qualification</th><th class="num">Closes</th><th>Stage</th></tr></thead><tbody>{queue}</tbody></table></div>
  <p class="cites">Rows from <b>tenders/t-*.yaml</b> (workflow.status, qualification, matching.relevance_score, dates.closing_at). A bid/no-bid is recorded as a decision by tender-pipeline; nothing here decides.</p></div></section>

  <section><header><div class="q">Are the lead sources flowing?</div><div class="w">One row per connector from state/tender.json · health as the harvester last recorded it</div></header>
  <div class="fig"><div class="tbl"><table><thead><tr><th>Connector</th><th>Health</th><th class="num">Last success</th><th class="num">New last run</th><th class="num">Failures</th><th>Cursor</th></tr></thead><tbody>{conns}</tbody></table></div>
  <p class="cites">Mailbox label <b>{label}</b>. A connector past its interval is raised by the daily digest; access_restricted is never retried.</p></div></section>

  <section><header><div class="q">What changed in the last 14 days?</div><div class="w">Typed events from tenders/events.ndjson</div></header>
  <div class="fig">{ev}<ul class="ev">{recent}</ul>
  <p class="cites">Lifecycle across all {ntend} tenders: {lifecycle}.</p></div></section>
</div></body></html>
"""

if __name__ == "__main__":
    sys.exit(main())
