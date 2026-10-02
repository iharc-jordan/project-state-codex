#!/usr/bin/env python3
"""build-research-delta — what changed in a standing mandate, as a self-contained HTML report.

    python3 build-research-delta.py <facility-dir> [--mandate RES-M-NNN] [--since YYYY-MM-DD]
                                    [--out FILE] [--as-of YYYY-MM-DD] [--artifact]

The product of standing research (spec §1, §6.8): not a fresh essay each morning but the
difference since the last brief. Built from research-change records, so it can only report what
was recorded; when nothing material moved it says so in one line. Five parts per mandate:

  1. What changed        material changes, each with the finding it replaced and the one that replaced it
  2. What else moved     notable changes; noise is counted and never shown
  3. The questions now   each question's state, with the ones that reopened
  4. Not yet settled     provisional findings and open challenges on this mandate
  5. Watching next       evidence due to go stale soonest, and time-bound facts

Default period: since state/research.json → last_brief. Writes <facility>/research/reports/delta.html.
This is the lens `research-brief delta` renders from; the skill adds the interpretation, this
shows the record. Read-only.
"""
from __future__ import annotations

import argparse
import json
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _research import Facility, esc, is_fixture, model, page, to_date  # noqa: E402

Q_CHIP = {"open": "", "answered": "ok", "aging": "warn", "stale": "crit", "reopened": "crit", "dropped": ""}

