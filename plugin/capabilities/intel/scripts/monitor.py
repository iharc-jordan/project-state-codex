#!/usr/bin/env python3
"""monitor — the deterministic half of intel-monitor (OCI competitive-change-monitor, docs/INTEL-CI-SPEC.md §14.1).

    python3 monitor.py <facility> plan [--as-of YYYY-MM-DD] [--json]
    python3 monitor.py <facility> diff --since YYYY-MM-DD [--as-of YYYY-MM-DD] [--json]

plan  Which watched sources are due (intel/watch.yaml against state/intel.json → monitor.sources), and for each
      the current claims it can settle — what the skill compares a fresh reading against. Also what is not
      watched: in-scope competitors with no active source, and material categories no source covers.
diff  The claim delta since a date, as OCI §7.4 asks: every supersession and every new material claim, classed
      material / notable / noise by the manifest's rules, with its change type and owners, and whether an
      intel-change already records it. What has no change event yet is what the skill writes.

Reads only. The reading of sources and every write (claims, change events, the cursor in state/intel.json)
belong to the skill, through project-state; this script says what is due and what changed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intel_lib import AFFECTED, CHANGE_TYPE, DEFAULT_MATERIAL_CATEGORIES, Facility, to_date  # noqa: E402

VIAS = ["web.read", "documents.search", "deals.read", "messages.search", "mail.search"]


def plan(f: Facility):
    watch = f.watch or {}
    default_every = int(watch.get("cadence_days") or 7)
    cursors = ((f.state.get("monitor") or {}).get("sources") or {})
    due, waiting, paused, problems = [], [], [], []
    seen_ids = set()
    for s in watch.get("sources") or []:
        sid = s.get("id")
        if not sid or sid in seen_ids:
            problems.append(f"source without a unique id: {s}")
            continue
        seen_ids.add(sid)
        if s.get("entity") not in f.entities:
            problems.append(f"{sid}: entity {s.get('entity')} is not on the map")
        if s.get("via", "web.read") not in VIAS:
            problems.append(f"{sid}: via {s.get('via')} is not a connector capability ({', '.join(VIAS)})")
        status = s.get("status", "active")
        if status != "active":
            paused.append({"id": sid, "status": status})
            continue
        every = int(s.get("every_days") or default_every)
        cur = cursors.get(sid) or {}
        last = to_date(cur.get("last_checked"))
        age = (f.as_of - last).days if last else None
        claims = [{"id": c["id"], "category": c.get("category"), "statement": c.get("statement"), "epistemic_status": c.get("epistemic_status"),
                   "confidence": c.get("confidence"), "freshness": f.freshness(c), "source_ref": (c.get("source") or {}).get("ref"), "material": bool(c.get("material"))}
                  for c in f.current_claims(s.get("entity"), s.get("categories"))]
        row = {"id": sid, "entity": s.get("entity"), "name": f.name(s.get("entity")), "ref": s.get("ref"), "via": s.get("via", "web.read"),
               "categories": s.get("categories") or [], "every_days": every, "last_checked": cur.get("last_checked"), "last_status": cur.get("last_status"),
               "days_since": age, "claims": claims}
        (due if last is None or age >= every else waiting).append(row)
    active_entities = {s.get("entity") for s in (watch.get("sources") or []) if s.get("status", "active") == "active"}
    material = (f.comp.get("monitor") or {}).get("significance", {}).get("material_categories") or DEFAULT_MATERIAL_CATEGORIES
    covered = {}
    for s in watch.get("sources") or []:
        if s.get("status", "active") == "active":
            covered.setdefault(s.get("entity"), set()).update(s.get("categories") or [])
    unwatched = [{"entity": e, "name": f.name(e)} for e in f.in_scope() if e not in active_entities]
    thin = [{"entity": e, "name": f.name(e), "uncovered": sorted(set(material) - covered.get(e, set()))} for e in f.in_scope() if e in active_entities and set(material) - covered.get(e, set())]
    last_run = (f.state.get("monitor") or {}).get("last_run")
    return {"as_of": str(f.as_of), "last_run": last_run, "cadence_days": default_every, "due": sorted(due, key=lambda r: (r["last_checked"] or "", r["id"])),
            "waiting": waiting, "paused": paused, "unwatched": unwatched, "thin": thin, "problems": problems,
            "overdue": [r["id"] for r in due if r["days_since"] is None or r["days_since"] >= 2 * r["every_days"]]}


def classify(f: Facility, new, old=None):
    """(change_type, significance, affected) for a claim delta; significance follows the manifest's material categories."""
    material_cats = (f.comp.get("monitor") or {}).get("significance", {}).get("material_categories") or DEFAULT_MATERIAL_CATEGORIES
    cat = new.get("category")
    if old is not None:
        sig = "material" if old.get("material") and cat in material_cats else "notable" if old.get("material") or new.get("material") else "noise"
    else:
        sig = "notable" if new.get("material") and cat in material_cats else "noise"
    affected = AFFECTED.get(cat, [])
    if not affected:
        sig = "noise"  # OCI §7.4: an event nobody owns is noise by definition
    return CHANGE_TYPE.get(cat, "positioning"), sig, affected


