#!/usr/bin/env python3
"""migrate_research_state — move a standalone `.research-state/` facility into a project's research capability
(docs/RESEARCH-CAPABILITY-SPEC.md §11.2).

    python3 migrate_research_state.py <.research-state dir> <project-state dir>                 # plan: prints what it would do
    python3 migrate_research_state.py <.research-state dir> <project-state dir> --write --actor <email>

Non-destructive: the old tree is read, never changed. What moves, per §11.2:
  ids        MND→RES-M, STEP→RES-S, FND→RES-F, CHL→RES-C, CND→RES-L — numbers kept when free, renumbered after
             what the project already holds otherwise; every reference rewritten; the map written to
             research/migration-map.yaml; each record keeps `migrated_from:`
  layout     per-mandate directories flattened into research/{mandates,steps,findings,challenges,candidates}/
  questions  plain question strings become structured questions Q1…Qn
  findings   evidence strings + source_refs become evidence items {excerpt, ref, retrieved_at}; `epistemic_status:
             reported` (`hypothesis` on the speculative tier), `status: established`, `migrated_from:`. The old
             records do not say which question a finding answers, so `answers` is inferred from the overlap between the
             claim and each question's words and flagged (`legacy.answers_inferred`); a finding matching none answers
             Q1 and is flagged `legacy.answers_unmatched` for a person to move. `category: migrated` (the default 365-day
             half-life) — the old facility had no half-lives. History lost to in-place edits in the old facility
             cannot be recovered; this script says so rather than inventing a supersession chain.
  candidates statuses mapped (ranked → scored, top_N → shortlisted, discarded → excluded); scores keep their
             justification, and their source_refs are linked to the findings that cite the same references — a score
             no finding backs keeps `sources:` and is reported for re-linking
  challenges `raised_by` → `logged_by`; a ruled challenge's `resolved_by` must name a person — the old list is kept
             in `resolution` and `resolved_by` records who migrated it
  sources    SRC records registered through the curator: originals copied to documents/research-sources/ and
             entered in documents/index.yaml; their mandate_relevance moved onto each mandate's source_relevance
  CON/PUB/LESSON → people/, publications/, lessons-learned/
  activity   events renamed to research.* (where the research vocabulary has them) and appended to the host log
  counters   → state/research.json; the learned store → research/learned/; old run logs → research/runs/migrated/
The manifest gains the capabilities.research block when absent. Re-running is safe: records already migrated
(by `migrated_from`) are skipped. `--write` refuses while any old record is unreadable — nothing is dropped silently.
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

OLD = {"MND": "RES-M", "STEP": "RES-S", "FND": "RES-F", "CHL": "RES-C", "CND": "RES-L"}
KIND = {"MND": "mandates", "STEP": "steps", "FND": "findings", "CHL": "challenges", "CND": "candidates"}
COUNTER = {"MND": "mandate", "STEP": "step", "FND": "finding", "CHL": "challenge", "CND": "candidate"}
OLD_ID = re.compile(r"\b(MND|STEP|FND|CHL|CND)-(\d{3,})\b")
CAND_STATUS = {"discovered": "discovered", "enriched": "enriched", "scored": "scored", "ranked": "scored", "top_N": "shortlisted", "shortlisted": "shortlisted",
               "discarded": "excluded", "excluded": "excluded"}
EVENT = {"mandate.drafted": "research.mandate.drafted", "mandate.iterated": "research.mandate.iterated", "mandate.locked": "research.mandate.locked",
         "mandate.started": "research.mandate.started", "mandate.completed": "research.mandate.completed", "mandate.killed": "research.mandate.killed",
         "step.started": "research.step.started", "step.completed": "research.step.completed", "step.abandoned": "research.step.abandoned",
         "finding.written": "research.finding.logged", "challenge.raised": "research.challenge.raised", "challenge.closed": "research.challenge.ruled",
         "candidate.discovered": "research.candidate.discovered", "candidate.scored": "research.candidate.scored", "candidate.ranked": "research.candidate.ranked",
         "deliverable.shipped": "research.deliverable.shipped", "longlist.shipped": "research.deliverable.shipped", "source.ingested": "research.inbox.drained"}
STOP = set("a an and are as at be by for from has have in is it its of on or that the this to was were will with which who what whether how does do their they any".split())
LOGGED = {"research-step", "research-deepweb", "research-longlist", "research-ingest", "research-walk", "manual"}


def yload(p: Path):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ydump(d) -> str:
    return yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=110)


def toks(s) -> set:
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", str(s).lower()) if w not in STOP and len(w) > 2}


def plan(src: Path, dst: Path, today=None) -> dict:
    today = today or dt.date.today().isoformat()
    errors, recs = [], {k: [] for k in OLD}
    for p in sorted((src / "mandates").glob("MND-*.yaml")):
        try:
            recs["MND"].append((p, yload(p)))
        except Exception as e:
            errors.append(f"{p.relative_to(src)}: {e}")
    for d in sorted((src / "mandates").glob("MND-*")):
        if not d.is_dir():
            continue
        for k in ("STEP", "FND", "CHL", "CND"):
            for p in sorted((d / KIND[k]).glob(f"{k}-*.yaml")):
                try:
                    recs[k].append((p, yload(p)))
                except Exception as e:
                    errors.append(f"{p.relative_to(src)}: {e}")
    man = yload(dst / "manifest.yaml") or {}
    have = {}
    for k in OLD:
        d = dst / "research" / KIND[k]
        for p in sorted(d.glob(f"{OLD[k]}-*.yaml")) if d.is_dir() else []:
            doc = yload(p) or {}
            have[doc.get("migrated_from")] = doc.get("id")
    taken = {k: {p.stem for p in (dst / "research" / KIND[k]).glob(f"{OLD[k]}-*.yaml")} if (dst / "research" / KIND[k]).is_dir() else set() for k in OLD}
    idmap, skipped, nxt = {}, [], {}
    for k in OLD:
        nxt[k] = max([int(x.rsplit("-", 1)[1]) for x in taken[k]] or [0])
        for p, doc in recs[k]:
            oid = (doc or {}).get("id") or p.stem
            if oid in have:
                idmap[oid] = have[oid]
                skipped.append(oid)
                continue
            n = int(OLD_ID.match(oid).group(2)) if OLD_ID.match(oid) else None
            new = f"{OLD[k]}-{n:03d}" if n and f"{OLD[k]}-{n:03d}" not in taken[k] and f"{OLD[k]}-{n:03d}" not in idmap.values() else None
            if not new:
                nxt[k] += 1
                new = f"{OLD[k]}-{nxt[k]:03d}"
            idmap[oid] = new
    rw = lambda v: OLD_ID.sub(lambda m: idmap.get(m.group(0), m.group(0)), v) if isinstance(v, str) else [rw(x) for x in v] if isinstance(v, list) else {kk: rw(x) for kk, x in v.items()} if isinstance(v, dict) else v  # noqa: E731

    # sources → registered documents
    sources, relevance = [], {}
    for p in sorted((src / "sources" / "indexed").glob("SRC-*.yaml")) if (src / "sources" / "indexed").is_dir() else []:
        try:
            s = yload(p) or {}
        except Exception as e:
            errors.append(f"{p.relative_to(src)}: {e}")
            continue
        orig = src / "sources" / "originals" / str(s.get("original_filename") or "")
        doc_path = f"documents/research-sources/{s.get('original_filename') or p.stem + '.md'}"
        sources.append({"id": s.get("id") or p.stem, "doc_path": doc_path, "from": orig if orig.is_file() else None, "title": s.get("original_filename") or s.get("id"),
                        "summary": s.get("summary"), "tags": s.get("tags") or []})
        for mid, score in (s.get("mandate_relevance") or {}).items():
            relevance.setdefault(mid, []).append({"ref": doc_path, "score": score})
    src_path = {s["id"]: s["doc_path"] for s in sources}
    ref = lambda r: src_path.get(r, r)  # noqa: E731 — an SRC-NNN becomes its registered document; a URL stays a URL

    out = {k: [] for k in OLD}
    notes = {"answers_inferred": 0, "answers_unmatched": [], "scores_unlinked": [], "rulings_migrated": []}
    questions = {}
    for p, m in recs["MND"]:
        if m["id"] in skipped:
            continue
        qs = []
        for i, q in enumerate(m.get("questions") or [], 1):
            text = q.get("text") if isinstance(q, dict) else str(q)
            qs.append({"id": f"Q{i}", "text": text, "state": "open", "answered_by": []})
        questions[m["id"]] = qs
        status = m.get("status") or "draft"
        if status == "locked" and any((s or {}).get("mandate_id") == m["id"] for _, s in recs["STEP"]):
            status = "in-progress"   # the first action moves a locked mandate on (spec §4.2); the old facility never recorded it
        new = {"id": idmap[m["id"]], "kind": "research-mandate", "slug": m.get("slug") or p.stem.split("-", 2)[-1], "status": status,
               "iteration": m.get("iteration") or 1, "headline": m.get("headline"), "questions": qs, "methodology_type": m.get("methodology_type") or "narrative",
               "also_types": m.get("also_types") or [], "methodology": m.get("methodology") or [], "deliverable": m.get("deliverable") or {},
               "success_criteria": m.get("success_criteria") or [], "primary_source_min_ratio": m.get("primary_source_min_ratio") or 0.5,
               "longlist_criteria": m.get("longlist_criteria") or [], "comparison_subjects": m.get("comparison_subjects") or [],
               "comparative_dimensions": m.get("comparative_dimensions") or [], "deepweb_depth_cap": m.get("deepweb_depth_cap") or 3,
               "source_relevance": relevance.get(m["id"], []), "corpus_independent": bool(m.get("corpus_independent")) or not relevance.get(m["id"]),
               "standing": None, "null_result_statement": m.get("null_result_statement"), "locked_at": m.get("locked_at"), "locked_iteration": m.get("locked_iteration"),
               "completed_at": m.get("completed_at"), "killed_at": m.get("killed_at"), "kill_reason": m.get("kill_reason"),
               "owner": m.get("owner"), "created": m.get("created") or m.get("locked_at") or today, "migrated_from": m["id"]}
        out["MND"].append(new)
    mq = {idmap[m["id"]]: questions.get(m["id"], []) for _, m in recs["MND"] if m["id"] in idmap}
    for p, f in recs["FND"]:
        if f["id"] in skipped:
            continue
        mid = idmap.get(f.get("mandate_id"), f.get("mandate_id"))
        qs = mq.get(mid) or []
        ct = toks(f.get("claim"))
        scored = sorted(((len(ct & toks(q["text"])), q["id"]) for q in qs), reverse=True)
        legacy = {k: v for k, v in f.items() if k not in ("id", "mandate_id", "step_id", "claim", "evidence", "source_refs", "independent_sources", "derives_from", "source_tier",
                                                          "confidence", "contradicts", "supports", "created")}
        if scored and scored[0][0] >= 2:
            answers = [scored[0][1]]
            legacy["answers_inferred"] = True
            notes["answers_inferred"] += 1
        else:
            answers = [qs[0]["id"]] if qs else ["Q1"]
            legacy["answers_unmatched"] = True
            notes["answers_unmatched"].append(idmap[f["id"]])
        ev_text = f.get("evidence") or []
        ev_text = [ev_text] if isinstance(ev_text, str) else ev_text
        refs = f.get("source_refs") or []
        n = max(len(ev_text), len(refs))
        created = str(f.get("created") or today)
        evidence = [{"excerpt": ev_text[i] if i < len(ev_text) else None, "ref": ref(refs[i]) if i < len(refs) else None, "retrieved_at": created[:10], "source_date": None} for i in range(n)]
        tier = f.get("source_tier") or "secondary"
        new = {"id": idmap[f["id"]], "kind": "research-finding", "mandate_id": mid, "step_id": idmap.get(f.get("step_id"), f.get("step_id")), "answers": answers,
               "claim": f.get("claim"), "evidence": evidence, "source_tier": tier, "confidence": f.get("confidence") or "low",
               "epistemic_status": "hypothesis" if tier == "speculative" else "reported", "independent_sources": min(int(f.get("independent_sources") or 1), max(1, len(evidence))),
               "derives_from": [ref(x) for x in f.get("derives_from") or []], "category": "migrated", "material": True, "status": "established",
               "supersedes": None, "contradicts": rw(f.get("contradicts") or []), "supports": rw(f.get("supports") or []), "became": [],
               "logged_by": f.get("created_by") if f.get("created_by") in LOGGED else "manual", "run_id": None, "created": created, "migrated_from": f["id"]}
        if legacy:
            new["legacy"] = rw(legacy)
        out["FND"].append(new)
        for q in qs:
            if q["id"] in answers and new["id"] not in q["answered_by"]:
                q["answered_by"].append(new["id"])
                q["state"] = "answered"
    fz = {f["id"]: f for f in out["FND"]}
    for p, s in recs["STEP"]:
        if s["id"] in skipped:
            continue
        inp = s.get("inputs") or {}
        out["STEP"].append({"id": idmap[s["id"]], "kind": "research-step", "mandate_id": idmap.get(s.get("mandate_id"), s.get("mandate_id")),
                            "methodology_step": s.get("methodology_step"), "mode": s.get("mode") or "query", "description": s.get("description"),
                            "status": s.get("status") or "complete", "started_at": s.get("started_at") or today, "completed_at": s.get("completed_at"),
                            "inputs": {"refs": [ref(x) for x in inp.get("source_refs") or []], "queries": inp.get("external_queries") or [], "urls": inp.get("external_urls") or []},
                            "findings_produced": rw(s.get("findings_produced") or [f["id"] for f in fz.values() if f["step_id"] == idmap[s["id"]]]),
                            "summary": s.get("summary"), "open_followups": s.get("open_followups") or [], "run_id": None, "migrated_from": s["id"]})
    for p, c in recs["CHL"]:
        if c["id"] in skipped:
            continue
        ruled = c.get("status") in ("accepted", "rejected", "resolved")
        old_by = c.get("resolved_by")
        res = c.get("resolution")
        if ruled and old_by and not isinstance(old_by, str):
            res = f"{res or ''} [resolved by {', '.join(rw(old_by))} in the old facility]".strip()
        new = {"id": idmap[c["id"]], "mandate_id": idmap.get(c.get("mandate_id"), c.get("mandate_id")), "finding_id": idmap.get(c.get("finding_id"), c.get("finding_id")),
               "kind": c.get("kind"), "argument": rw(c.get("argument")), "severity": c.get("severity") or "material", "status": c.get("status") or "open",
               "proposed_resolution": None, "resolution": rw(res) if res else None, "resolved_by": None, "resolved_at": None,
               "logged_by": c.get("raised_by") or "research-redteam", "created": c.get("created") or today, "migrated_from": c["id"]}
        if ruled:
            new["resolved_by"] = "__ACTOR__"
            notes["rulings_migrated"].append(new["id"])
        out["CHL"].append(new)
    by_ref = {}
    for f in out["FND"]:
        for e in f["evidence"]:
            if e.get("ref"):
                by_ref.setdefault(e["ref"], []).append(f["id"])
    for p, c in recs["CND"]:
        if c["id"] in skipped:
            continue
        scores = []
        for s in c.get("scores") or []:
            fids = sorted({fid for r in s.get("source_refs") or [] for fid in by_ref.get(ref(r), []) if fz[fid]["mandate_id"] == idmap.get(c.get("mandate_id"))})
            row = {"criterion": s.get("criterion"), "score": s.get("value", s.get("score")), "justification": s.get("justification"), "finding_ids": fids}
            if not fids:
                row["sources"] = [ref(r) for r in s.get("source_refs") or []]
                notes["scores_unlinked"].append(f"{idmap[c['id']]}:{s.get('criterion')}")
            scores.append(row)
        profile = dict(c.get("profile") or {})
        for k in ("url", "description"):
            if c.get(k):
                profile[k] = c[k]
        out["CND"].append({"id": idmap[c["id"]], "kind": "research-candidate", "mandate_id": idmap.get(c.get("mandate_id"), c.get("mandate_id")), "name": c.get("name"),
                           "aliases": c.get("aliases") or [], "type": c.get("type") or "other", "profile": profile, "scores": scores, "total": c.get("total"),
                           "rank": c.get("rank"), "status": CAND_STATUS.get(c.get("status"), "discovered"), "discovered_via": c.get("discovered_via") or "import",
                           "created": c.get("discovered_at") or today, "migrated_from": c["id"]})
    events = []
    log = src / "activity.ndjson"
    if log.is_file():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            new_ev = EVENT.get(e.get("kind"))
            if new_ev:
                events.append({"ts": e.get("ts"), "actor": e.get("actor") or "manual", "event": new_ev, "id": idmap.get(e.get("id"), e.get("id")),
                               "detail": f"migrated from {src.name}: {e.get('kind')}" + (f" {e.get('mandate_id')}" if e.get("mandate_id") else "")})
    copies = []
    for sub, to in (("learned", "research/learned"), ("runs", "research/runs/migrated"), ("reports", "research/reports/migrated"), ("drafts", "research/reports/migrated/drafts")):
        d = src / sub
        if d.is_dir():
            copies += [(f, dst / to / f.relative_to(d)) for f in sorted(d.rglob("*")) if f.is_file() and not f.name.startswith(".")]
    for s in sources:
        if s["from"]:
            copies.append((s["from"], dst / s["doc_path"]))
    people = [yload(p) for p in sorted((src / "contacts").glob("*.yaml"))] if (src / "contacts").is_dir() else []
    pubs = [yload(p) for p in sorted((src / "publications").glob("*.yaml"))] if (src / "publications").is_dir() else []
    lessons = [yload(p) for p in sorted((src / "lessons").glob("*.yaml"))] if (src / "lessons").is_dir() else []
    return {"src": str(src), "dst": str(dst), "today": today, "idmap": idmap, "skipped": skipped, "records": out, "events": events, "copies": copies,
            "sources": sources, "people": people, "publications": pubs, "lessons": lessons, "errors": errors, "notes": notes,
            "counters": {COUNTER[k]: max([int(v.rsplit("-", 1)[1]) for o, v in idmap.items() if o.startswith(k + "-")] + [0]) for k in OLD},
            "block_present": bool((man.get("capabilities") or {}).get("research"))}


def write(p: dict, actor: str) -> int:
    dst = Path(p["dst"])
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = []
    for k, recs in p["records"].items():
        for r in recs:
            if r.get("resolved_by") == "__ACTOR__":
                r["resolved_by"] = actor
                r["resolved_at"] = ts
            f = dst / "research" / KIND[k] / f"{r['id']}.yaml"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(ydump(r), encoding="utf-8")
    for sub in ("mandates", "steps", "findings", "challenges", "candidates", "changes", "runs", "topics", "reports", "learned"):
        (dst / "research" / sub).mkdir(parents=True, exist_ok=True)
    for a, b in p["copies"]:
        b.parent.mkdir(parents=True, exist_ok=True)
        if not b.exists():
            shutil.copy2(a, b)
    if p["sources"]:
        idx = dst / "documents" / "index.yaml"
        cur = (yload(idx) if idx.exists() else None) or {"docs": []}
        known = {str(d.get("source_path")) for d in cur.get("docs") or [] if isinstance(d, dict)}
        for s in p["sources"]:
            if s["doc_path"] not in known:
                cur.setdefault("docs", []).append({"slug": re.sub(r"[^a-z0-9]+", "-", str(s["title"]).lower()).strip("-"), "title": s["title"], "description": s["summary"],
                                                   "source_path": s["doc_path"], "status": "registered", "tags": s["tags"], "note": f"migrated from {Path(p['src']).name} {s['id']}"})
        idx.parent.mkdir(parents=True, exist_ok=True)
        idx.write_text(ydump(cur), encoding="utf-8")
    for person in p["people"]:
        if isinstance(person, dict) and person.get("name"):
            slug = re.sub(r"[^a-z0-9]+", "-", person["name"].lower()).strip("-")
            f = dst / "people" / f"{slug}.yaml"
            if not f.exists():
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(ydump({"id": slug, "kind": "person", "full_name": person["name"], "created": ts, "created_by": actor, "last_modified": ts, "last_modified_by": actor,
                                    "legacy": person}), encoding="utf-8")
    for pub in p["publications"]:
        if isinstance(pub, dict):
            day = str(pub.get("published_at") or p["today"])[:10]
            slug = re.sub(r"[^a-z0-9]+", "-", str(pub.get("id") or "publication").lower()).strip("-")
            f = dst / "publications" / f"{day}-{slug}.yaml"
            if not f.exists():
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(ydump({"id": f"{day}-{slug}", "kind": "publication", "created": ts, "created_by": actor, "last_modified": ts, "last_modified_by": actor, "legacy": pub}), encoding="utf-8")
    for les in p["lessons"]:
        if isinstance(les, dict):
            day = str(les.get("created") or p["today"])[:10]
            slug = re.sub(r"[^a-z0-9]+", "-", str(les.get("title") or les.get("id") or "lesson").lower()).strip("-")[:60]
            f = dst / "lessons-learned" / f"{day}-{slug}.md"
            if not f.exists():
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(f"---\nid: {day}-{slug}\ndate: {day}\ntitle: {json.dumps(les.get('title') or les.get('id'))}\ncreated: {ts}\ncreated_by: {actor}\n---\n\n{les.get('lesson') or les.get('body') or ''}\n", encoding="utf-8")
    state_p = dst / "state" / "research.json"
    st = json.loads(state_p.read_text()) if state_p.exists() else {}
    st.setdefault("counters", {})
    for k, v in p["counters"].items():
        st["counters"][k] = max(int(st["counters"].get(k, 0)), v)
    st["counters"].setdefault("change", 0)
    st.setdefault("walk", {"active": None, "last_run": None}); st.setdefault("last_brief", None); st.setdefault("last_sweep", None)
    state_p.parent.mkdir(exist_ok=True)
    state_p.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
    mp = dst / "research" / "migration-map.yaml"
    prior = (yload(mp) if mp.exists() else None) or {}
    prior.setdefault("migrations", []).append({"from": p["src"], "at": ts, "by": actor, "ids": {o: n for o, n in p["idmap"].items() if o not in p["skipped"]},
                                               "notes": {"answers_inferred": p["notes"]["answers_inferred"], "answers_unmatched": p["notes"]["answers_unmatched"],
                                                         "scores_unlinked": p["notes"]["scores_unlinked"], "rulings_migrated": p["notes"]["rulings_migrated"],
                                                         "history": "in-place edits in the old facility are not recoverable; no supersession chain was invented"}})
    mp.write_text(ydump(prior), encoding="utf-8")
    if not p["block_present"]:
        mf = dst / "manifest.yaml"
        t = mf.read_text(encoding="utf-8")
        blk = ('  research:\n    enabled: true\n    version: "0.1.0"\n    pack: research-default\n'
               f'    # migrated from a standalone .research-state facility on {p["today"]} (capabilities/research/scripts/migrate_research_state.py);\n'
               '    # defaults, half_lives_days, walk, learning and crossings take the capability defaults (templates/manifest-block.yaml).\n')
        if re.search(r"^capabilities:\s*$", t, re.M):
            t = re.sub(r"^capabilities:\s*$", "capabilities:\n" + blk.rstrip("\n"), t, count=1, flags=re.M)
        elif re.search(r"^capabilities:", t, re.M):
            raise SystemExit("migrate: the manifest has an inline capabilities: value; enable research by hand (research-onboarding), then re-run")
        else:
            t = t.rstrip("\n") + "\n\ncapabilities:\n" + blk
        mf.write_text(t, encoding="utf-8")
        log.append({"ts": ts, "actor": actor, "event": "capability.enabled", "id": "research", "detail": "research 0.1.0 enabled by migration from a standalone .research-state facility"})
    for e in p["events"]:
        log.append(e)
    counts = {k: len(v) for k, v in p["records"].items()}
    log.append({"ts": ts, "actor": actor, "event": "research.migrated", "id": None,
                "detail": f"from {p['src']}: {counts['MND']} mandates, {counts['STEP']} steps, {counts['FND']} findings, {counts['CHL']} challenges, {counts['CND']} candidates; map research/migration-map.yaml"})
    (dst / "logs").mkdir(exist_ok=True)
    with open(dst / "logs" / "activity.ndjson", "a", encoding="utf-8") as f:
        for line in log:
            f.write(json.dumps(line) + "\n")
    return len(log)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="the old .research-state/ folder")
    ap.add_argument("dst", help="the project's project-state/ folder")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--actor")
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    src, dst = Path(a.src), Path(a.dst)
    if not (dst / "manifest.yaml").exists():
        raise SystemExit(f"migrate: {dst} holds no manifest.yaml")
    if not (src / "mandates").is_dir():
        raise SystemExit(f"migrate: {src} has no mandates/ — not a .research-state facility")
    p = plan(src, dst, a.today)
    c = {k: len(v) for k, v in p["records"].items()}
    n = p["notes"]
    print(f".research-state {src} → {dst}")
    print(f"  {c['MND']} mandate(s), {c['STEP']} step(s), {c['FND']} finding(s), {c['CHL']} challenge(s), {c['CND']} candidate(s) to write; {len(p['skipped'])} already migrated")
    print(f"  ids: " + ", ".join(f"{o}→{v}" for o, v in list(p["idmap"].items())[:6]) + (" …" if len(p["idmap"]) > 6 else ""))
    print(f"  answers inferred from the claim's words for {n['answers_inferred']} finding(s); {len(n['answers_unmatched'])} matched no question (set to Q1, flagged)")
    print(f"  {len(n['scores_unlinked'])} candidate score(s) cite sources no finding carries — kept as sources:, to re-link with /research-longlist")
    print(f"  {len(n['rulings_migrated'])} ruled challenge(s) will name the migrating person as resolved_by (the old ruling kept in resolution)")
    print(f"  {len(p['events'])} activity event(s) renamed to research.*; {len(p['copies'])} file(s) copied; {len(p['sources'])} source(s) registered")
    print("  history lost to in-place edits in the old facility cannot be recovered; no supersession chain is invented")
    print(f"  manifest: {'capabilities.research present — left as is' if p['block_present'] else 'capabilities.research will be added'}")
    for e in p["errors"]:
        print(f"  UNREADABLE  {e}")
    if not a.write:
        print("  plan only: re-run with --write --actor <email>")
        return 0
    if not a.actor:
        raise SystemExit("migrate: --write needs --actor <email> (who the activity log says did this)")
    if p["errors"]:
        raise SystemExit(f"migrate: {len(p['errors'])} record(s) are unreadable — fix them in the old facility first; a migration never drops a record silently")
    k = write(p, a.actor)
    print(f"  written; {k} line(s) appended to logs/activity.ndjson. Next: validator/scripts/check.py, then /research-redteam and /research-walk plan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
