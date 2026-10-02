#!/usr/bin/env python3
"""walk — the deterministic half of research-walk, the unattended producer (capabilities/research/README.md).

    python3 walk.py <facility> plan [--as-of YYYY-MM-DD] [--json]         what this run would do, each action auto or gate
    python3 walk.py <facility> open [--host NAME] [--json]                the marker to hold (refuses while one is live)
    python3 walk.py <facility> landed --since <ISO time> [--json]         what landed since the run opened (rule 3)
    python3 walk.py <facility> fingerprint RES-M-NNN                      the mandate's fingerprint (rule 1)

The walk works one run inside a budget; it never schedules and never writes the digest. This script decides
nothing a person must decide: it classifies every candidate action `auto` (the walk may do it) or `gate` (it is
parked for a person, and reaches them through routine.yaml's research.walk-gated). It reads only; the skill
writes the marker, the run record and everything the auto actions produce, through project-state.

Classification (spec §6.10):
  auto  drain the inbox · start a locked mandate by methodology_type · the next methodology step · re-plan a
        standing mandate against stale or reopened questions · work an open challenge by gathering evidence ·
        file the mechanical objections · raise the primary share · compose a draft · run the retrospective
  gate  lock or kill a draft · reopen or close-negative after `walk.barren_run` barren steps with questions open ·
        mark a mandate complete · rule on a challenge · review a material supersession · confirm new candidates ·
        anything outbound
The three normative rules:
  1  memory outlives the run — an auto action already attempted in an earlier run, against a mandate whose
     fingerprint has not moved since, is reclassified gate, naming that run;
  2  a named unread source is research, not judgement — an open challenge whose argument names a page no finding
     cites is worked (fetched) before it is parked for a ruling;
  3  show work in flight — `landed` lists what was written since the run opened.
The walk halts outright, planning nothing, when validator/scripts/check.py reports errors.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import socket
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAP = HERE.parent
sys.path.insert(0, str(CAP / "views"))
sys.path.insert(0, str(CAP / "validator" / "scripts"))
sys.path.insert(0, str(HERE))
from _research import Facility, host, to_date  # noqa: E402
import check as checker  # noqa: E402
import redteam  # noqa: E402

ROUTE = {"narrative": ("research-step", "run methodology step {n}"), "longlist": ("research-longlist", "discover candidates"),
         "comparative": ("research-step", "compare, dimension by dimension"), "deep-web-investigation": ("research-deepweb", "plan the investigation")}
URL = re.compile(r"https?://[^\s)\]\"'>,]+|\b(?:[a-z0-9-]+\.)+(?:example|com|org|net|ca|gov|edu|io|co|uk|eu)(?:/[^\s)\]\"'>,]*)?", re.I)


def fingerprint(fx: Facility, mid: str) -> str:
    m = fx.mandate.get(mid) or {}
    body = {"status": m.get("status"), "iteration": m.get("iteration"),
            "questions": [(q.get("id"), q.get("state"), sorted(q.get("answered_by") or [])) for q in m.get("questions") or []],
            "findings": sorted((f["id"], f.get("status")) for f in fx.findings if f.get("mandate_id") == mid),
            "steps": sorted((s["id"], s.get("status")) for s in fx.steps if s.get("mandate_id") == mid),
            "challenges": sorted((c["id"], c.get("status"), bool(c.get("proposed_resolution"))) for c in fx.challenges if c.get("mandate_id") == mid),
            "changes": sorted(x["id"] for x in fx.changes if x.get("mandate_id") == mid)}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


def cited_refs(fx: Facility) -> set:
    refs = set()
    for f in fx.findings:
        for e in f.get("evidence") or []:
            if isinstance(e, dict) and e.get("ref"):
                refs.add(str(e["ref"]).rstrip("/"))
                refs.add(host(str(e["ref"])))
    return refs


def barren_streak(fx: Facility, mid: str) -> int:
    done = sorted((s for s in fx.steps if s.get("mandate_id") == mid and s.get("status") == "complete"), key=lambda s: str(s.get("completed_at") or s.get("started_at")))
    n = 0
    for s in reversed(done):
        if s.get("findings_produced"):
            break
        n += 1
    return n


def plan(fx: Facility) -> dict:
    res = checker.check(fx, history=False)
    if not res["ok"]:
        return {"status": "halted", "why": f"the facility does not validate ({res['errors']} error(s)) — the walk refuses to work on it",
                "problems": [p for p in res["problems"] if p["level"] == "error"][:20], "actions": [], "gates": []}
    walk_cfg = fx.cap.get("walk") or {}
    barren_run = int(walk_cfg.get("barren_run") or 3)
    max_actions = int(walk_cfg.get("max_actions") or 40)
    acts = []

    def add(mid, action, skill, cls, reason, target=None, args=None):
        acts.append({"mandate_id": mid, "action": action, "skill": skill, "class": cls, "reason": reason, "target": target, "args": args or {},
                     "fingerprint": fingerprint(fx, mid) if mid else None})

    inbox = fx.fac / "documents" / "inbox"
    waiting = [p.name for p in sorted(inbox.iterdir()) if p.is_file() and not p.name.startswith(".")] if inbox.is_dir() else []
    if waiting:
        add(None, "drain-inbox", "research-ingest", "auto", f"{len(waiting)} document(s) in documents/inbox/", args={"files": waiting[:20]})
    cited = cited_refs(fx)
    last_brief = str(fx.state.get("last_brief") or "")
    retro_done = {e.get("id") or e.get("ref") for e in fx.events if e.get("event") == "research.retro.recorded"}
    for m in fx.mandates:
        mid, st = m["id"], m.get("status")
        if st == "draft":
            fails = checker.lock_failures(fx, m)
            add(mid, "lock-or-kill", "research-mandate", "gate",
                ("Drift: a draft at iteration " + str(m.get("iteration")) + ". " if int(m.get("iteration") or 1) >= 2 else "") +
                ("Lock checklist: " + "; ".join(t for _, t in fails) if fails else "It passes the lock checklist; locking is a person's decision."))
            continue
        if st == "locked":
            skill, what = ROUTE.get(m.get("methodology_type"), ("research-step", "run methodology step {n}"))
            add(mid, "start", skill, "auto", f"locked, no work yet: {what.format(n=1)}", args={"methodology_type": m.get("methodology_type")})
            continue
        if st in ("complete", "closed-negative"):
            if mid not in retro_done:
                add(mid, "retro", "research-retro", "auto", f"{st} with no retrospective recorded")
            continue
        if st not in ("in-progress", "standing"):
            continue
        open_ch = [c for c in fx.challenges if c.get("mandate_id") == mid and c.get("status") == "open"]
        for c in open_ch:
            named = [u.rstrip(".") for u in URL.findall(str(c.get("argument") or ""))]
            # a page with a path is read only if that page is cited; a bare domain is read if anything on it is cited
            unread = [u for u in named if (u.rstrip("/") not in cited) if ("/" in u.split("://")[-1].strip("/") or host(u if u.startswith("http") else "https://" + u) not in cited)]
            if unread:
                add(mid, "fetch-named-source", "research-step", "auto", f"{c['id']} names a page no finding cites: {', '.join(unread)} — read it before anyone rules",
                    target=c["id"], args={"mode": "validate", "urls": unread, "challenge": c["id"]})
            elif not c.get("proposed_resolution"):
                add(mid, "work-challenge", "research-step", "auto", f"{c['id']} ({c.get('severity')}, {c.get('kind')}): gather the evidence that would settle it",
                    target=c["id"], args={"mode": "validate", "challenge": c["id"]})
            if c.get("severity") == "blocking" or c.get("proposed_resolution"):
                add(mid, "rule-on-challenge", "research-redteam", "gate",
                    f"{c['id']} is {c.get('severity')}; only a person rules" + (f" — the walk proposes: {c['proposed_resolution']}" if c.get("proposed_resolution") else ""), target=c["id"])
        props = redteam.attacks(fx, [f for f in fx.findings if f.get("mandate_id") == mid])
        if props:
            add(mid, "file-objections", "research-redteam", "auto", f"{len(props)} mechanical objection(s) to judge and file", args={"proposals": [p["finding_id"] + ":" + p["kind"] for p in props]})
        share, thr, verdict = fx.gate(m)
        if verdict == "below":
            add(mid, "raise-primary-share", "research-step", "auto", f"primary share {round(100 * share)}% below the {round(100 * thr)}% gate — find primary sources for the secondary findings", args={"mode": "validate"})
        qstate = {q.get("id"): fx.question_state(m, q) for q in m.get("questions") or []}
        open_q = [q for q, s in qstate.items() if s in ("open", "reopened", "stale")]
        streak = barren_streak(fx, mid)
        if open_q and streak >= barren_run:
            add(mid, "reopen-or-close-negative", "research-mandate", "gate", f"{streak} barren step(s) in a row with {', '.join(open_q)} still open: reopen with a new method, or close negative with a null-result statement")
        elif st == "standing":
            stale = [q for q, s in qstate.items() if s in ("stale", "reopened")]
            if stale:
                add(mid, "replan-standing", "research-step", "auto", f"{', '.join(stale)} rest on stale evidence — re-plan the night against them", args={"questions": stale})
            for x in fx.changes:
                if x.get("mandate_id") == mid and x.get("significance") == "material" and str(x.get("detected_at")) > last_brief[:10]:
                    add(mid, "review-material-change", "research-brief", "gate", f"material supersession {x['id']} ({', '.join(x.get('before') or [])} → {', '.join(x.get('after') or [])}) before it enters the delta", target=x["id"])
        else:
            done_steps = {s.get("methodology_step") for s in fx.steps if s.get("mandate_id") == mid and s.get("status") == "complete"}
            nxt = [s for s in m.get("methodology") or [] if isinstance(s, dict) and s.get("step") not in done_steps]
            if open_q and nxt:
                skill = ROUTE.get(m.get("methodology_type"), ("research-step", ""))[0]
                add(mid, "next-step", skill, "auto", f"methodology step {nxt[0]['step']}: {nxt[0].get('description')}", target=f"step-{nxt[0]['step']}", args={"methodology_step": nxt[0]["step"], "questions": open_q})
            blocking = fx.open_blocking(mid)
            if not open_q and verdict == "pass" and not blocking:
                drafted = [r for r in fx.reports if r.startswith(mid)]
                if drafted:
                    add(mid, "mark-complete", "research-mandate", "gate", f"every question answered, the gate passes and a draft exists ({drafted[-1]}): marking complete is a person's decision")
                else:
                    add(mid, "compose-draft", "research-brief", "auto", "every question answered, the gate passes, no blocking challenge: compose the draft (shipping it stays gated)")
        new_cands = [c for c in fx.candidates if c.get("mandate_id") == mid and c.get("status") == "discovered" and c.get("discovered_via") not in (None, "operator")]
        if new_cands:
            add(mid, "confirm-candidates", "research-longlist", "gate", f"{len(new_cands)} candidate(s) the research discovered: a person confirms what joins the longlist", args={"candidates": [c["id"] for c in new_cands]})

    # rule 1 — memory outlives the run
    for a in acts:
        if a["class"] != "auto" or not a["mandate_id"]:
            continue
        for run in reversed(fx.runs):
            for prev in run.get("actions") or []:
                if prev.get("mandate_id") == a["mandate_id"] and prev.get("action") == a["action"] and prev.get("target") == a["target"] \
                        and prev.get("fingerprint") and prev.get("fingerprint") == a["fingerprint"]:
                    a["class"] = "gate"
                    a["reason"] = f"already tried in {run.get('run_id')} ({prev.get('outcome', '?')}) against a project that has not moved since — a person decides what to try instead. Was: {a['reason']}"
                    break
            if a["class"] == "gate":
                break
    autos = [a for a in acts if a["class"] == "auto"]
    return {"status": "ready", "max_actions": max_actions, "budget_seconds": int(walk_cfg.get("budget_seconds") or 14400),
            "actions": autos[:max_actions], "deferred": autos[max_actions:], "gates": [a for a in acts if a["class"] == "gate"]}


def open_marker(fx: Facility, host_name: str) -> dict:
    act = (fx.state.get("walk") or {}).get("active")
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    if isinstance(act, dict) and str(act.get("expires_at") or "") > now.strftime("%Y-%m-%dT%H:%M:%SZ"):
        return {"refused": f"walk {act.get('run_id')} holds the marker until {act.get('expires_at')} on {act.get('host')}"}
    day = now.strftime("%Y-%m-%d")
    n = 1 + sum(1 for r in fx.runs if str(r.get("run_id", "")).startswith(f"RUN-{day}-"))
    budget = int((fx.cap.get("walk") or {}).get("budget_seconds") or 14400)
    return {"run_id": f"RUN-{day}-{n}", "started": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": (now + dt.timedelta(seconds=budget + 600)).strftime("%Y-%m-%dT%H:%M:%SZ"), "host": host_name,
            "previous_expired": act if isinstance(act, dict) else None}


def landed(fx: Facility, since: str) -> dict:
    rows = []
    for kind, recs, stamp in (("finding", fx.findings, "created"), ("step", fx.steps, "started_at"), ("challenge", fx.challenges, "created"),
                              ("change", fx.changes, "detected_at"), ("candidate", fx.candidates, "created")):
        for r in recs:
            if str(r.get(stamp) or "") >= since:
                rows.append({"kind": kind, "id": r["id"], "mandate_id": r.get("mandate_id"), "at": str(r.get(stamp)), "status": r.get("status")})
    return {"since": since, "landed": sorted(rows, key=lambda r: r["at"])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    ap.add_argument("verb", choices=["plan", "open", "landed", "fingerprint"])
    ap.add_argument("mandate", nargs="?")
    ap.add_argument("--as-of")
    ap.add_argument("--since")
    ap.add_argument("--host", default=socket.gethostname())
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    fac = Path(a.facility)
    fx = Facility(fac if (fac / "manifest.yaml").exists() else fac / "project-state", to_date(a.as_of) or dt.date.today())
    if a.verb == "fingerprint":
        if a.mandate not in fx.mandate:
            print(f"walk: no mandate {a.mandate}", file=sys.stderr)
            return 2
        print(fingerprint(fx, a.mandate))
        return 0
    if a.verb == "open":
        out = open_marker(fx, a.host)
        print(json.dumps(out, indent=1) if a.json or "refused" not in out else f"walk: {out['refused']}")
        return 1 if "refused" in out else 0
    if a.verb == "landed":
        if not a.since:
            ap.error("landed needs --since")
        out = landed(fx, a.since)
        if a.json:
            print(json.dumps(out, indent=1))
        else:
            print(f"{len(out['landed'])} record(s) since {a.since}")
            for r in out["landed"]:
                print(f"  {r['at']}  {r['kind']:<9} {r['id']}  {r['mandate_id'] or ''}  {r['status'] or ''}")
        return 0
    out = plan(fx)
    if a.json:
        print(json.dumps(out, indent=1))
        return 0 if out["status"] == "ready" else 1
    if out["status"] == "halted":
        print(f"walk halted: {out['why']}")
        for p in out["problems"]:
            print(f"  ✗ {p['where']}: {p['message']}")
        return 1
    print(f"walk plan · {len(out['actions'])} auto action(s) (max {out['max_actions']}) · {len(out['gates'])} gate(s)")
    for x in out["actions"]:
        print(f"  auto  {x['mandate_id'] or '—':<9} {x['action']:<22} {x['skill']:<18} {x['reason']}")
    for x in out["gates"]:
        print(f"  GATE  {x['mandate_id'] or '—':<9} {x['action']:<22} {x['skill']:<18} {x['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
