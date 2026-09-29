#!/usr/bin/env python3
"""redteam — the mechanical attacks research-redteam judges into challenges (docs/RESEARCH-CAPABILITY-SPEC.md §6.7).

    python3 redteam.py <facility> --mandate RES-M-NNN [--as-of YYYY-MM-DD] [--json]
    python3 redteam.py <facility> --sweep [--as-of YYYY-MM-DD] [--json]      every live finding of every standing mandate

Proposes; never writes. Each proposal names the finding, the attack kind (§4.5), a severity and an argument
specific enough to act on. The skill judges each one — files it as a RES-C challenge, sharpens it, or drops it
with a reason — and adds the attacks only judgement can make (unfalsifiable claims, a self-interested primary
the heuristics miss). A proposal is withheld when a challenge of the same kind against the same finding is
already open, accepted or rejected: a ruling stands until the evidence changes.

Mechanical attacks:
  single-source                 a live material finding with one independent origin that alone answers a question
  non-independent-triangulation several evidence items that are not several origins (independent_sources < 2,
                                derives_from set, or one host) under medium or high confidence
  self-interested-primary       an evaluative claim ("leading", "best", "only", …) resting on the subject's own page
  unresolved-contradiction      two live findings that contradict each other, neither superseded
  inference-gap                 high confidence on tertiary or speculative evidence, or on an inferred / hypothesis claim
  stale-evidence                a live finding answering a question whose evidence is past twice its half-life
  off-mandate                   a finding that answers none of its mandate's questions
Severity: blocking when the attacked finding is the only established answer to a question of a bounded mandate
(the brief would ship on it) or a contradiction sits inside one question's answers; material otherwise; minor for
off-mandate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "views"))
from _research import Facility, host, to_date  # noqa: E402

EVALUATIVE = re.compile(r"\b(leading|best|only|first|largest|fastest|unique|unmatched|premier|top|award-winning|number one|#1|world-class)\b", re.I)


def sole_answer(fx: Facility, f) -> list:
    """Question ids this finding alone answers among live established findings."""
    m = fx.mandate.get(f.get("mandate_id")) or {}
    out = []
    for q in m.get("questions") or []:
        live = [i for i in q.get("answered_by") or [] if i in fx.by_id and fx.gate_eligible(fx.by_id[i])]
        if live == [f["id"]]:
            out.append(q.get("id"))
    return out


def attacks(fx: Facility, findings) -> list[dict]:
    already = {(c.get("finding_id"), c.get("kind")) for c in fx.challenges if c.get("status") in ("open", "accepted", "rejected")}
    out = []

    def propose(f, kind, severity, argument):
        if (f["id"], kind) in already:
            return
        out.append({"mandate_id": f.get("mandate_id"), "finding_id": f["id"], "kind": kind, "severity": severity, "argument": argument})

    for f in findings:
        if not fx.live(f):
            continue
        m = fx.mandate.get(f.get("mandate_id")) or {}
        bounded = m.get("status") != "standing"
        ev = [e for e in f.get("evidence") or [] if isinstance(e, dict)]
        hosts = {host(str(e.get("ref"))) for e in ev if str(e.get("ref", "")).startswith("http")}
        n = int(f.get("independent_sources") or 0)
        alone = sole_answer(fx, f)
        claim = str(f.get("claim") or "")
        if f.get("material") and n < 2 and alone and f.get("epistemic_status") != "unknown":
            propose(f, "single-source", "blocking" if bounded and f.get("status") == "established" else "material",
                    f"{f['id']} is the only established answer to {', '.join(alone)} and rests on one origin ({', '.join(str(e.get('ref')) for e in ev) or 'no reference'}). "
                    f"A second, independent source — or a primary one if this is secondary — would settle it.")
        web = [e for e in ev if str(e.get("ref", "")).startswith("http")]
        one_host = len(web) == len(ev) and len(hosts) == 1
        if len(ev) >= 2 and f.get("confidence") in ("high", "medium") and (n < 2 or f.get("derives_from") or one_host):
            why = ("derive from " + ", ".join(f.get("derives_from"))) if f.get("derives_from") else (f"share one host ({next(iter(hosts))})" if one_host else f"count as {n} independent origin(s)")
            propose(f, "non-independent-triangulation", "material",
                    f"{f['id']} cites {len(ev)} sources at {f.get('confidence')} confidence, but they {why}. That is one source counted {len(ev)} times; state the origin and lower the confidence, or find an independent one.")
        if f.get("source_tier") == "primary" and EVALUATIVE.search(claim) and n < 2:
            word = EVALUATIVE.search(claim).group(0)
            propose(f, "self-interested-primary", "material",
                    f"{f['id']} says \"{word}\" on the strength of one primary source — if that source is the subject's own page, it is a self-description, not evidence. A third party that measured it would carry it.")
        for other in f.get("contradicts") or []:
            g = fx.by_id.get(other)
            if g and fx.live(g) and f["id"] < other:
                same_q = set(f.get("answers") or []) & set(g.get("answers") or [])
                propose(f, "unresolved-contradiction", "blocking" if same_q and bounded and f.get("status") == g.get("status") == "established" else "material",
                        f"{f['id']} and {other} contradict each other{(' on ' + ', '.join(sorted(same_q))) if same_q else ''} and neither is superseded. Show both, dated, until a newer finding settles it — never pick one silently.")
        if f.get("confidence") == "high" and (f.get("source_tier") in ("tertiary", "speculative") or f.get("epistemic_status") in ("inferred", "hypothesis")):
            propose(f, "inference-gap", "material",
                    f"{f['id']} is held at high confidence on {f.get('source_tier')} evidence as a{'n' if f.get('epistemic_status', '')[:1] in 'aeiou' else ''} {f.get('epistemic_status')} claim. The confidence outruns the evidence; lower it or source the step the inference skips.")
        answering = [q.get("id") for q in m.get("questions") or [] if f["id"] in (q.get("answered_by") or [])]
        if answering and fx.freshness(f) == "stale":
            d = fx.source_date(f)
            propose(f, "stale-evidence", "material",
                    f"{f['id']} answers {', '.join(answering)} on evidence dated {d} — past twice the {f.get('category')} half-life of {fx.half.get(str(f.get('category')), 365)} days. Re-check it; a newer finding that supersedes it closes this.")
        if not f.get("answers"):
            propose(f, "off-mandate", "minor", f"{f['id']} answers none of {f.get('mandate_id')}'s questions. Attach it to a question, move it, or let it go.")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--mandate")
    g.add_argument("--sweep", action="store_true")
    ap.add_argument("--as-of")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    fac = Path(a.facility)
    fx = Facility(fac if (fac / "manifest.yaml").exists() else fac / "project-state", to_date(a.as_of) or dt.date.today())
    if a.sweep:
        scope = {m["id"] for m in fx.mandates if m.get("status") == "standing"}
    else:
        if a.mandate not in fx.mandate:
            print(f"redteam: no mandate {a.mandate}", file=sys.stderr)
            return 2
        scope = {a.mandate}
    props = attacks(fx, [f for f in fx.findings if f.get("mandate_id") in scope])
    out = {"as_of": str(fx.today), "scope": sorted(scope), "proposals": props,
           "by_severity": {s: sum(1 for p in props if p["severity"] == s) for s in ("blocking", "material", "minor")}}
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"red team over {', '.join(sorted(scope)) or 'no standing mandate'}: {len(props)} proposal(s) — " + ", ".join(f"{n} {s}" for s, n in out["by_severity"].items()))
        for p in props:
            print(f"  [{p['severity']}] {p['finding_id']} {p['kind']}: {p['argument']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
