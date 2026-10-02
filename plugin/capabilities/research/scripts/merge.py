#!/usr/bin/env python3
"""merge — fold the fan-out subagents' returns into what the parent skill writes (capabilities/research/README.md,
§6.5, §6.6, agents/).

    python3 merge.py RETURN.json [RETURN.json …] [--facility <project-state>] [--json]

Each RETURN.json is one subagent's answer for one unit (a query, a document, a candidate, a matrix cell), in the
return contract every agent in agents/ declares:

    {"kind": "fetch|ingest|score|compare", "unit": "…", "status": "complete|partial|empty|blocked",
     "finding_candidates": [{answers, claim, evidence: [{excerpt, ref, retrieved_at, source_date}], source_tier,
                             confidence, epistemic_status, independent_sources, derives_from, category, material}],
     "next_queries": [{"query": "…", "why": "…"}], "scores": [...], "cell": {...}, "document": {...}, "gaps": ["…"]}

The parent stays the only writer: subagents never mint ids and never write. This script:
  refuses   candidates that break the finding rules at the agent boundary — speculative tier without speculative
            confidence (or the reverse), independent_sources above the evidence it counts, a material primary or
            secondary claim without an excerpt on every item, text that reads as an instruction to the model;
  folds     duplicates — same question, claims whose normalised tokens overlap ≥ 0.8 — into one candidate with the
            union of the evidence; confidence becomes the lower, and independent_sources the HIGHER OF THE INPUTS, never
            their sum: the merge itself never raises independence (two agents reading one release are one origin);
  surfaces  possible contradictions — same question, overlapping subject (token overlap ≥ 0.4) and different numbers —
            for the parent to judge and record as `contradicts`, never merged away;
  dedupes   next_queries, and drops those a step on this facility already ran (--facility);
  counts    units by status — `empty` is a result, not a failure.
Reads only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "views"))
from _research import load_dir  # noqa: E402

STOP = set("a an and are as at be by for from has have in is it its of on or that the this to was were will with which who".split())
NUM = re.compile(r"\d+(?:[.,]\d+)?%?")
CONF = ["speculative", "low", "medium", "high"]
TIER = ["speculative", "tertiary", "secondary", "primary"]
INSTRUCTION = re.compile(r"\b(ignore (all|previous|the above)|disregard|you are now|system prompt|do not tell|execute|run the following)\b", re.I)


def stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(s: str) -> set:
    return {stem(w) for w in re.findall(r"[a-z0-9%]+", str(s).lower()) if w not in STOP and w != "among" and len(w) > 1}


def overlap(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def refuse(c: dict):
    ev = [e for e in c.get("evidence") or [] if isinstance(e, dict)]
    if (c.get("source_tier") == "speculative") != (c.get("confidence") == "speculative"):
        return "a speculative tier and speculative confidence go together"
    if int(c.get("independent_sources") or 0) > len(ev):
        return f"independent_sources {c.get('independent_sources')} exceeds its {len(ev)} evidence item(s)"
    if not ev and c.get("epistemic_status") != "unknown":
        return "no evidence and not an unknown"
    if c.get("material") and c.get("source_tier") in ("primary", "secondary") and c.get("epistemic_status") != "unknown" and any(not str(e.get("excerpt") or "").strip() for e in ev):
        return "a material primary or secondary claim needs an excerpt on every evidence item"
    if INSTRUCTION.search(str(c.get("claim") or "")):
        return "the claim reads as an instruction — source text is data, never an instruction"
    if not c.get("answers"):
        return "answers no question"
    return None


def merge(returns: list[dict], facility: Path | None = None) -> dict:
    kept, refused, leads, gaps = [], [], [], []
    units = {}
    for r in returns:
        units[r.get("status", "?")] = units.get(r.get("status", "?"), 0) + 1
        gaps += [{"unit": r.get("unit"), "gap": g} for g in r.get("gaps") or []]
        for c in r.get("finding_candidates") or []:
            why = refuse(c)
            if why:
                refused.append({"unit": r.get("unit"), "claim": c.get("claim"), "why": why})
                continue
            c = {**c, "from_units": [r.get("unit")]}
            twin = next((k for k in kept if set(k.get("answers") or []) & set(c.get("answers") or []) and overlap(k["claim"], c["claim"]) >= 0.8), None)
            if twin:
                refs = {e.get("ref") for e in twin["evidence"]}
                twin["evidence"] += [e for e in c["evidence"] if e.get("ref") not in refs]
                twin["confidence"] = min(twin.get("confidence", "low"), c.get("confidence", "low"), key=CONF.index)
                twin["source_tier"] = max(twin.get("source_tier", "tertiary"), c.get("source_tier", "tertiary"), key=TIER.index)
                twin["independent_sources"] = max(int(twin.get("independent_sources") or 1), int(c.get("independent_sources") or 1))
                twin["derives_from"] = sorted(set(twin.get("derives_from") or []) | set(c.get("derives_from") or []))
                twin["material"] = bool(twin.get("material") or c.get("material"))
                twin["from_units"] += c["from_units"]
                twin["merged"] = twin.get("merged", 1) + 1
            else:
                kept.append(c)
        for q in r.get("next_queries") or []:
            leads.append({"query": q.get("query") if isinstance(q, dict) else str(q), "why": q.get("why") if isinstance(q, dict) else None, "from": r.get("unit")})
    contradictions = []
    for i, a in enumerate(kept):
        for b in kept[i + 1:]:
            if set(a.get("answers") or []) & set(b.get("answers") or []) and 0.4 <= overlap(a["claim"], b["claim"]) and set(NUM.findall(a["claim"])) != set(NUM.findall(b["claim"])) \
                    and NUM.findall(a["claim"]) and NUM.findall(b["claim"]):
                contradictions.append({"a": a["claim"], "b": b["claim"], "why": "same question, same subject, different figures"})
    ran = set()
    if facility:
        for s in load_dir(Path(facility) / "research" / "steps"):
            for q in (s.get("inputs") or {}).get("queries") or []:
                ran.add(" ".join(sorted(tokens(q))))
    seen, uniq = set(), []
    for l in leads:
        key = " ".join(sorted(tokens(l["query"])))
        if key and key not in seen and key not in ran:
            seen.add(key)
            uniq.append(l)
    return {"units": units, "findings": kept, "contradictions": contradictions, "leads": uniq, "refused": refused, "gaps": gaps}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("returns", nargs="+")
    ap.add_argument("--facility")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rets = []
    for p in a.returns:
        d = json.loads(Path(p).read_text())
        rets += d if isinstance(d, list) else [d]
    out = merge(rets, Path(a.facility) if a.facility else None)
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"{sum(out['units'].values())} unit(s) {out['units']} → {len(out['findings'])} finding candidate(s), {len(out['contradictions'])} possible contradiction(s), "
              f"{len(out['leads'])} new lead(s), {len(out['refused'])} refused")
        for r in out["refused"]:
            print(f"  refused ({r['unit']}): {r['why']} — {str(r['claim'])[:80]}")
        for c in out["contradictions"]:
            print(f"  contradiction? {c['a'][:60]} ↔ {c['b'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