CSS = """
.mandate{border-top:2px solid var(--ink);padding-top:14px;margin-top:8px}
.change{padding:12px 0;border-top:1px solid var(--line)}.change:first-child{border-top:0;padding-top:0}
.change .sum{font-family:var(--serif);font-size:1.08rem;font-weight:600;line-height:1.35}
.ba{display:grid;grid-template-columns:70px 1fr;gap:4px 12px;margin-top:8px;font-size:.88rem}
.ba .k{font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding-top:2px}
.before{color:var(--muted);text-decoration:line-through;text-decoration-color:var(--faint)}
.ex{font-family:var(--serif);font-style:italic;color:var(--muted);font-size:.84rem;margin-top:2px}
.meta{font-family:var(--mono);font-size:.72rem;color:var(--muted);margin-top:6px}
.quiet{font-family:var(--serif);font-size:1.3rem;color:var(--ok);padding:6px 0}
.qrow{display:grid;grid-template-columns:30px 1fr auto;gap:10px;align-items:center;padding:5px 0;border-top:1px solid var(--line);font-size:.9rem}
.qrow:first-child{border-top:0}.qrow .qid{font-family:var(--mono);font-size:.74rem;color:var(--muted)}
.soon{font-family:var(--mono);font-variant-numeric:tabular-nums}
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("facility")
    ap.add_argument("--mandate")
    ap.add_argument("--since")
    ap.add_argument("--out")
    ap.add_argument("--as-of")
    ap.add_argument("--artifact", action="store_true")
    ap.add_argument("--json", help="also write the delta as JSON — what research-brief delta composes from")
    a = ap.parse_args(argv)
    fac = Path(a.facility).resolve()
    if not (fac / "research").is_dir():
        print(f"build-research-delta: {fac}/research not found", file=sys.stderr)
        return 1
    today = dt.date.fromisoformat(a.as_of) if a.as_of else dt.datetime.utcnow().date()
    now_s = today.strftime("%Y-%m-%d 06:30") if a.as_of else dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    fx = Facility(fac, today)
    since = to_date(a.since) if a.since else to_date(fx.state.get("last_brief"))
    targets = [m for m in fx.mandates if (m["id"] == a.mandate if a.mandate else m.get("status") == "standing")]
    if not targets:
        print("build-research-delta: no standing mandate" + (f" {a.mandate}" if a.mandate else ""), file=sys.stderr)
        return 1

    def claim_block(fid, kind):
        f = fx.by_id.get(fid)
        if not f:
            return f'<div class="k">{kind}</div><div class="mut">{esc(fid)} — not on file</div>'
        ex = next((e.get("excerpt") for e in (f.get("evidence") or []) if isinstance(e, dict) and e.get("excerpt")), None)
        cls = "before" if kind == "before" else ""
        return (f'<div class="k">{kind}</div><div><span class="{cls}">{esc(f.get("claim"))}</span> '
                f'<span class="id">{esc(fid)} · {esc(f.get("source_tier"))} · {esc(f.get("epistemic_status"))} · {esc(fx.freshness(f))}</span>'
                + (f'<div class="ex">“{esc(ex)}”</div>' if ex and kind == "after" else "") + "</div>")

    blocks = []
    total_material = 0
    for m in targets:
        xs = [x for x in fx.changes if x.get("mandate_id") == m["id"] and to_date(x.get("detected_at"))
              and (since is None or to_date(x.get("detected_at")) > since) and to_date(x.get("detected_at")) <= today]
        mat = sorted([x for x in xs if x.get("significance") == "material"], key=lambda x: str(x.get("detected_at")), reverse=True)
        nota = [x for x in xs if x.get("significance") == "notable"]
        noise = [x for x in xs if x.get("significance") == "noise"]
        total_material += len(mat)

        # 1. what changed
        if mat:
            ch = "".join(
                f'<div class="change"><div class="sum">{esc(x.get("summary"))}</div><div class="ba">'
                + "".join(claim_block(b, "before") for b in (x.get("before") or []))
                + "".join(claim_block(af, "after") for af in (x.get("after") or []))
                + f'</div><div class="meta">{esc(x.get("id"))} · {esc(x.get("subject"))} · detected {esc(x.get("detected_at"))}'
                + (f' by {esc(x.get("detected_by"))} in {esc(x.get("run_id"))}' if x.get("run_id") else "") + "</div></div>" for x in mat)
        else:
            ch = f'<div class="quiet">Nothing material changed since {esc(since or "the start")}.</div>'

        # 2. what else moved
        other = "".join(f'<div class="change"><div>{esc(x.get("summary"))}</div><div class="meta">{esc(x.get("id"))} · {esc(x.get("subject"))} · {esc(x.get("detected_at"))}</div></div>' for x in nota)
        other += f'<p class="mut small">{len(noise)} noise change{"s" if len(noise) != 1 else ""} suppressed.</p>' if noise else ""
        other = other or '<p class="mut">Nothing else moved.</p>'

        # 3. the questions now
        qs = "".join(
            f'<div class="qrow"><span class="qid">{esc(q.get("id"))}</span><span>{esc(q.get("text"))}</span>'
            f'<span class="chip {Q_CHIP[s]}">{esc(s)}</span></div>'
            for q in (m.get("questions") or []) for s in [fx.question_state(m, q)])

        # 4. not yet settled
        prov = [f for f in fx.findings_for(m["id"]) if fx.live(f) and f.get("status") == "provisional"]
        opench = [c for c in fx.challenges if c.get("mandate_id") == m["id"] and c.get("status") == "open"]
        unsettled = "".join(f'<tr><td class="id">{esc(f["id"])}</td><td>{esc(f.get("claim"))}</td><td><span class="chip warn">provisional</span></td>'
                            f'<td class="small mut">waits for an independent origin or a person</td></tr>' for f in prov)
        unsettled += "".join(f'<tr><td class="id">{esc(c["id"])}</td><td>{esc(c.get("argument"))}</td><td><span class="chip {"crit" if c.get("severity") == "blocking" else "warn"}">{esc(c.get("severity"))}</span></td>'
                             f'<td class="small mut">against {esc(c.get("finding_id"))} · a person rules</td></tr>' for c in opench)
        unsettled = f'<div class="tbl"><table><tbody>{unsettled}</tbody></table></div>' if unsettled else '<p class="mut">Everything on this mandate is settled.</p>'

        # 5. watching next
        watch = []
        for q in m.get("questions") or []:
            ans = [fx.by_id[i] for i in (q.get("answered_by") or []) if i in fx.by_id and fx.gate_eligible(fx.by_id[i])]
            ds = [fx.days_to_stale(f) for f in ans if fx.days_to_stale(f) is not None]
            if ds and max(ds) > 0 and max(ds) <= 120:
                watch.append((max(ds), f'{q.get("id")}: its freshest evidence goes stale', q.get("text")))
        for f in fx.findings_for(m["id"]):
            if fx.live(f) and f.get("category") == "event" and fx.freshness(f) == "fresh":
                watch.append((fx.days_to_stale(f) or 999, f"time-bound: {f['id']}", f.get("claim")))
        watch.sort(key=lambda w: w[0])
        watch_html = ('<div class="tbl"><table><thead><tr><th class="num">Days</th><th>What</th><th>Detail</th></tr></thead><tbody>'
                      + "".join(f'<tr><td class="num soon">{d}</td><td class="small">{esc(w)}</td><td class="small mut">{esc(t)}</td></tr>' for d, w, t in watch)
                      + "</tbody></table></div>") if watch else '<p class="mut">Nothing due to go stale in the next 120 days.</p>'

        cadence = (m.get("standing") or {}).get("cadence", "")
        blocks.append(f"""
  <div class="mandate"><div class="eyebrow">{esc(m["id"])} · {esc(m.get("status"))}{(" · " + esc(cadence)) if cadence else ""} · period {esc(since or "start")} → {esc(today)}</div>
  <h2 style="font-family:var(--serif);font-size:1.5rem;margin:4px 0 0;text-wrap:balance">{esc(m.get("headline"))}</h2></div>
  <section><header><div class="q">What changed?</div><div class="w">Material changes only — each shows the finding it replaced, struck through, and the finding that replaced it.</div></header>
  <div class="fig">{ch}</div></section>
  <section><header><div class="q">What else moved?</div></header><div class="fig">{other}</div></section>
  <section><header><div class="q">Where do the questions stand?</div><div class="w">A question reopens when every finding that answered it has gone stale.</div></header><div class="fig">{qs}</div></section>
  <section><header><div class="q">What is not yet settled?</div><div class="w">Findings that do not count until corroborated, and objections waiting on a ruling.</div></header><div class="fig">{unsettled}</div></section>
  <section><header><div class="q">What are we watching next?</div><div class="w">Evidence due to go stale soonest, and facts with a date on them.</div></header><div class="fig">{watch_html}</div></section>""")

    fixture = '<span class="fixture">fixture · every fact invented</span>' if is_fixture(fx) else ""
    headline = (f"{total_material} material change{'s' if total_material != 1 else ''} since {since}" if total_material
                else f"Nothing material changed since {since or 'the start'}")
    body = f"""
  <div class="eyebrow">research capability · generated by build-research-delta · {esc(now_s)}</div>
  <h1>{esc(fx.name)} — the delta{fixture}</h1>
  <p class="lede">{esc(headline)}. Built from change records, so it reports only what the research recorded moving; interpretation is added by research-brief when it composes the brief that leaves the Project.</p>
  {"".join(blocks)}
