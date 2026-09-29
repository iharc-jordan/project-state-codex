#!/usr/bin/env python3
"""build-research-timeline — the research capability's Timeline report.

    python3 build-research-timeline.py <facility-dir> [--out FILE] [--as-of YYYY-MM-DD] [--horizon DAYS] [--artifact]

Three pictures, drawn from the shared model (views/_research.py model) so they agree with At a glance:

  1. The life of each mandate   one lane per mandate across its whole life: the lifecycle (draft · locked · in
                                progress or standing · closed), every step (filled when it found something, hollow when
                                barren), every finding (coloured by source tier; hollow while provisional; faded once
                                superseded, with a line to what replaced it), challenges from raised to ruled (open ones
                                run to today), changes, shipped deliverables — and, past today, the date each answered
                                question's evidence goes stale.
  2. When does the evidence go  every live established finding as a runway from its source date — fresh until one
     stale?                     half-life, aging to two, stale after — sorted by the day it goes stale. What decays
                                first is what a standing mandate re-checks first.
  3. What has the walk been     one column per night the walk ran: actions taken and decisions parked for a person.
     doing?
Writes <facility>/research/reports/timeline.html and nothing else. No scripts, no external resources.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _research import Facility, esc, is_fixture, model, page, to_date  # noqa: E402

PHASE = {"draft": "var(--faint)", "locked": "var(--t-tertiary)", "in-progress": "var(--accent)", "standing": "var(--f-change)",
         "complete": "var(--ok)", "closed-negative": "var(--t-secondary)", "killed": "var(--crit)"}
TIER = {"primary": "var(--t-primary)", "secondary": "var(--t-secondary)", "tertiary": "var(--t-tertiary)", "speculative": "var(--t-spec)"}

CSS = """
svg .lane{fill:var(--paper)}svg .lanealt{fill:var(--ground)}svg .ph{font-size:10px;fill:#fff;font-weight:600}svg .lbl{font-weight:600;font-size:12.5px}
svg .today{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:3 3}svg .future{fill:var(--accent-soft);opacity:.55}svg .qs{font-family:var(--mono);font-size:9.5px;fill:var(--warn)}
.legend i.hollow{background:none;border:1.5px solid var(--t-primary)}.legend i.dia{transform:rotate(45deg);background:var(--f-change)}
.two{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:18px}@media (max-width:760px){.two{grid-template-columns:1fr}}
.note{font-size:.84rem;color:var(--muted);border-left:3px solid var(--line);padding:4px 0 4px 12px}
"""


def x_of(d: dt.date, t0: dt.date, t1: dt.date, x0: float, x1: float) -> float:
    return x0 + (x1 - x0) * max(0, min(1, (d - t0).days / max(1, (t1 - t0).days)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("facility")
    ap.add_argument("--out")
    ap.add_argument("--as-of")
    ap.add_argument("--horizon", type=int, default=120, help="days past today to draw (when evidence goes stale)")
    ap.add_argument("--artifact", action="store_true")
    a = ap.parse_args(argv)
    fac = Path(a.facility).resolve()
    if not (fac / "research").is_dir():
        print(f"build-research-timeline: {fac}/research not found — is the research capability enabled here?", file=sys.stderr)
        return 1
    today = dt.date.fromisoformat(a.as_of) if a.as_of else dt.datetime.utcnow().date()
    fx = Facility(fac, today)
    M = model(fx)
    mandates = M["mandates"]
    firsts = [to_date(m["created"]) for m in mandates if to_date(m["created"])] + [to_date(f["created"]) for f in M["findings"] if to_date(f["created"])]
    t0 = (min(firsts) if firsts else today - dt.timedelta(days=60)) - dt.timedelta(days=3)
    t1 = today + dt.timedelta(days=a.horizon)
    W, X0, X1 = 1000, 190, 985
    XM = X0 + 0.7 * (X1 - X0)   # the past takes 70% of the width; the horizon past today has its own, compressed scale

    def X(d):
        return x_of(d, t0, today, X0, XM) if d <= today else x_of(d, today, t1, XM, X1)
    fz = {f["id"]: f for f in M["findings"]}

    # ── 1. the life of each mandate ──────────────────────────────────────────
    LH = 96
    H = 40 + LH * max(1, len(mandates)) + 26
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Mandate timelines">',
         f'<rect class="future" x="{XM:.1f}" y="24" width="{X1 - XM:.1f}" height="{H - 50}"/>']
    # month grid
    marks, span = [], (today - t0).days
    if span <= 100:   # a short history: a tick a week
        d = t0 + dt.timedelta(days=(7 - t0.weekday()) % 7)
        while d < today:
            marks.append((d, d.strftime("%b %-d")))
            d += dt.timedelta(days=7)
    d = dt.date(t0.year, t0.month, 1)
    while d <= t1:
        if d >= t0 and (d > today or span > 100):
            marks.append((d, d.strftime("%b %Y" if d.month == 1 else "%b")))
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    for d, lab in marks:
        xx = X(d)
        if xx < XM - 30 or xx > XM + 30:
            s.append(f'<line class="grid" x1="{xx:.1f}" y1="24" x2="{xx:.1f}" y2="{H - 26}"/><text x="{xx + 3:.1f}" y="18" class="mono">{lab}</text>')
    for i, m in enumerate(mandates):
        y = 30 + i * LH
        s.append(f'<rect class="{"lane" if i % 2 == 0 else "lanealt"}" x="0" y="{y}" width="{W}" height="{LH - 4}" rx="4"/>')
        s.append(f'<text x="10" y="{y + 18}" class="lbl">{esc(m["id"])}</text><text x="10" y="{y + 33}" class="mut">{esc(m["status"])}{" · " + esc(m["cadence"]) if m.get("cadence") else ""} · {esc(m["type"])}</text>'
                 f'<text x="10" y="{y + 48}" class="mut">{m["established"]} est · {m["provisional"]} prov · {m["steps"]} steps</text>')
        head = (m["headline"] or "")[:34] + ("…" if len(m["headline"] or "") > 34 else "")
        s.append(f'<text x="10" y="{y + 63}" class="mono"><title>{esc(m["headline"])}</title>{esc(head)}</text>')
        # lifecycle band
        for sp in m["lifecycle"]:
            a0, a1 = to_date(sp["from"]), to_date(sp["to"]) if sp["to"] else today
            if not a0:
                continue
            if sp["phase"] in ("complete", "closed-negative", "killed"):   # an end is a moment, not a span
                xe = X(a0)
                s.append(f'<path d="M{xe:.1f},{y + 4} v18 M{xe:.1f},{y + 4} l12,5 l-12,5" fill="{PHASE[sp["phase"]]}" stroke="{PHASE[sp["phase"]]}" stroke-width="2"><title>{esc(sp["phase"])} on {esc(sp["from"])}</title></path>'
                         f'<text x="{xe + 15:.1f}" y="{y + 16}" class="mono">{esc(sp["phase"])} {esc(sp["from"])}</text>')
                continue
            x_a, x_b = X(a0), max(X(a0) + 3, X(a1 or today))
            s.append(f'<rect x="{x_a:.1f}" y="{y + 6}" width="{x_b - x_a:.1f}" height="14" rx="3" fill="{PHASE.get(sp["phase"], "var(--faint)")}"><title>{esc(sp["phase"])} · {esc(sp["from"])} → {esc(sp["to"] or "today")}</title></rect>')
            if x_b - x_a > 60:
                s.append(f'<text x="{x_a + 5:.1f}" y="{y + 16.5}" class="ph">{esc(sp["phase"])}</text>')
        # steps
        for st in [z for z in M["steps"] if z["mandate"] == m["id"]]:
            ds = to_date(st["started"])
            if ds:
                xx = X(ds)
                fill = "none" if st["barren"] else "var(--f-step)"
                s.append(f'<rect x="{xx - 3:.1f}" y="{y + 26}" width="6" height="10" rx="1" fill="{fill}" stroke="{"var(--f-barren)" if st["barren"] else "var(--f-step)"}" stroke-width="1.5">'
                         f'<title>{esc(st["id"])} · {esc(st["mode"])} · {esc(st["started"])} — {esc(st["description"])} · {"barren: found nothing" if st["barren"] else str(st["findings"]) + " finding(s)"}</title></rect>')
        # findings, with supersession lines
        placed = {}
        for f in sorted([z for z in M["findings"] if z["mandate"] == m["id"]], key=lambda z: z["created"]):
            dc = to_date(f["created"])
            if not dc:
                continue
            xx = X(dc)
            k = round(xx / 7)
            dy = placed.get(k, 0)
            placed[k] = dy + 1
            yy = y + 48 + (dy % 4) * 8
            col = TIER.get(f["tier"], "var(--faint)")
            op = "0.35" if not f["live"] else "1"
            filled = col if f["status"] == "established" else "var(--paper)"
            s.append(f'<circle cx="{xx:.1f}" cy="{yy}" r="4" fill="{filled}" stroke="{col}" stroke-width="1.6" opacity="{op}">'
                     f'<title>{esc(f["id"])} · {esc(f["tier"])} · {esc(f["confidence"])} · {esc(f["status"])} · {esc(f["freshness"])}{" · superseded by " + esc(f["superseded_by"]) if f["superseded_by"] else ""} — {esc(f["claim"])}</title></circle>')
            f["_xy"] = (xx, yy)
        for f in [z for z in M["findings"] if z["mandate"] == m["id"] and z.get("supersedes")]:
            old = fz.get(f["supersedes"])
            if old and old.get("_xy") and f.get("_xy"):
                (ax, ay), (bx, by) = old["_xy"], f["_xy"]
                s.append(f'<path d="M{ax:.1f},{ay} C{(ax + bx) / 2:.1f},{ay - 14} {(ax + bx) / 2:.1f},{by - 14} {bx:.1f},{by}" fill="none" stroke="var(--f-change)" stroke-width="1.2" stroke-dasharray="3 2"><title>{esc(f["supersedes"])} superseded by {esc(f["id"])}</title></path>')
        # challenges raised → ruled
        for j, c in enumerate([z for z in M["challenges"] if z["mandate"] == m["id"]]):
            dc = to_date(c["created"])
            if not dc:
                continue
            end = to_date(c["ruled"]) or (today if c["status"] == "open" else dc)
            yy = y + LH - 12 - (j % 3) * 4
            col = "var(--crit)" if c["severity"] == "blocking" else "var(--f-red)" if c["status"] == "open" else "var(--faint)"
            s.append(f'<line x1="{X(dc):.1f}" y1="{yy}" x2="{max(X(end), X(dc) + 4):.1f}" y2="{yy}" stroke="{col}" stroke-width="{3 if c["severity"] == "blocking" else 2}" stroke-linecap="round">'
                     f'<title>{esc(c["id"])} · {esc(c["kind"])} · {esc(c["severity"])} · {esc(c["status"])} · raised {esc(c["created"])}{" · ruled " + esc(c["ruled"]) if c["ruled"] else ""} — {esc(c["argument"])}</title></line>')
        # changes
        for x in [z for z in M["changes"] if z["mandate"] == m["id"] and z["significance"] != "noise"]:
            dd = to_date(x["detected_at"])
            if dd:
                xx, r = X(dd), (6 if x["significance"] == "material" else 4)
                s.append(f'<rect x="{xx - r:.1f}" y="{y + 26 - r / 2:.1f}" width="{2 * r}" height="{2 * r}" transform="rotate(45 {xx:.1f} {y + 26 + r / 2:.1f})" fill="var(--f-change)">'
                         f'<title>{esc(x["id"])} · {esc(x["significance"])} · {esc(x["detected_at"])} · {esc(x["subject"])} — {esc(x["summary"])}</title></rect>')
        # shipped deliverables (report files named RES-M-NNN-…-YYYY-MM-DD)
        for r in [z for z in M["reports"] if z.startswith(m["id"])]:
            dm = re.search(r"(\d{4}-\d{2}-\d{2})", r)
            if dm and to_date(dm.group(1)):
                xx = X(to_date(dm.group(1)))
                s.append(f'<path d="M{xx:.1f},{y + 4} v22 M{xx:.1f},{y + 4} l10,4 l-10,4" fill="var(--f-ship)" stroke="var(--f-ship)" stroke-width="1.5"><title>shipped {esc(r)}</title></path>')
        # the horizon: when each answered question's evidence goes stale
        for q in m["questions"]:
            so = to_date(q.get("stale_on"))
            if so and today < so <= t1:
                xx = X(so)
                s.append(f'<line x1="{xx:.1f}" y1="{y + 22}" x2="{xx:.1f}" y2="{y + 40}" stroke="var(--warn)" stroke-width="1.5"/><text x="{xx + 3:.1f}" y="{y + 38}" class="qs">{esc(q["id"])}<title>{esc(q["id"])} goes stale on {esc(q["stale_on"])} — {esc(q["text"])}</title></text>')
    xt = XM
    s.append(f'<line class="today" x1="{xt:.1f}" y1="22" x2="{xt:.1f}" y2="{H - 24}"/><text x="{xt - 4:.1f}" y="{H - 10}" class="mono" text-anchor="end">today {today}</text>'
             f'<text x="{X1 - 4:.1f}" y="{H - 10}" class="mono" text-anchor="end">horizon +{a.horizon} d</text></svg>')
    lanes_svg = "".join(s)
    legend1 = ('<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{p}</span>' for p, c in PHASE.items() if p != "killed") +
               '<span><i style="background:var(--f-step)"></i>step that found something</span><span><i style="background:none;border:1.5px solid var(--f-barren)"></i>barren step</span>'
               '<span><i style="background:var(--t-primary);border-radius:50%"></i>established finding (tier colour)</span><span><i class="hollow" style="border-radius:50%"></i>provisional</span>'
               '<span><i class="dia"></i>change</span><span><i style="background:var(--crit)"></i>challenge, raised → ruled</span><span><i style="background:var(--warn)"></i>question goes stale</span></div>')

    # ── 2. when does the evidence go stale? ──────────────────────────────────
    runway = sorted([f for f in M["findings"] if f["live"] and f["status"] == "established" and to_date(f["source_date"])], key=lambda f: (f["stale_on"] or "9", f["id"]))[:40]
    if runway:
        r0 = min(to_date(f["source_date"]) for f in runway) - dt.timedelta(days=10)
        r1 = max([to_date(f["stale_on"]) for f in runway if to_date(f["stale_on"])] + [today + dt.timedelta(days=30)])
        RX0, RX1, RH = 190, 985, 15
        RX = lambda d: x_of(d, r0, r1, RX0, RX1)  # noqa: E731
        h2 = 30 + RH * len(runway) + 30
        r = [f'<svg viewBox="0 0 {W} {h2}" role="img" aria-label="Evidence runway">']
        for yr in range(r0.year, r1.year + 2):
            for mo in (1, 7):
                dd = dt.date(yr, mo, 1)
                if r0 <= dd <= r1:
                    r.append(f'<line class="grid" x1="{RX(dd):.1f}" y1="20" x2="{RX(dd):.1f}" y2="{h2 - 24}"/><text x="{RX(dd) + 3:.1f}" y="16" class="mono">{dd.strftime("%b %Y")}</text>')
        for i, f in enumerate(runway):
            y = 26 + i * RH
            sd, ag, so = to_date(f["source_date"]), to_date(f["aging_on"]), to_date(f["stale_on"])
            r.append(f'<text x="{RX0 - 8}" y="{y + 10}" text-anchor="end" class="mono">{esc(f["id"])} · {esc(f["category"])}</text>')
            r.append(f'<rect x="{RX(sd):.1f}" y="{y + 2}" width="{max(1, RX(ag) - RX(sd)):.1f}" height="10" rx="2" fill="var(--ok)" opacity=".8"><title>{esc(f["id"])} fresh {sd} → {ag}</title></rect>')
            r.append(f'<rect x="{RX(ag):.1f}" y="{y + 2}" width="{max(1, RX(so) - RX(ag)):.1f}" height="10" rx="2" fill="var(--warn)" opacity=".7"><title>{esc(f["id"])} aging {ag} → {so}</title></rect>')
            if so < r1:
                r.append(f'<rect x="{RX(so):.1f}" y="{y + 5}" width="{max(1, RX1 - RX(so)):.1f}" height="4" fill="var(--crit)" opacity=".35"><title>{esc(f["id"])} stale from {so}</title></rect>')
            r.append(f'<rect x="{RX0:.1f}" y="{y}" width="{RX1 - RX0:.1f}" height="{RH - 1}" fill="transparent"><title>{esc(f["id"])} ({esc(f["mandate"])} {", ".join(f["answers"])}) — {esc(f["claim"])} · fresh until {ag}, stale from {so}</title></rect>')
        r.append(f'<line class="today" x1="{RX(today):.1f}" y1="20" x2="{RX(today):.1f}" y2="{h2 - 22}"/><text x="{RX(today) + 4:.1f}" y="{h2 - 8}" class="mono">today</text></svg>')
        runway_svg = "".join(r)
        soon = [f for f in runway if f["stale_on"] and today <= to_date(f["stale_on"]) <= today + dt.timedelta(days=90)]
        stale_now = [f for f in runway if f["freshness"] == "stale"]
        runway_note = (f"{len(stale_now)} established finding(s) already stale, {len(soon)} going stale in the next 90 days"
                       + (f" — first {soon[0]['id']} on {soon[0]['stale_on']}" if soon else "") + ".")
    else:
        runway_svg, runway_note = '<p class="mut">No established finding yet.</p>', ""

    # ── 3. the walk, night by night ──────────────────────────────────────────
    runs = [z for z in M["runs"] if to_date(z["started"])]
    if runs:
        mx = max(1, max(z["actions"] + z["gates"] for z in runs))
        cw = min(60, 800 // max(1, len(runs)))
        h3 = 150
        w = [f'<svg viewBox="0 0 {W} {h3}" role="img" aria-label="Walk runs">']
        for i, z in enumerate(sorted(runs, key=lambda z: z["started"])):
            xx = 60 + i * (cw + 8)
            ha, hg = 90 * z["actions"] / mx, 90 * z["gates"] / mx
            w.append(f'<rect x="{xx}" y="{110 - ha:.1f}" width="{cw}" height="{ha:.1f}" fill="var(--accent)" rx="2"><title>{esc(z["run_id"])} · {z["actions"]} action(s)</title></rect>'
                     f'<rect x="{xx}" y="{110 - ha - hg:.1f}" width="{cw}" height="{hg:.1f}" fill="var(--f-gate)" rx="2"><title>{esc(z["run_id"])} · {z["gates"]} parked for a person</title></rect>'
                     f'<text x="{xx + cw / 2:.1f}" y="126" text-anchor="middle" class="mono">{esc(z["started"][5:])}</text>')
        w.append('<line class="grid" x1="50" y1="110" x2="990" y2="110"/></svg>')
        walk_svg = "".join(w) + '<div class="legend"><span><i style="background:var(--accent)"></i>actions the walk took</span><span><i style="background:var(--f-gate)"></i>decisions parked for a person</span></div>'
    else:
        walk_svg = '<p class="mut">The walk has not run yet.</p>'

    c = M["counts"]
    counts = "".join(f'<div class="c{" alert" if al else ""}"><b>{v}</b><span>{k}</span></div>' for v, k, al in [
        (len(mandates), "mandates", False), (sum(1 for z in M["steps"] if z["barren"]), "barren steps", False), (c["established"], "established", False),
        (c["stale"], "stale, still live", c["stale"] > 0), (sum(1 for z in M["changes"] if z["significance"] == "material"), "material changes", False),
        (len(runs), "walk runs", False)])
    fixture = '<span class="fixture">fixture · every fact invented</span>' if M["fixture"] else ""
    body = f"""
  <div class="eyebrow">research capability · generated by build-research-timeline · {esc(str(today))}</div>
  <h1>{esc(fx.name)} — research over time {fixture}</h1>
  <p class="lede">Every mandate's life, the evidence it gathered and when that evidence expires, and what the nightly walk did — drawn from the records and the activity log. Hover any mark for its record.</p>
  <div class="counts">{counts}</div>
  <section><header><div class="q">What has each mandate been through?</div><div class="w">One lane per mandate: its lifecycle, steps, findings by tier (hollow while provisional, faded once superseded, a dashed arc to what replaced them), challenges from raised to ruled, changes and shipped deliverables. The shaded band past today is the horizon: the ticks mark when each answered question's evidence goes stale.</div></header>
  <div class="fig">{lanes_svg}{legend1}</div></section>
  <section><header><div class="q">When does the evidence go stale?</div><div class="w">Each live established finding from its source date: fresh until one half-life, aging until two, stale after. Sorted by the day it goes stale — what decays first is what a standing mandate re-checks first.</div></header>
  <div class="fig">{runway_svg}<div class="legend"><span><i style="background:var(--ok)"></i>fresh</span><span><i style="background:var(--warn)"></i>aging</span><span><i style="background:var(--crit);opacity:.5"></i>stale</span></div><p class="cites">{esc(runway_note)} Half-lives from the manifest.</p></div></section>
  <section><header><div class="q">What has the walk been doing?</div><div class="w">One column per night the walk ran: the actions it took, and on top the decisions it parked for a person instead of making.</div></header>
  <div class="fig">{walk_svg}</div></section>
"""
    title = "Research Timeline" if a.artifact else f"{fx.name} — research over time"
    out = Path(a.out) if a.out else fac / "research" / "reports" / "timeline.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(title, body, CSS, a.artifact), encoding="utf-8")
    print(f"research-timeline → {out}\n  {len(mandates)} mandate lane(s) · {len(runway)} finding runway(s) · {len(runs)} walk run(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
