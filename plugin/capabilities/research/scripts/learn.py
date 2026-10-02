#!/usr/bin/env python3
"""learn — what research-retro records at a mandate's close (capabilities/research/README.md).

    python3 learn.py <facility> RES-M-NNN [--as-of YYYY-MM-DD] [--json]

Which steps produced evidence and which produced activity, as DATA — never as code (spec §1.2, "learning is data,
never code"). The skill writes the three records it proposes into `capabilities.research.learning.path`
(default research/learned/) and the lessons into core lessons-learned/, through project-state:

  query-yield.ndjson    one line per query a step ran: the query, its mode, the findings it produced and how many
                        of those became established — research-deepweb reads it before planning
  domain-tiers.yaml     per host the mandate's evidence came from: findings by tier and how many were established,
                        withdrawn or challenged — a prior for the next mandate's source choice, not a verdict
  calibration.ndjson    per confidence level: findings stated, how many later held (established and never
                        superseded by a contradicting finding), and how many fell (withdrawn, or an accepted challenge)
Also: the barren steps (activity that produced nothing), challenges by kind and outcome, and candidate lessons —
each tied to its evidence, for a person to keep or drop.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "views"))
from _research import Facility, host, to_date  # noqa: E402


def learn(fx: Facility, mid: str) -> dict:
    m = fx.mandate[mid]
    steps = [s for s in fx.steps if s.get("mandate_id") == mid]
    fs = {f["id"]: f for f in fx.findings if f.get("mandate_id") == mid}
    accepted = {c.get("finding_id") for c in fx.challenges if c.get("mandate_id") == mid and c.get("status") == "accepted"}
    yield_rows = []
    for s in steps:
        produced = [fs[i] for i in s.get("findings_produced") or [] if i in fs]
        qs = (s.get("inputs") or {}).get("queries") or [s.get("description")]
        for q in qs:
            yield_rows.append({"mandate_id": mid, "step_id": s["id"], "mode": s.get("mode"), "query": q, "findings": len(produced),
                               "established": sum(1 for f in produced if f.get("status") == "established"), "at": str(s.get("completed_at") or s.get("started_at"))})
    hosts = defaultdict(lambda: Counter())
    for f in fs.values():
        for e in f.get("evidence") or []:
            if isinstance(e, dict) and e.get("ref"):
                h = host(str(e["ref"])) if str(e["ref"]).startswith("http") else "documents"
                hosts[h][f.get("source_tier") or "?"] += 1
                hosts[h]["established"] += f.get("status") == "established"
                hosts[h]["withdrawn"] += f.get("status") == "withdrawn"
                hosts[h]["challenged"] += f["id"] in accepted
    calib = []
    for level in ("high", "medium", "low", "speculative"):
        stated = [f for f in fs.values() if f.get("confidence") == level]
        if not stated:
            continue
        fell = [f for f in stated if f.get("status") == "withdrawn" or f["id"] in accepted]
        held = [f for f in stated if f.get("status") == "established" and f not in fell]
        calib.append({"mandate_id": mid, "confidence": level, "stated": len(stated), "held": len(held), "fell": len(fell),
                      "held_share": round(len(held) / len(stated), 2)})
    barren = [{"step_id": s["id"], "mode": s.get("mode"), "description": s.get("description")} for s in steps if s.get("status") == "complete" and not s.get("findings_produced")]
    ch = Counter((c.get("kind"), c.get("status")) for c in fx.challenges if c.get("mandate_id") == mid)
    lessons = []
    if barren and len(barren) * 2 >= len(steps):
        lessons.append({"lesson": f"{len(barren)} of {len(steps)} steps produced nothing — the method front-loaded broad searches before a pinned source list.", "evidence": [b["step_id"] for b in barren]})
    for h, c in sorted(hosts.items(), key=lambda kv: -sum(kv[1][t] for t in ("primary", "secondary", "tertiary"))):
        if c["challenged"] or c["withdrawn"]:
            lessons.append({"lesson": f"{h} fed {c['challenged'] + c['withdrawn']} finding(s) that did not hold — treat it as leads, not evidence.", "evidence": [h]})
    for row in calib:
        if row["confidence"] == "high" and row["stated"] >= 3 and row["held_share"] < 0.8:
            lessons.append({"lesson": f"High confidence held for {row['held']} of {row['stated']} findings — the rubric was applied too generously.", "evidence": ["calibration"]})
    top = Counter((c.get("kind")) for c in fx.challenges if c.get("mandate_id") == mid and c.get("status") == "accepted").most_common(1)
    if top:
        lessons.append({"lesson": f"The red team's most upheld objection was {top[0][0]} ({top[0][1]}×) — check for it while the research is open, not before shipping.", "evidence": ["challenges"]})
    return {"mandate_id": mid, "status": m.get("status"), "steps": len(steps), "productive_steps": len(steps) - len(barren), "barren_steps": barren,
            "query_yield": yield_rows, "domain_tiers": {h: dict(c) for h, c in hosts.items()}, "calibration": calib,
            "challenges": [{"kind": k, "status": s, "n": n} for (k, s), n in sorted(ch.items())], "lessons": lessons}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    ap.add_argument("mandate")
    ap.add_argument("--as-of")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    fac = Path(a.facility)
    fx = Facility(fac if (fac / "manifest.yaml").exists() else fac / "project-state", to_date(a.as_of) or dt.date.today())
    if a.mandate not in fx.mandate:
        print(f"learn: no mandate {a.mandate}", file=sys.stderr)
        return 2
    out = learn(fx, a.mandate)
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"{out['mandate_id']} ({out['status']}): {out['productive_steps']} of {out['steps']} steps produced evidence")
        for b in out["barren_steps"]:
            print(f"  barren  {b['step_id']} {b['mode']}: {b['description']}")
        for c in out["calibration"]:
            print(f"  calibration  {c['confidence']}: {c['held']} of {c['stated']} held")
        for l in out["lessons"]:
            print(f"  lesson  {l['lesson']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
