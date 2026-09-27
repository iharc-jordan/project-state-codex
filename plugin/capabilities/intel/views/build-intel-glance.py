#!/usr/bin/env python3
"""build-intel-glance — the intel desk at a glance, as a self-contained HTML report.

    python3 build-intel-glance.py <facility-dir> [--out FILE] [--as-of YYYY-MM-DD]

Reads (all optional except intel/):
    intel/entities/*.yaml     the players — type, priority, status, relationships
    intel/signals/*.yaml      the findings — append-only, dated, valued, referencing entities
    intel/mandates/*.yaml     engagements with intel context
    intel/agenda.yaml         the tiered research agenda (p0–p3)
    state/intel.json          counters, last longlist / sweep
    manifest.yaml             capabilities.intel (focus, staleness_threshold_days)

Writes ONE file (default <facility>/intel/reports/at-a-glance.html) and nothing else. A lens,
not a writer. Declared to the app in surfaces.yaml (`reports:`) so the Intel page renders it in
place; no scripts, no external resources. Four pictures: the map (entities by type, dots sized
by signal count, coloured by status, faded when stale), the signal stream (last 30 days, one
mark per signal by value), agenda coverage (answered vs open per tier), and mandates by stage.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("build-intel-glance: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

STATUS_COLOR = {"active_research": "var(--accent)", "active_engagement": "var(--ok)", "watch": "var(--warn)", "inactive": "var(--faint)", "archived": "var(--line)"}
VALUE_R = {"high": 7, "medium": 5, "low": 3.5}
MANDATE_LANES = [("Prospecting", ["prospecting"]), ("Proposed", ["proposed"]), ("Active", ["active"]), ("Stalled", ["stalled"]), ("Closed", ["completed", "closed"])]


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def yload(p: Path):
    try:
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def to_date(v):
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def load_dir(d: Path):
    out = []
    for p in sorted(d.glob("*.yaml")):
        x = yload(p)
        if isinstance(x, dict):
            x.setdefault("id", p.stem); x["_path"] = f"{d.name}/{p.name}"
            out.append(x)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("facility"); ap.add_argument("--out"); ap.add_argument("--as-of")
    a = ap.parse_args(argv)
    fac = Path(a.facility).resolve()
    today = dt.date.fromisoformat(a.as_of) if a.as_of else dt.datetime.utcnow().date()
    now_s = (today.strftime("%Y-%m-%d 05:30") if a.as_of else dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
    if not (fac / "intel").is_dir():
        print(f"build-intel-glance: {fac}/intel not found — is the intel capability enabled here?", file=sys.stderr); return 1
    manifest = yload(fac / "manifest.yaml") or {}
    cap = (manifest.get("capabilities") or {}).get("intel") or {}
    focus = cap.get("focus"); focus = focus[0] if isinstance(focus, list) and focus else focus
    stale_days = int(cap.get("staleness_threshold_days", 14))
    name = ((manifest.get("project") or {}).get("name")) or fac.parent.name
    ents = load_dir(fac / "intel" / "entities"); sigs = load_dir(fac / "intel" / "signals"); mands = load_dir(fac / "intel" / "mandates")
    agenda = yload(fac / "intel" / "agenda.yaml") or {}
    try:
        state = json.loads((fac / "state" / "intel.json").read_text())
    except Exception:
        state = {}

    # ── derive ───────────────────────────────────────────────────────────────
    sig_by_ent = defaultdict(list)
    for s in sigs:
        for e in s.get("entities_referenced") or []:
            sig_by_ent[e].append(s)
    def last_signal(eid):
        ds = [to_date(s.get("date")) for s in sig_by_ent.get(eid, [])]
        ds = [d for d in ds if d]
        return max(ds) if ds else None
    active = [e for e in ents if e.get("status") not in ("archived",)]
    stale = [e for e in active if e.get("status") in ("active_research", "active_engagement") and (last_signal(e["id"]) is None or (today - last_signal(e["id"])).days > stale_days)]
    recent = [s for s in sigs if to_date(s.get("date")) and (today - to_date(s.get("date"))).days <= 30]
    by_value = Counter(s.get("intelligence_value") for s in recent)
    tiers = (agenda.get("tiers") or {})
    def q_list(t):
        v = tiers.get(t) or []
        return [q if isinstance(q, dict) else {"q": q} for q in v]
    answered = {t: sum(1 for q in q_list(t) if q.get("answered") or q.get("answered_by")) for t in ("p0", "p1", "p2", "p3")}
    total = {t: len(q_list(t)) for t in ("p0", "p1", "p2", "p3")}
    p0_open = total["p0"] - answered["p0"]

    # ── 1. the map: entities by type ─────────────────────────────────────────
    types = sorted({str(e.get("type") or "other") for e in active}) or ["—"]
    col_w = max(120, min(220, int(900 / max(1, len(types)))))
    x0 = 24
    rows_per_col = defaultdict(list)
    for e in sorted(active, key=lambda e: (str(e.get("priority") or "P9"), e.get("name") or "")):
        rows_per_col[str(e.get("type") or "other")].append(e)
    max_rows = max((len(v) for v in rows_per_col.values()), default=1)
    h = 50 + max_rows * 30 + 10
    svg = [f'<svg viewBox="0 0 960 {h}" role="img" aria-label="Entity map by type">']
    for i, t in enumerate(types):
        x = x0 + i * col_w
        svg.append(f'<text x="{x}" y="22" class="mono">{esc(t.upper())} · {len(rows_per_col[t])}</text><line class="grid" x1="{x}" y1="30" x2="{x}" y2="{h-6}"/>')
        for j, e in enumerate(rows_per_col[t]):
            y = 50 + j * 30
            n = len(sig_by_ent.get(e["id"], [])); r = 5 + min(6, n)
            col = STATUS_COLOR.get(str(e.get("status")), "var(--faint)")
            op = ' opacity=".45"' if e in stale else ""
            ls = last_signal(e["id"])
            svg.append(f'<circle cx="{x+12}" cy="{y}" r="{r}" fill="{col}"{op}><title>{esc(e["id"])} · {esc(e.get("name"))} · {esc(e.get("priority"))} · {esc(e.get("status"))} · {n} signal(s) · last {ls or "never"}</title></circle>'
                       f'<text x="{x+28}" y="{y+4}" class="lbl"{op}>{esc((e.get("name") or e["id"])[:22])}</text><text x="{x+28}" y="{y+15}" class="tiny">{esc(e.get("priority"))} · {n} sig · {("stale " + str((today-ls).days) + " d") if e in stale and ls else ("no signal" if ls is None else str((today-ls).days) + " d ago")}</text>')
    svg.append("</svg>")
    map_svg = "".join(svg)

    # ── 2. the signal stream, last 30 days ───────────────────────────────────
    sx0, sx1 = 60, 936; spx = (sx1 - sx0) / 30
    ss = ['<svg viewBox="0 0 960 150" role="img" aria-label="Signals over the last 30 days">']
    for k in (0, 7, 14, 21, 30):
        d = today - dt.timedelta(days=30 - k); xx = sx0 + k * spx
        ss.append(f'<line class="grid" x1="{xx:.0f}" y1="30" x2="{xx:.0f}" y2="120"/><text x="{xx:.0f}" y="138" class="mono" text-anchor="middle">{d.strftime("%b %-d")}</text>')
    ss.append(f'<line class="today" x1="{sx1}" y1="30" x2="{sx1}" y2="120"/>')
    lanes_y = {"high": 50, "medium": 78, "low": 106}
    for v, yy in lanes_y.items():
        ss.append(f'<text x="8" y="{yy+4}" class="mut">{v}</text><line class="grid" x1="{sx0}" y1="{yy}" x2="{sx1}" y2="{yy}"/>')
    placed = defaultdict(int)
    for s in sorted(recent, key=lambda s: str(s.get("date"))):
        d = to_date(s.get("date")); v = str(s.get("intelligence_value") or "low"); yy = lanes_y.get(v, 106)
        xx = sx0 + (30 - (today - d).days) * spx
        key = (round(xx / 10), v); dy = placed[key] * 6; placed[key] += 1
        col = "var(--crit)" if v == "high" else ("var(--accent)" if v == "medium" else "var(--faint)")
        ss.append(f'<circle cx="{xx:.0f}" cy="{yy-dy}" r="{VALUE_R.get(v,4)}" fill="{col}"><title>{esc(s["id"])} · {esc(s.get("signal_type"))} · {esc(s.get("date"))} · {esc(s.get("source"))} · {esc((s.get("summary") or "")[:120])}</title></circle>')
    ss.append("</svg>")
    stream_svg = "".join(ss)

    # ── 3. agenda coverage ───────────────────────────────────────────────────
    ag = []
    for t in ("p0", "p1", "p2", "p3"):
        tot = total[t]; ans = answered[t]
        bar = f'<span class="bar" style="width:{min(260, tot*26)}px;background:var(--line)"></span>' if tot else '<span class="mut">—</span>'
        fill = f'<span class="bar" style="width:{min(260, ans*26)}px;background:var(--ok);margin-left:-{min(260, tot*26)}px"></span>' if ans else ""
        ag.append(f'<tr><td class="lbl">{t.upper()}</td><td>{bar}{fill}</td><td class="num">{ans} / {tot}</td><td class="tiny">{esc((q_list(t)[0].get("q") or q_list(t)[0].get("question") or "") if q_list(t) else "")}</td></tr>')
    agenda_html = "".join(ag)

    # ── 4. mandates ──────────────────────────────────────────────────────────
    mrows = []
    ent_name = {e["id"]: e.get("name") for e in ents}
    for label, sts in MANDATE_LANES:
        ms = [m for m in mands if str(m.get("status")) in sts]
        mrows.append(f'<tr><td class="lbl">{esc(label)}</td><td class="num">{len(ms)}</td><td>{"; ".join(esc(m["id"]) + " · " + esc(ent_name.get(m.get("entity_id"), m.get("entity_id"))) + " · " + esc(m.get("type")) for m in ms) or "<span class=mut>—</span>"}</td></tr>')
    mand_html = "".join(mrows)

    counts = [(len(active), "entities on the map"), (len(recent), "signals · 30 d"), (by_value.get("high", 0), "high-value"), (p0_open, "P0 unanswered"), (len(stale), f"stale > {stale_days} d")]
    counts_html = '<div class="counts">' + "".join(f'<div class="c"><b>{v}</b><span>{k}</span></div>' for v, k in counts) + "</div>"
    legend = '<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{esc(k.replace("_"," "))}</span>' for k, c in STATUS_COLOR.items() if k != "archived") + '<span><i style="background:var(--accent);opacity:.45"></i>stale</span><span>dot size = signal count</span></div>'
    last_ll = state.get("last_longlist") or "never"; last_sw = state.get("last_sweep") or "never"

    page = PAGE.format(title=esc(name), now=esc(now_s), focus=esc(focus or "no focus declared — the harvester must not run"), map=map_svg, legend=legend, counts=counts_html,
                       stream=stream_svg, agenda=agenda_html, mand=mand_html, ll=esc(last_ll), sw=esc(last_sw), nsig=len(sigs), nent=len(ents))
    out = Path(a.out) if a.out else fac / "intel" / "reports" / "at-a-glance.html"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(page, encoding="utf-8")
    print(f"intel-glance → {out}\n  as of {today} · {len(active)} entities · {len(recent)} signals in 30 d ({by_value.get('high',0)} high) · P0 open {p0_open} · stale {len(stale)}")
    return 0


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — intel desk at a glance</title>
<style>
:root{{--ground:#F5F7F4;--paper:#FFFFFF;--ink:#1B2230;--muted:#6B7480;--faint:#A9B1B8;--line:#DDE3DE;--rule:#B9C2BC;--accent:#1F5F6B;--accent-soft:#E3EEF0;--crit:#d03b3b;--crit-soft:#F6E0E0;--warn:#c98500;--warn-soft:#F7ECD6;--ok:#2E7D4F;--ok-soft:#E1F0E6;
--mono:ui-monospace,Menlo,monospace;--sans:system-ui,-apple-system,"Segoe UI",sans-serif;--serif:Georgia,"Times New Roman",serif}}
@media (prefers-color-scheme:dark){{:root{{--ground:#12181E;--paper:#1A222A;--ink:#E7EBEE;--muted:#A3ACB4;--faint:#5B6670;--line:#2C3640;--rule:#465262;--accent:#6FBFC9;--accent-soft:#1E3238;--crit:#e66767;--crit-soft:#3E2222;--warn:#e0b463;--warn-soft:#3A2F17;--ok:#6CC58F;--ok-soft:#1D3327}}}}
*{{box-sizing:border-box}}body{{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0}}
.wrap{{max-width:1000px;margin:0 auto;padding:28px 20px 64px}}h1{{font-family:var(--serif);font-weight:600;font-size:2rem;line-height:1.1;margin:0}}
.eyebrow{{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}.lede{{color:var(--muted);max-width:66ch;margin:8px 0 28px}}
.focus{{border-left:3px solid var(--accent);background:var(--accent-soft);padding:10px 14px;border-radius:0 6px 6px 0;margin:0 0 28px;font-size:.95rem}}
section{{margin-bottom:52px}}section>header .q{{font-family:var(--serif);font-size:1.5rem;font-weight:600}}section>header .w{{color:var(--muted);font-size:.92rem;margin-top:2px}}
.fig{{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:18px 20px 14px;margin-top:14px}}svg{{width:100%;height:auto;display:block;font-family:var(--sans)}}
svg text{{fill:var(--ink);font-size:12.5px}}svg .mut{{fill:var(--muted);font-size:11px}}svg .tiny{{fill:var(--muted);font-size:10px}}svg .mono{{font-family:var(--mono);font-size:10.5px;fill:var(--muted)}}
svg .lbl{{font-weight:600;font-size:12.5px}}svg .grid{{stroke:var(--line);stroke-width:1}}svg .today{{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:3 3}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.8rem;color:var(--muted);margin-top:10px}}.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}}
.counts{{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}}.counts .c{{border:1px solid var(--line);border-radius:8px;background:var(--paper);padding:10px 14px;min-width:96px}}.counts .c b{{display:block;font-family:var(--serif);font-size:1.6rem;font-weight:600;line-height:1}}.counts .c span{{font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.tbl{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-family:var(--mono);font-size:.7rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}td.lbl,.lbl{{font-weight:600}}.mut{{color:var(--muted)}}.tiny{{font-size:.78rem;color:var(--muted)}}
.bar{{display:inline-block;height:10px;vertical-align:middle}}
.cites{{font-family:var(--mono);font-size:.74rem;color:var(--muted);margin:10px 0 0;line-height:1.7}}.cites b{{color:var(--accent);font-weight:500}}
</style></head><body><div class="wrap">
  <div class="eyebrow">intel capability · generated by build-intel-glance · {now}</div>
  <h1>{title} — intel desk at a glance</h1>
  <p class="lede">Drawn from intel/entities, intel/signals (append-only), intel/mandates, the research agenda and the capability state. Every mark carries its source; a search that found nothing is shown as nothing.</p>
  <div class="focus"><b>Focus.</b> {focus}</div>

  <section><header><div class="q">Who is on the map, and who has gone quiet?</div><div class="w">Entities by type · dot size is the signal count · colour is status · faded past the staleness threshold</div></header>
  <div class="fig">{map}{legend}</div>{counts}</section>

  <section><header><div class="q">What has been learned in the last 30 days?</div><div class="w">One mark per signal on its date, in the lane of its intelligence value</div></header>
  <div class="fig">{stream}<p class="cites">Signals are never edited: a correction is a new signal that supersedes the old. Promoting one into a risk or decision records a <b>became:</b> edge. {nsig} signals on file across {nent} entities.</p></div></section>

  <section><header><div class="q">Which questions decide strategy, and are they answered?</div><div class="w">The research agenda by tier · answered questions cite the signal that closed them</div></header>
  <div class="fig"><div class="tbl"><table><thead><tr><th>Tier</th><th>Coverage</th><th class="num">Answered</th><th>First open question</th></tr></thead><tbody>{agenda}</tbody></table></div>
  <p class="cites">Last longlist <b>{ll}</b> · last sweep <b>{sw}</b>. P0 unanswered questions are raised by the daily digest.</p></div></section>

  <section><header><div class="q">Which engagements carry intel context?</div><div class="w">Mandates by stage</div></header>
  <div class="fig"><div class="tbl"><table><thead><tr><th>Stage</th><th class="num">#</th><th>Mandates</th></tr></thead><tbody>{mand}</tbody></table></div></div></section>
</div></body></html>
"""

if __name__ == "__main__":
    sys.exit(main())
