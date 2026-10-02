#!/usr/bin/env python3
"""build-research-glance — research at a glance, as a self-contained HTML report.

    python3 build-research-glance.py <facility-dir> [--out FILE] [--as-of YYYY-MM-DD] [--json FILE] [--artifact]

Reads research/{mandates,steps,findings,challenges,candidates,changes,runs}/, state/research.json,
the research.* slice of logs/activity.ndjson, and manifest.yaml → capabilities.research.

Writes ONE file (default <facility>/research/reports/at-a-glance.html) and nothing else. A lens,
not a writer. Declared in surfaces.yaml as the default report; no scripts, no external
resources, no fact that is not in the substrate. Five pictures (spec §10.2):

  1. The questions      what are we asking, and how far along is each?
  2. What needs you     what is waiting on a person?
  3. Evidence health    would this survive a reviewer?
  4. The spine          what has the research actually been doing?
  5. What changed       what moved since the last delta?

--artifact emits the body-only form for the local HTML preview, as sred's dashboard does.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _research import (EPISTEMIC, TERMINAL, TIERS, Facility, esc, family, is_fixture, model, needs, page,  # noqa: E402
                       to_date)

STATUS_ORDER = ["standing", "in-progress", "locked", "draft", "closed-negative", "complete"]
STATUS_CHIP = {"standing": "acc", "in-progress": "ok", "locked": "ok", "draft": "warn", "closed-negative": "solid", "complete": "solid", "killed": ""}
Q_CHIP = {"open": "", "answered": "ok", "aging": "warn", "stale": "crit", "reopened": "crit", "dropped": ""}
TIER_VAR = {"primary": "--t-primary", "secondary": "--t-secondary", "tertiary": "--t-tertiary", "speculative": "--t-spec"}

FAMILIES = [  # bottom-up stacking order in the spine, with the legend label
    ("mandate", "--f-mandate", "mandate moves"),
    ("step", "--f-step", "steps that found something"),
    ("barren", "--f-barren", "barren steps"),
    ("finding", "--f-finding", "findings"),
    ("red", "--f-red", "red team"),
    ("change", "--f-change", "changes"),
    ("ship", "--f-ship", "shipped, briefed, retro"),
    ("gate", "--f-gate", "parked for a person"),
]


CSS = """
.mand{padding:12px 0;border-top:1px solid var(--line)}.mand:first-child{border-top:0;padding-top:2px}
.mh{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px}.mh b{font-weight:600;font-size:.98rem}
.qs{margin:8px 0 0 0;display:grid;gap:5px}
.qq{display:grid;grid-template-columns:30px 1fr auto 74px;gap:10px;align-items:center;font-size:.88rem;padding:4px 8px;border-radius:5px}
.qq:hover{background:var(--ground)}.qq .qid{font-family:var(--mono);font-size:.74rem;color:var(--muted)}
.qq.st-dropped .qt{text-decoration:line-through;color:var(--muted)}
.tb{display:flex;height:8px;border-radius:2px;overflow:hidden;background:var(--line);width:74px}.tb i{display:block;height:100%}
.moved{font-family:var(--mono);font-size:.64rem;color:var(--f-change);margin-left:6px}
.neg{margin:8px 0 0;padding:8px 10px;border-radius:5px;background:var(--ground);font-size:.86rem}.neg b{font-weight:600}
@media (max-width:620px){.qq{grid-template-columns:26px 1fr;}.qq .chip,.qq .tb{grid-column:2}}
.need td:first-child{width:26%}.sev{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:1px}
.moveblock{padding:10px 0;border-top:1px solid var(--line)}.moveblock:first-child{border-top:0;padding-top:2px}
.mv{display:grid;grid-template-columns:96px 1fr;gap:4px 12px;font-size:.88rem;margin-top:6px}.mv .d{font-family:var(--mono);font-size:.74rem;color:var(--muted)}
.quiet{font-family:var(--serif);font-size:1.05rem;color:var(--ok);margin-top:6px}
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("facility")
    ap.add_argument("--out")
    ap.add_argument("--as-of")
    ap.add_argument("--json", help="also write the derived data as JSON")
    ap.add_argument("--artifact", action="store_true", help="body-only HTML for the local HTML preview")
    a = ap.parse_args(argv)
    fac = Path(a.facility).resolve()
    if not (fac / "research").is_dir():
        print(f"build-research-glance: {fac}/research not found — is the research capability enabled here?", file=sys.stderr)
        return 1
    today = dt.date.fromisoformat(a.as_of) if a.as_of else dt.datetime.utcnow().date()
    now_s = today.strftime("%Y-%m-%d 06:00") if a.as_of else dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    fx = Facility(fac, today)

    live_mandates = sorted([m for m in fx.mandates if m.get("status") != "killed"],
                           key=lambda m: (STATUS_ORDER.index(m.get("status")) if m.get("status") in STATUS_ORDER else 9, m["id"]))

    # ── 1. the questions ─────────────────────────────────────────────────────
    q_total = q_answered = 0
    blocks = []
    derived_q = []
    for m in live_mandates:
        st = m.get("status")
        label = st + (f" · {m.get('standing', {}).get('cadence')}" if st == "standing" and m.get("standing") else "")
        head = (f'<div class="mh"><span class="chip {STATUS_CHIP.get(st, "")}">{esc(label)}</span>'
                f'<span class="id">{esc(m["id"])}</span><b>{esc(m.get("headline"))}</b>'
                f'<span class="chip">{esc(m.get("methodology_type"))}</span>'
                + (f'<span class="chip warn">iteration {m.get("iteration")}</span>' if st == "draft" else "") + "</div>")
        rows = []
        for q in m.get("questions") or []:
            s = fx.question_state(m, q)
            if st not in ("draft",):
                q_total += 1
                q_answered += s in ("answered", "aging")
            ans = [fx.by_id[i] for i in (q.get("answered_by") or []) if i in fx.by_id and fx.gate_eligible(fx.by_id[i])]
            tc = Counter(f.get("source_tier") for f in ans)
            n = sum(tc.values())
            bar = ('<span class="tb" title="tiers of the findings that answer it">'
                   + "".join(f'<i style="width:{100*tc[t]/n:.0f}%;background:var({TIER_VAR[t]})"></i>' for t in TIERS if tc[t])
                   + "</span>") if n else '<span class="tb" title="no established finding answers it yet"></span>'
            moved = '<span class="moved">● moved this week</span>' if fx.changed_recently(m["id"], q.get("id")) else ""
            rows.append(f'<div class="qq st-{s}"><span class="qid">{esc(q.get("id"))}</span>'
                        f'<span class="qt">{esc(q.get("text"))}{moved}</span>'
                        f'<span class="chip {Q_CHIP[s]}">{esc(s)}</span>{bar}</div>')
            derived_q.append({"mandate": m["id"], "question": q.get("id"), "state": s, "answered_by": [f["id"] for f in ans]})
        extra = ""
        if st == "closed-negative" and m.get("null_result_statement"):
            extra = f'<div class="neg"><b>Established absence.</b> {esc(m["null_result_statement"])}</div>'
        blocks.append(f'<div class="mand">{head}<div class="qs">{"".join(rows)}</div>{extra}</div>')
    questions_html = "".join(blocks) or '<p class="mut">No mandates on file.</p>'

    # ── 2. what needs you ────────────────────────────────────────────────────
    # what is waiting on a person — computed once in _research.needs, so the Console and the digest agree
    need = [(r["severity"], r["what"], r["why"], r["mandate"], r["handler"], r["source"]) for r in needs(fx)]
    run = fx.last_run()
    sev_col = {"urgent": "var(--crit)", "soon": "var(--warn)", "ondeck": "var(--faint)"}
    need.sort(key=lambda r: {"urgent": 0, "soon": 1}.get(r[0], 2))
    need_rows = "".join(
        f'<tr><td><span class="sev" style="background:{sev_col[s]}"></span>{esc(w)}</td><td class="small mut">{esc(y)}</td>'
        f'<td class="id">{esc(mid)}</td><td class="small"><span class="chip">{esc(h)}</span><div class="mut small">{esc(src)}</div></td></tr>'
        for s, w, y, mid, h, src in need)
    need_html = (f'<div class="tbl"><table class="need"><thead><tr><th>What</th><th>Why</th><th>Mandate</th><th>Clears with</th></tr></thead>'
                 f'<tbody>{need_rows}</tbody></table></div>') if need else '<p class="quiet">Nothing is waiting on a person.</p>'

    # ── 3. evidence health ───────────────────────────────────────────────────
    ev_rows = [m for m in live_mandates if fx.findings_for(m["id"])]
    W, LX, BX, BW = 960, 0, 280, 400
    RH = 46
    h = 28 + max(1, len(ev_rows)) * RH
    svg = [f'<svg viewBox="0 0 {W} {h}" role="img" aria-label="Evidence health per mandate">',
           f'<text x="{BX}" y="14" class="mono">PRIMARY SHARE OF ESTABLISHED FINDINGS · ▏= GATE</text>',
           f'<text x="{BX + BW + 24}" y="14" class="mono">ESTABLISHED · PROVISIONAL · NOT TRI.</text>']
    health = []
    for i, m in enumerate(ev_rows):
        y = 28 + i * RH
        fs = fx.findings_for(m["id"])
        el = [f for f in fs if fx.gate_eligible(f)]
        prov = [f for f in fs if fx.live(f) and f.get("status") == "provisional"]
        ntri = [f for f in fs if fx.live(f) and fx.not_triangulated(f)]
        share, thr, verdict = fx.gate(m)
        head = m.get("headline") or ""
        short = head if len(head) <= 40 else head[:39].rstrip() + "…"
        svg.append(f'<text x="{LX}" y="{y + 14}" class="mono">{esc(m["id"])} · {esc(m.get("status"))}</text>'
                   f'<text x="{LX}" y="{y + 30}">{esc(short)}</text>')
        x = BX
        tc = Counter(f.get("source_tier") for f in el)
        n = len(el)
        svg.append(f'<rect x="{BX}" y="{y + 8}" width="{BW}" height="16" rx="2" fill="var(--line)"/>')
        for t in TIERS:
            if n and tc[t]:
                w = BW * tc[t] / n
                svg.append(f'<rect x="{x:.1f}" y="{y + 8}" width="{w:.1f}" height="16" fill="var({TIER_VAR[t]})"><title>{t}: {tc[t]}</title></rect>')
                x += w
        gx = BX + BW * thr
        svg.append(f'<line x1="{gx:.1f}" y1="{y + 3}" x2="{gx:.1f}" y2="{y + 29}" stroke="var(--ink)" stroke-width="2"/>')
        vcol = {"pass": "var(--ok)", "below": "var(--crit)"}.get(verdict, "var(--muted)")
        vtxt = f"{share * 100:.0f}% primary · gate {thr * 100:.0f}% · {verdict}" if share is not None else f"no established evidence · gate {thr * 100:.0f}%"
        blk = fx.open_blocking(m["id"])
        if blk and m.get("status") not in TERMINAL:
            vtxt += f" · {len(blk)} blocking"
        svg.append(f'<text x="{BX}" y="{y + 40}" class="mut" style="fill:{vcol}">{esc(vtxt)}</text>')
        epi = Counter(f.get("epistemic_status") for f in el)
        svg.append(f'<text x="{BX + BW + 24}" y="{y + 20}"><tspan font-weight="600">{len(el)}</tspan>'
                   f'<tspan class="mut"> est · </tspan><tspan font-weight="600" style="fill:{"var(--warn)" if prov else "var(--ink)"}">{len(prov)}</tspan>'
                   f'<tspan class="mut"> prov · </tspan><tspan font-weight="600" style="fill:{"var(--crit)" if ntri else "var(--ink)"}">{len(ntri)}</tspan><tspan class="mut"> not tri.</tspan></text>')
        svg.append(f'<text x="{BX + BW + 24}" y="{y + 36}" class="mono">'
                   + esc(" · ".join(f"{k} {epi[k]}" for k in EPISTEMIC if epi[k])) + "</text>")
        health.append({"mandate": m["id"], "established": len(el), "provisional": len(prov), "not_triangulated": len(ntri),
                       "primary_share": share, "threshold": thr, "verdict": verdict, "blocking": len(blk)})
    svg.append("</svg>")
    health_svg = "".join(svg)
    tier_legend = ('<div class="legend">' + "".join(f'<span><i style="background:var({TIER_VAR[t]})"></i>{t}</span>' for t in TIERS)
                   + '<span><i style="background:var(--ink);width:3px"></i>the mandate\'s gate</span>'
                   + "<span>provisional and superseded findings are excluded from the bar</span></div>")

    # ── 4. the spine ─────────────────────────────────────────────────────────
    days = [today - dt.timedelta(days=29 - i) for i in range(30)]
    by_day = defaultdict(lambda: Counter())
    walk_nights = set()
    for e in fx.events:
        d = to_date(e.get("ts"))
        if not d or d < days[0] or d > today:
            continue
        if e.get("event") == "research.walk.opened":
            walk_nights.add(d)
        fam = family(e)
        if fam:
            by_day[d][fam] += 1
    CW, S, G, TOP, CAP = 30, 8, 2, 12, 14
    base = TOP + CAP * (S + G)
    sh = base + 44
    sp = [f'<svg viewBox="0 0 {40 + 30 * CW} {sh}" role="img" aria-label="Research activity over the last 30 days">']
    for i, d in enumerate(days):
        x = 40 + i * CW
        if (d.weekday() == 0 or i == 0) and i < 27:     # keep clear of the 'today' label
            sp.append(f'<line class="grid" x1="{x}" y1="{TOP - 4}" x2="{x}" y2="{base}"/>'
                      f'<text x="{x + 2}" y="{base + 32}" class="mono">{d.strftime("%b %d")}</text>')
        stack = []
        for fam, var, _ in FAMILIES:
            stack += [(fam, var)] * by_day[d][fam]
        shown = stack[:CAP]
        for j, (fam, var) in enumerate(shown):
            yy = base - (j + 1) * (S + G)
            if fam == "gate":
                sp.append(f'<rect x="{x + 11}" y="{yy}" width="{S}" height="{S}" fill="none" stroke="var({var})" stroke-width="1.6"/>')
            else:
                sp.append(f'<rect x="{x + 11}" y="{yy}" width="{S}" height="{S}" rx="1" fill="var({var})"/>')
        if len(stack) > CAP:
            sp.append(f'<text x="{x + 15}" y="{TOP - 2}" class="mono" text-anchor="middle">+{len(stack) - CAP}</text>')
        if d in walk_nights:
            sp.append(f'<circle cx="{x + 15}" cy="{base + 10}" r="3" fill="var(--accent)"><title>night walk</title></circle>')
    tx = 40 + 29 * CW + 15
    sp.append(f'<line x1="{40}" y1="{base}" x2="{40 + 30 * CW}" y2="{base}" stroke="var(--rule)"/>'
              f'<text x="{tx}" y="{base + 32}" class="mono" text-anchor="end">today</text></svg>')
    spine_svg = "".join(sp)
    spine_legend = ('<div class="legend">' + "".join(
        f'<span><i style="background:var({v})"></i>{lbl}</span>' if f != "gate" else f'<span><i style="border:1.6px solid var({v});background:none"></i>{lbl}</span>'
        for f, v, lbl in FAMILIES) + '<span><i style="background:var(--accent);border-radius:50%"></i>a night walk ran</span></div>')

    # ── 5. what changed ──────────────────────────────────────────────────────
    last_brief = to_date(fx.state.get("last_brief"))
    moves = []
    for m in live_mandates:
        xs = [x for x in fx.changes if x.get("mandate_id") == m["id"] and to_date(x.get("detected_at")) and (today - to_date(x.get("detected_at"))).days <= 30]
        since = [x for x in xs if not last_brief or to_date(x.get("detected_at")) > last_brief]
        if not since and m.get("status") != "standing":
            continue                      # a bounded mandate with nothing new has nothing to say here
        mat = [x for x in since if x.get("significance") == "material"]
        nota = [x for x in since if x.get("significance") == "notable"]
        noise = [x for x in since if x.get("significance") == "noise"]
        lines = []
        for x in sorted(mat + nota, key=lambda x: str(x.get("detected_at")), reverse=True):
            chip = "crit" if x.get("significance") == "material" else "warn"
            lines.append(f'<div class="d">{esc(x.get("detected_at"))}<br><span class="chip {chip}">{esc(x.get("significance"))}</span></div>'
                         f'<div>{esc(x.get("summary"))} <span class="id">{esc(x.get("subject"))} · '
                         f'{esc(", ".join(x.get("before") or []) or "—")} → {esc(", ".join(x.get("after") or []) or "—")} · {esc(x.get("id"))}</span></div>')
        quiet = ""
        if m.get("status") == "standing" and not mat:
            quiet = f'<div class="quiet">Nothing material changed since {esc(last_brief or "the last delta")}.</div>'
        tail = f'<div class="mut small" style="margin-top:6px">{len(noise)} noise change{"s" if len(noise) != 1 else ""} suppressed.</div>' if noise else ""
        moves.append(f'<div class="moveblock"><div class="mh"><span class="chip {STATUS_CHIP.get(m.get("status"), "")}">{esc(m.get("status"))}</span>'
                     f'<span class="id">{esc(m["id"])}</span><b>{esc(m.get("headline"))}</b></div>'
                     f'{quiet}<div class="mv">{"".join(lines)}</div>{tail}</div>')
    moves_html = "".join(moves) or '<p class="mut">No change records in the last 30 days.</p>'

    # ── counts and page ──────────────────────────────────────────────────────
    live_f = [f for f in fx.findings if fx.live(f)]
    est = sum(1 for f in live_f if f.get("status") == "established")
    prov_n = sum(1 for f in live_f if f.get("status") == "provisional")
    open_ch = [c for c in fx.challenges if c.get("status") == "open"]
    blk_n = sum(1 for c in open_ch if c.get("severity") == "blocking")
    active_m = sum(1 for m in live_mandates if m.get("status") not in TERMINAL)
    counts = [(active_m, "active mandates", False), (f"{q_answered}/{q_total}", "questions answered", False),
              (est, "established findings", False), (prov_n, "provisional", False),
              (f"{len(open_ch)}" + (f" · {blk_n}✕" if blk_n else ""), "open challenges", blk_n > 0),
              (len(need), "waiting on you", len(need) > 0)]
    counts_html = '<div class="counts">' + "".join(f'<div class="c{" alert" if al else ""}"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for v, k, al in counts) + "</div>"
    hl = fx.half
    hl_txt = " · ".join(f"{k} {hl[k]} d" for k in ("statistic", "pricing", "programme", "event", "offering", "literature") if k in hl)
    run_txt = (f'Last walk <b>{esc(run["run_id"])}</b>: {len(run.get("actions") or [])} action(s), '
               f'{len(run.get("gates") or [])} parked for a person.') if run else "No walk has run yet."
    fixture = '<span class="fixture">fixture · every fact invented</span>' if is_fixture(fx) else ""

    body = f"""
  <div class="eyebrow">research capability · generated by build-research-glance · {esc(now_s)}</div>
  <h1>{esc(fx.name)} — research at a glance{fixture}</h1>
  <p class="lede">Drawn from research/mandates, findings (append-only), challenges, change records, the last walk and the research slice of the activity log. Only established findings count toward a gate; a search that found nothing is shown as nothing.</p>
  {f'<div class="scope">{esc(fx.scope)}</div>' if fx.scope else ''}
  {counts_html}

  <section><header><div class="q">What are we asking, and how far along is each question?</div>
  <div class="w">Every mandate's questions as written. Answered means an established finding answers it; aging and stale follow the half-life of that evidence; on a standing mandate stale evidence reopens the question. The bar is the tier mix of what answers it.</div></header>
  <div class="fig">{questions_html}</div></section>

  <section><header><div class="q">What is waiting on a person?</div>
  <div class="w">Decisions the last walk parked rather than guessed, blocking challenges, drafts that are drifting, findings that need corroboration, and questions reopened by stale evidence — each with the skill that clears it.</div></header>
  <div class="fig">{need_html}</div></section>

  <section><header><div class="q">Would this survive a reviewer?</div>
  <div class="w">Per mandate: the source-tier mix of established findings against its own primary-source gate, how much is still provisional, and how much claims corroboration it does not have.</div></header>
  <div class="fig">{health_svg}{tier_legend}</div></section>

  <section><header><div class="q">What has the research actually been doing?</div>
  <div class="w">The last 30 days, one mark per event, stacked by kind. Barren steps are shown because a step that found nothing is data; hollow squares are decisions the walk parked for a person.</div></header>
  <div class="fig">{spine_svg}{spine_legend}</div></section>

  <section><header><div class="q">What moved since the last delta?</div>
  <div class="w">Change records since the last brief ({esc(last_brief or 'none yet')}). Material and notable changes are listed with the findings they replaced; noise is counted and never shown.</div></header>
  <div class="fig">{moves_html}
  <p class="cites">Findings are never edited: a correction is a new finding that <b>supersedes</b> the old, and the delta is a change record. {run_txt} Freshness from the manifest's half-lives: {esc(hl_txt)}.</p></div></section>
"""
    title = "Research at a Glance" if a.artifact else f"{fx.name} — research at a glance"
    out = Path(a.out) if a.out else fac / "research" / "reports" / "at-a-glance.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(title, body, CSS, a.artifact), encoding="utf-8")

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        # the shared model (views/_research.py model) — what view_capability research returns to the Console
        data = model(fx)
        data.update({"generator": "capabilities/research/views/build-research-glance.py", "health": health})
        Path(a.json).write_text(json.dumps(data, indent=2, default=str))
    print(f"research-glance → {out}\n  as of {today} · {active_m} active mandates · {q_answered}/{q_total} questions answered · "
          f"{est} established, {prov_n} provisional · {len(open_ch)} open challenges ({blk_n} blocking) · {len(need)} waiting on a person")
    return 0


if __name__ == "__main__":
    sys.exit(main())