def diff(f: Facility, since):
    recorded = {}
    for x in f.changes.values():
        for a in x.get("after") or []:
            recorded.setdefault(a, []).append(x["id"])
    deltas = []
    for c in sorted(f.claims.values(), key=lambda c: (str(c.get("created")), c["id"])):
        created = to_date(c.get("created"))
        if created is None or created < since or created > f.as_of:
            continue
        old = f.claims.get(c.get("supersedes")) if c.get("supersedes") else None
        if f.subject(c) == f.self_id:
            continue  # claims about us are not competitive change
        # A change is a claim delta (OCI §7.4): a supersession, or something new a watched source showed the monitor.
        # A first claim from research is knowledge acquired, not a change in the competitor.
        if old is None and (c.get("logged_by") != "intel-monitor" or not c.get("material")):
            continue
        ctype, sig, affected = classify(f, c, old)
        deltas.append({"subject": f.subject(c), "name": f.name(f.subject(c)), "change_type": ctype, "significance": sig, "affected": affected,
                       "before": [old["id"]] if old else [], "after": [c["id"]], "category": c.get("category"), "detected_at": str(created),
                       "statement": c.get("statement"), "was": old.get("statement") if old else None, "recorded_as": recorded.get(c["id"], [])})
    return {"as_of": str(f.as_of), "since": str(since), "deltas": deltas,
            "unrecorded": [d for d in deltas if not d["recorded_as"] and d["significance"] != "noise"],
            "by_significance": {k: sum(1 for d in deltas if d["significance"] == k) for k in ("material", "notable", "noise")}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    ap.add_argument("verb", choices=["plan", "diff"])
    ap.add_argument("--since")
    ap.add_argument("--as-of")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    f = Facility(a.facility, a.as_of)
    if a.verb == "plan":
        out = plan(f)
        if a.json:
            print(json.dumps(out, indent=1, default=str))
            return 0
        print(f"monitor plan · {out['as_of']} · last run {out['last_run'] or 'never'} · default cadence {out['cadence_days']} d")
        for r in out["due"]:
            print(f"  DUE  {r['id']} · {r['name']} · {r['via']} {r['ref']} · {', '.join(r['categories'])} · last {r['last_checked'] or 'never'}{' · OVERDUE' if r['id'] in out['overdue'] else ''}")
            for c in r["claims"]:
                print(f"         {c['id']} {c['category']} · {c['epistemic_status']} · {c['freshness']} — {c['statement'][:90]}")
        for r in out["waiting"]:
            print(f"  ok   {r['id']} · checked {r['last_checked']} ({r['days_since']} d ago)")
        for u in out["unwatched"]:
            print(f"  NOT WATCHED  {u['entity']} {u['name']} — in scope, no active source")
        for t in out["thin"]:
            print(f"  thin {t['entity']} {t['name']} — no source for {', '.join(t['uncovered'])}")
        for p in out["problems"]:
            print(f"  PROBLEM  {p}")
        return 0
    if not a.since:
        ap.error("diff needs --since YYYY-MM-DD")
    out = diff(f, to_date(a.since))
    if a.json:
        print(json.dumps(out, indent=1, default=str))
        return 0
    print(f"claim delta {out['since']} → {out['as_of']}: " + ", ".join(f"{n} {k}" for k, n in out["by_significance"].items()))
    for d in out["deltas"]:
        print(f"  {d['significance']:<8} {d['subject']} {d['change_type']}: {', '.join(d['before']) or '—'} → {', '.join(d['after'])}  {'recorded as ' + ', '.join(d['recorded_as']) if d['recorded_as'] else 'NO CHANGE EVENT YET' if d['significance'] != 'noise' else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