"""
    out = Path(a.out) if a.out else fac / "research" / "reports" / "delta.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(("Research Delta Brief" if a.artifact else f"{fx.name} — the delta"), body, CSS, a.artifact), encoding="utf-8")
    if a.json:
        # the record research-brief delta interprets: per mandate, the changes since `since` by significance, where each
        # question stands, what is not settled, and the evidence due to go stale soonest — the same derivations as the page
        M = model(fx)
        mm = {m["id"]: m for m in M["mandates"]}
        rows = []
        for m in targets:
            ch = [x for x in M["changes"] if x["mandate"] == m["id"] and (since is None or (to_date(x["detected_at"]) and to_date(x["detected_at"]) > since))]
            live = [f for f in M["findings"] if f["mandate"] == m["id"] and f["live"]]
            rows.append({"mandate": m["id"], "headline": m.get("headline"), "since": str(since) if since else None,
                         "material": [x for x in ch if x["significance"] == "material"], "notable": [x for x in ch if x["significance"] == "notable"],
                         "noise_suppressed": sum(1 for x in ch if x["significance"] == "noise"),
                         "nothing_material": not any(x["significance"] == "material" for x in ch),
                         "questions": (mm.get(m["id"]) or {}).get("questions", []),
                         "unsettled": {"provisional": [f["id"] for f in live if f["status"] == "provisional"],
                                       "open_challenges": [c["id"] for c in M["challenges"] if c["mandate"] == m["id"] and c["status"] == "open"]},
                         "stale_soonest": [{"id": f["id"], "stale_on": f["stale_on"], "claim": f["claim"]} for f in sorted((f for f in live if f["stale_on"]), key=lambda f: f["stale_on"])[:5]]})
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps({"as_of": str(today), "since": str(since) if since else None, "mandates": rows}, indent=2, default=str))
    print(f"research-delta → {out}\n  {len(targets)} standing mandate(s) · {headline}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
