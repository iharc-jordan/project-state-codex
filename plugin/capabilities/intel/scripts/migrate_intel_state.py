#!/usr/bin/env python3
"""migrate_intel_state — move a standalone intel-state/ facility into a project's intel capability
(docs/INTEL-CAPABILITY-SPEC.md §10 step 4).

    python3 migrate_intel_state.py <intel-state dir> <project-state dir>                       # plan: prints what it would do
    python3 migrate_intel_state.py <intel-state dir> <project-state dir> --write --actor <email> [--focus "..."]

Non-destructive: the old tree is read, never changed; archiving it is the operator's call. What moves:

- entities, signals and mandates, renumbered to the capability's fixed ids (INT-E-NNN, INT-S-NNN, INT-M-NNN) after
  whatever the project already holds; every reference to an old id — in relationships, entities_referenced,
  entity_id, and in prose — is rewritten; each record keeps `migrated_from: <old id>` and anything the capability
  has no field for under `legacy:` (nothing is dropped);
- `domain:` is dropped (the project is the domain); drifted field names are mapped (overview → summary,
  headline + detail → summary, intel_gaps → research_questions, sources → urls, entities → entities_referenced,
  confidence → intelligence_value, web-harvest → web_harvest);
- the research agenda moves out of the old manifest into intel/agenda.yaml (merged with any agenda already there);
- counters into state/intel.json; reports, longlists and network maps are copied under intel/reports/migrated/
  and intel/network/;
- the capabilities.intel block is added to the manifest when absent (focus is REQUIRED: --focus, or the plan
  shows the old facility's description as a proposal and --write refuses without it); entity and mandate types
  the old facility used are added to the declared types.

Re-running is safe: a record whose `migrated_from` already exists in the project is skipped. Each written file is
logged to logs/activity.ndjson under --actor, with one intel.migrated summary line; the id map is written to
intel/reports/migrated/id-map-YYYY-MM-DD.md. Unprocessed files in the old inbox are listed, not moved.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("migrate: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

DEFAULT_TYPES = ["vendor", "competitor", "regulator", "partner", "infrastructure", "adjacent", "self"]
DEFAULT_MANDATE_TYPES = ["integration-partnership", "licensing", "pilot", "research-engagement"]
ENTITY_STATUS = ["active_research", "active_engagement", "watch", "inactive", "archived"]
MANDATE_STATUS = ["prospecting", "proposed", "active", "completed", "stalled", "closed"]
SIGNAL_TYPES = ["market_intelligence", "competitive", "integration", "regulatory", "customer", "technology"]
SOURCES = ["web_harvest", "document_inbox", "slack", "email", "meeting", "document", "manual"]
OLD_ID = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-[A-Z]-\d{2,}\b")

E_KEEP = {"id", "type", "name", "priority", "status", "summary", "key_facts", "research_questions", "urls", "relationships", "tags", "created", "last_updated"}
S_KEEP = {"id", "signal_type", "subtype", "date", "source", "source_url", "logged_by", "summary", "entities_referenced", "intelligence_value", "became", "tags", "created"}
M_KEEP = {"id", "type", "entity_id", "status", "owner", "summary", "milestones", "tags", "created"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "other"


def yload(p: Path):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ydump(d) -> str:
    return yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=110)


def records(d: Path):
    out = []
    if d.is_dir():
        for f in sorted(d.glob("*.y*ml")):
            try:
                doc = yload(f)
            except Exception as e:
                out.append({"_error": f"{f.name}: {e}"})
                continue
            if isinstance(doc, dict) and doc.get("id"):
                doc["_file"] = f.name
                out.append(doc)
    return out


def num(old_id):
    m = re.search(r"(\d+)$", str(old_id))
    return int(m.group(1)) if m else 0


def rewrite(v, idmap):
    """Replace every old id with its new one, anywhere in a value."""
    if isinstance(v, str):
        return OLD_ID.sub(lambda m: idmap.get(m.group(0), m.group(0)), v)
    if isinstance(v, list):
        return [rewrite(x, idmap) for x in v]
    if isinstance(v, dict):
        return {k: rewrite(x, idmap) for k, x in v.items()}
    return v


def text(*vals):
    return "\n\n".join(str(v).strip() for v in vals if v not in (None, "", [])) or None


def day(v, fallback):
    v = v or fallback
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return str(v)


def plan(src: Path, dst: Path, focus=None, today=None):
    today = today or dt.date.today().isoformat()
    old = yload(src / "manifest.yaml") if (src / "manifest.yaml").exists() else {}
    man = yload(dst / "manifest.yaml")
    block = ((man.get("capabilities") or {}).get("intel")) or None
    state = json.loads((dst / "state" / "intel.json").read_text()) if (dst / "state" / "intel.json").exists() else {}
    counters = dict((state.get("counters") or {}))

    def existing(kind):
        d = dst / "intel" / kind
        return records(d)

    have = {k: existing(k) for k in ("entities", "signals", "mandates")}
    done = {r.get("migrated_from"): r["id"] for k in have for r in have[k] if r.get("migrated_from")}
    nxt = {"entities": max([counters.get("entity", 0)] + [num(r["id"]) for r in have["entities"]]),
           "signals": max([counters.get("signal", 0)] + [num(r["id"]) for r in have["signals"]]),
           "mandates": max([counters.get("mandate", 0)] + [num(r["id"]) for r in have["mandates"]])}
    letter = {"entities": "E", "signals": "S", "mandates": "M"}
    src_recs = {k: [r for r in records(src / k) if "_error" not in r] for k in ("entities", "signals", "mandates")}
    errors = [r["_error"] for k in ("entities", "signals", "mandates") for r in records(src / k) if "_error" in r]
    idmap, skipped = {}, []
    for k in ("entities", "signals", "mandates"):
        for r in sorted(src_recs[k], key=lambda r: (num(r["id"]), r["id"])):
            if r["id"] in done:
                idmap[r["id"]] = done[r["id"]]
                skipped.append(r["id"])
                continue
            nxt[k] += 1
            idmap[r["id"]] = f"INT-{letter[k]}-{nxt[k]:03d}"

    types, mtypes = set(), set()
    out = {"entities": [], "signals": [], "mandates": []}
    for r in src_recs["entities"]:
        if r["id"] in skipped:
            continue
        rel = r.get("relationship_type")
        typ = rel if rel in DEFAULT_TYPES else slug(r.get("type") or r.get("entity_type") or rel or "vendor")
        types.add(typ)
        st = r.get("status")
        status = st if st in ENTITY_STATUS else {"active": "active_engagement", "engaged": "active_engagement", "research": "active_research", "prospect": "active_research", "competitor": "watch", "retired": "archived", "dormant": "inactive"}.get(str(st).lower(), "watch")
        e = {"id": idmap[r["id"]], "type": typ, "name": r.get("name") or r["id"], "priority": r.get("priority") if r.get("priority") in ("P0", "P1", "P2", "P3") else "P2",
             "status": status, "summary": text(r.get("summary"), r.get("overview"), r.get("description")) or r.get("name"),
             "key_facts": r.get("key_facts") or [], "research_questions": r.get("research_questions") or r.get("intel_gaps") or [],
             "urls": r.get("urls") or r.get("sources") or [], "relationships": r.get("relationships") or [], "tags": list(r.get("tags") or []) + [f"alias:{a}" for a in r.get("aliases") or []],
             "created": day(r.get("created"), today), "last_updated": day(r.get("last_updated") or r.get("created"), today), "migrated_from": r["id"]}
        legacy = {k: v for k, v in r.items() if k not in E_KEEP | {"_file", "domain", "overview", "description", "intel_gaps", "sources", "aliases", "entity_type", "relationship_type"}}
        if st not in ENTITY_STATUS and st is not None:
            legacy["status"] = st
        for k in ("entity_type", "relationship_type"):
            if r.get(k):
                legacy[k] = r[k]
        if legacy:
            e["legacy"] = legacy
        out["entities"].append({**rewrite(e, idmap), "migrated_from": r["id"]})
    for r in src_recs["signals"]:
        if r["id"] in skipped:
            continue
        st = r.get("signal_type") or r.get("type")
        src_v = str(r.get("source") or "manual").replace("-", "_")
        val = r.get("intelligence_value") or r.get("confidence") or r.get("value")
        s = {"id": idmap[r["id"]], "signal_type": st if st in SIGNAL_TYPES else "market_intelligence", "subtype": r.get("subtype") or (st if st not in SIGNAL_TYPES else None),
             "date": day(r.get("date") or r.get("created"), today), "source": src_v if src_v in SOURCES else "manual",
             "source_url": r.get("source_url") or r.get("url"), "logged_by": r.get("logged_by") if r.get("logged_by") in ("intel-harvester", "intel-ingest", "manual") else "manual",
             "summary": text(r.get("summary"), r.get("headline"), r.get("detail")) or "(no summary in the source record)",
             "entities_referenced": r.get("entities_referenced") or r.get("entities") or [], "intelligence_value": val if val in ("high", "medium", "low") else "medium",
             "became": r.get("became") or [], "tags": r.get("tags") or [], "created": day(r.get("created") or r.get("date"), today), "migrated_from": r["id"]}
        legacy = {k: v for k, v in r.items() if k not in S_KEEP | {"_file", "domain", "type", "headline", "detail", "entities", "confidence", "value", "url"}}
        if src_v not in SOURCES:
            legacy["source"] = r.get("source")
        if legacy:
            s["legacy"] = legacy
        out["signals"].append({**rewrite(s, idmap), "migrated_from": r["id"]})
    # A mandate must name its entity. Old mandates with no client are the organisation's own engagements: they get
    # the project's self entity (created here when there is none), tagged so the operator can reassign them.
    needs_self = [r for r in src_recs["mandates"] if r["id"] not in skipped and not (r.get("entity_id") or r.get("client_partner") or r.get("partner"))]
    self_id, self_created = None, None
    for r in have["entities"] + out["entities"]:
        if r.get("type") == "self":
            self_id = r["id"]
            break
    if needs_self and not self_id:
        nxt["entities"] += 1
        self_id = f"INT-E-{nxt['entities']:03d}"
        pname = ((man.get("project") or {}).get("name")) or ((man.get("project") or {}).get("long_name")) or man.get("name") or (man.get("facility") or {}).get("name") or dst.resolve().parent.name
        self_created = {"id": self_id, "type": "self", "name": f"{pname} — us", "priority": "P0", "status": "active_research",
                        "summary": "Us. Created by the intel-state migration to hold the engagements the old facility recorded with no client; claims about our own product make battlecards provable.",
                        "key_facts": [], "research_questions": [], "urls": [], "relationships": [], "tags": ["migration:created"], "created": day(None, today), "last_updated": day(None, today)}
        out["entities"].append(self_created)
        types.add("self")
    for r in src_recs["mandates"]:
        if r["id"] in skipped:
            continue
        typ = slug(r.get("type") or r.get("mandate_type") or "engagement")
        mtypes.add(typ)
        st = r.get("status")
        named = r.get("entity_id") or r.get("client_partner") or r.get("partner")
        m = {"id": idmap[r["id"]], "type": typ, "entity_id": named or self_id,
             "status": st if st in MANDATE_STATUS else "active" if str(st).lower() in ("active", "in_progress", "live") else "proposed",
             "owner": r.get("owner"), "summary": text(r.get("summary"), r.get("name"), r.get("description")) or r["id"], "milestones": r.get("milestones") or [],
             "tags": r.get("tags") or [], "created": day(r.get("created"), today), "migrated_from": r["id"]}
        legacy = {k: v for k, v in r.items() if k not in M_KEEP | {"_file", "domain", "mandate_type", "client_partner", "partner", "name", "description"}}
        if st not in MANDATE_STATUS and st is not None:
            legacy["status"] = st
        if not named:
            m["tags"] = list(m["tags"]) + ["migration:entity-unassigned"]
        if legacy:
            m["legacy"] = legacy
        out["mandates"].append({**rewrite(m, idmap), "migrated_from": r["id"]})

    agenda = old.get("research_agenda") or {}
    tiers = {t: [rewrite(q, idmap) if isinstance(q, str) else rewrite(q, idmap) for q in (agenda.get(t) or [])] for t in ("p0", "p1", "p2", "p3")} if isinstance(agenda, dict) else {}
    proposed_focus = text((old.get("facility") or {}).get("description"), (old.get("product") or {}).get("description"))
    orphans = sorted({i for k in out for r in out[k] for i in OLD_ID.findall(json.dumps(r, default=str)) if i not in idmap and not i.startswith("INT-")})
    copies = []
    for sub, to in (("reports", "intel/reports/migrated"), ("longlist", "intel/reports/migrated/longlist"), ("network", "intel/network")):
        d = src / sub
        if d.is_dir():
            copies += [(f, dst / to / f.relative_to(d)) for f in sorted(d.rglob("*")) if f.is_file()]
    inbox = [str(f.relative_to(src)) for f in sorted((src / "inbox").glob("*")) if f.is_file() and not f.name.startswith(".")] if (src / "inbox").is_dir() else []
    return {"src": str(src), "dst": str(dst), "today": today, "idmap": idmap, "skipped": skipped, "records": out, "agenda": tiers,
            "types": sorted(types), "mandate_types": sorted(mtypes), "block_present": block is not None, "focus": focus, "proposed_focus": proposed_focus,
            "staleness": old.get("staleness_threshold_days"), "counters": {"entity": nxt["entities"], "signal": nxt["signals"], "mandate": nxt["mandates"]},
            "copies": copies, "inbox": inbox, "orphans": orphans, "errors": errors, "state": state,
            "self_created": self_created, "self_for": [idmap[r["id"]] for r in needs_self]}


def manifest_block(p):
    types = list(dict.fromkeys(DEFAULT_TYPES + p["types"]))
    mtypes = list(dict.fromkeys(DEFAULT_MANDATE_TYPES + p["mandate_types"]))
    lines = ["  intel:", "    enabled: true", '    version: "1.2.0"', "    pack: intel-default", f"    focus: {json.dumps(p['focus'])}",
             f"    entity_types: [{', '.join(types)}]", f"    mandate_types: [{', '.join(mtypes)}]", f"    staleness_threshold_days: {int(p['staleness'] or 14)}",
             f"    # migrated from a standalone intel-state facility on {p['today']} (capabilities/intel/scripts/migrate_intel_state.py);",
             "    # the competitive: sub-block takes the capability's defaults until intel-onboarding competitive sets it."]
    return "\n".join(lines) + "\n"


def write(p, actor):
    dst = Path(p["dst"])
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = []
    kinds = {"entities": ("intel-entity", "intel.entity.added"), "signals": ("intel-signal", "intel.signal.logged"), "mandates": ("intel-mandate", "intel.mandate.updated")}
    for k, recs in p["records"].items():
        for r in recs:
            f = dst / "intel" / k / f"{r['id']}.yaml"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(ydump(r), encoding="utf-8")
            log.append({"ts": ts, "actor": actor, "skill": "intel-onboarding", "event": kinds[k][1], "id": r["id"], "detail": f"migrated from {r['migrated_from']}" if r.get("migrated_from") else "created by the migration"})
    for sub in ("network", "reports", "claims", "changes", "profiles", "battlecards", "deals", "answers", "winloss", "monitor"):
        (dst / "intel" / sub).mkdir(parents=True, exist_ok=True)
    ag = dst / "intel" / "agenda.yaml"
    cur = (yload(ag) if ag.exists() else None) or {"schema_version": 1, "tiers": {}}
    cur.setdefault("tiers", {})
    for t, qs in p["agenda"].items():
        have = cur["tiers"].get(t) or []
        cur["tiers"][t] = have + [q for q in qs if q not in have]
    ag.write_text(ydump(cur), encoding="utf-8")
    st = p["state"] or {}
    st.setdefault("counters", {})
    for k, v in p["counters"].items():
        st["counters"][k] = max(int(st["counters"].get(k, 0)), v)
    for k in ("claim", "change", "winloss"):
        st["counters"].setdefault(k, 0)
    st.setdefault("cursors", {}); st.setdefault("projections", {}); st.setdefault("monitor", {"last_run": None, "sources": {}})
    (dst / "state").mkdir(exist_ok=True)
    (dst / "state" / "intel.json").write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
    for a, b in p["copies"]:
        b.parent.mkdir(parents=True, exist_ok=True)
        if not b.exists():
            shutil.copy2(a, b)
    if not p["block_present"]:
        mp = dst / "manifest.yaml"
        t = mp.read_text(encoding="utf-8")
        blk = manifest_block(p)
        if re.search(r"^capabilities:\s*$", t, re.M):
            t = re.sub(r"^capabilities:\s*$", "capabilities:\n" + blk.rstrip("\n"), t, count=1, flags=re.M)
        elif re.search(r"^capabilities:", t, re.M):
            raise SystemExit("migrate: manifest has an inline capabilities: value; add the intel block by hand (intel-onboarding), then re-run")
        else:
            t = t.rstrip("\n") + "\n\ncapabilities:\n" + blk
        mp.write_text(t, encoding="utf-8")
        log.append({"ts": ts, "actor": actor, "skill": "intel-onboarding", "event": "capability.enabled", "id": "intel", "detail": "intel 1.2.0 enabled by migration from a standalone intel-state facility"})
    idm = dst / "intel" / "reports" / "migrated" / f"id-map-{p['today']}.md"
    idm.parent.mkdir(parents=True, exist_ok=True)
    idm.write_text(f"# intel-state → intel capability, {p['today']}\n\nFrom `{p['src']}`. The old tree was not changed.\n\n| Old id | New id |\n|---|---|\n"
                   + "".join(f"| {o} | {n} |\n" for o, n in p["idmap"].items()), encoding="utf-8")
    counts = {k: len(v) for k, v in p["records"].items()}
    log.append({"ts": ts, "actor": actor, "skill": "intel-onboarding", "event": "intel.migrated", "id": None,
                "detail": f"from {p['src']}: {counts['entities']} entities, {counts['signals']} signals, {counts['mandates']} mandates, {len(p['copies'])} files copied, {len(p['skipped'])} already migrated; id map {idm.relative_to(dst)}"})
    (dst / "logs").mkdir(exist_ok=True)
    with open(dst / "logs" / "activity.ndjson", "a", encoding="utf-8") as f:
        for line in log:
            f.write(json.dumps(line) + "\n")
    return len(log)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="the standalone intel-state/ folder")
    ap.add_argument("dst", help="the project's project-state/ folder")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--actor")
    ap.add_argument("--focus")
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    src, dst = Path(a.src), Path(a.dst)
    if not (dst / "manifest.yaml").exists():
        raise SystemExit(f"migrate: {dst} holds no manifest.yaml")
    if not (src / "entities").is_dir() and not (src / "signals").is_dir():
        raise SystemExit(f"migrate: {src} has no entities/ or signals/ — not an intel-state facility")
    p = plan(src, dst, a.focus, a.today)
    c = {k: len(v) for k, v in p["records"].items()}
    print(f"intel-state {src} → {dst}")
    print(f"  {c['entities']} entities, {c['signals']} signals, {c['mandates']} mandates to write; {len(p['skipped'])} already migrated")
    print(f"  ids: " + ", ".join(f"{o}→{n}" for o, n in list(p["idmap"].items())[:6]) + (" …" if len(p["idmap"]) > 6 else ""))
    print(f"  agenda: " + ", ".join(f"{t} {len(q)}" for t, q in p["agenda"].items()) if any(p["agenda"].values()) else "  agenda: none in the old manifest")
    print(f"  entity types: {', '.join(p['types']) or '—'} · mandate types: {', '.join(p['mandate_types']) or '—'}")
    print(f"  files copied: {len(p['copies'])} (reports, longlists, network)")
    if p["block_present"]:
        print("  manifest: capabilities.intel present — left as is; add any new types above to its entity_types / mandate_types")
    else:
        print(f"  manifest: capabilities.intel will be added · focus: {p['focus'] or 'NOT GIVEN'}")
        if not p["focus"] and p["proposed_focus"]:
            print(f"    proposed (from the old facility, edit before using): {p['proposed_focus'][:300]}")
    if p["self_for"]:
        print(f"  {len(p['self_for'])} mandate(s) name no client — assigned to the self entity {'(created: ' + p['self_created']['id'] + ' ' + p['self_created']['name'] + ')' if p['self_created'] else ''} and tagged migration:entity-unassigned: {', '.join(p['self_for'])}")
    if p["inbox"]:
        print(f"  old inbox holds {len(p['inbox'])} file(s), not moved — drop them into documents/inbox/ for intel-ingest: {', '.join(p['inbox'][:5])}")
    if p["orphans"]:
        print(f"  references to ids that are not in the facility (left as written): {', '.join(p['orphans'][:10])}")
    for e in p["errors"]:
        print(f"  UNREADABLE  {e}")
    if not a.write:
        print("  plan only: re-run with --write --actor <email> [--focus \"...\"]")
        return 0
    if not a.actor:
        raise SystemExit("migrate: --write needs --actor <email> (who the activity log says did this)")
    if p["errors"]:
        raise SystemExit(f"migrate: {len(p['errors'])} record(s) are unreadable — fix them in the old facility first; a migration never drops a record silently")
    if not p["block_present"] and not p["focus"]:
        raise SystemExit("migrate: the project has no intel block and no --focus was given — focus is REQUIRED (no focus, no harvest)")
    n = write(p, a.actor)
    print(f"  written; {n} line(s) appended to logs/activity.ndjson. Next: validate (project-state), then /intel-onboarding competitive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
