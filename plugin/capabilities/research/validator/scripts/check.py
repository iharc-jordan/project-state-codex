#!/usr/bin/env python3
"""check — the research capability's executable validator (capabilities/research/README.md).

    python3 check.py <facility> [--json] [--strict] [--no-history]      the whole research namespace
    python3 check.py <facility> --lock RES-M-NNN [--json]               the lock checklist for one mandate
    python3 check.py <facility> --gate RES-M-NNN [--json]               the evidence gate research-brief enforces

Composed with the core validator under validator/validate-research.md; fails only records in the
`research` namespace. Exit 0 clean, 1 errors (or, with --strict, warnings), 2 no facility.

What the whole check covers (spec §7):
  schema          required fields and enums per schema/entities.yaml; the file name is the id
  counters        state/research.json counters are not behind the ids on disk
  references      step → mandate; finding → mandate, step, the mandate's question ids; challenge → finding;
                  change → mandate and findings; candidate scores → findings
  lock            the lock checklist for every mandate at locked or later
  closed-negative requires null_result_statement
  append-only     findings, challenges and changes unchanged since they were first committed, but for their
                  lifecycle fields (needs git; --no-history skips)
  supersession    scoped: same mandate, a shared question (or candidate), same category; no cycles
  independence    independent_sources ≤ the evidence it counts; no self-corroboration; an established
                  material finding has an independent origin or a person's confirmation
  excerpts        on every evidence item of a material primary or secondary finding
  challenges      only a person rules (research.challenge.ruled by an actor that is not a skill)
  evidence gate   warned per mandate (research-brief refuses on it — --gate)
  walk            an expired walk marker; version drift of the manifest block
  library         every citation in a study (research/reports/RES-M-*.md) or article (research/topics/*.md)
                  resolves; a study cites only its own mandate's findings
Reads only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAP = HERE.parent.parent
sys.path.insert(0, str(CAP / "views"))
from _research import Facility, to_date, yload  # noqa: E402

SCHEMA = yload(CAP / "schema" / "entities.yaml") or {}
KINDS = SCHEMA.get("kinds") or {}
DIRS = {"research-mandate": "mandates", "research-step": "steps", "research-finding": "findings", "research-challenge": "challenges",
        "research-candidate": "candidates", "research-change": "changes"}
COUNTER = {"research-mandate": "mandate", "research-step": "step", "research-finding": "finding", "research-challenge": "challenge",
           "research-candidate": "candidate", "research-change": "change"}
ID_RE = {k: re.compile("^" + v["id_format"].replace("NNN", r"\d{3,}") + "$") for k, v in KINDS.items()}
LOCKED_OR_LATER = {"locked", "in-progress", "standing", "complete", "closed-negative"}
PLUGIN_VERSION = (yload(CAP / "plugin.yaml") or {}).get("plugin", {}).get("version")


class Problems:
    def __init__(self):
        self.items = []

    def error(self, where, code, msg):
        self.items.append({"level": "error", "where": where, "code": code, "message": msg})

    def warn(self, where, code, msg):
        self.items.append({"level": "warning", "where": where, "code": code, "message": msg})

    @property
    def errors(self):
        return [p for p in self.items if p["level"] == "error"]

    @property
    def warnings(self):
        return [p for p in self.items if p["level"] == "warning"]


def get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def registered(fx: Facility, ref: str) -> bool:
    """A document the curator knows: on disk, or named in documents/index.yaml or documents/ingested.yaml."""
    if (fx.fac / ref).exists():
        return True
    for name in ("index.yaml", "ingested.yaml"):
        idx = yload(fx.fac / "documents" / name) or {}
        rows = (idx.get("docs") or idx.get("documents") or []) if isinstance(idx, dict) else (idx if isinstance(idx, list) else [])
        for row in rows:
            if isinstance(row, dict) and ref in [str(v) for v in row.values() if isinstance(v, str)]:
                return True
    return False


# ── the lock checklist (spec §7) ─────────────────────────────────────────────
def lock_failures(fx: Facility, m: dict) -> list[tuple[str, str]]:
    """Every reason this mandate cannot lock, as (code, message). Empty means it may lock."""
    out = []
    qs = [q for q in (m.get("questions") or []) if isinstance(q, dict) and str(q.get("text") or "").strip()]
    if not qs:
        out.append(("lock.questions", "no questions: a mandate commits to at least one"))
    steps = [s for s in (m.get("methodology") or []) if isinstance(s, dict) and len(str(s.get("description") or "").strip()) >= 10]
    if len(steps) < 3:
        out.append(("lock.methodology", f"{len(steps)} concrete methodology step(s); locking needs at least 3"))
    d = m.get("deliverable") or {}
    missing = [k for k in ("format", "structure", "audience") if not d.get(k)]
    if missing:
        out.append(("lock.deliverable", f"the deliverable has no {', '.join(missing)}"))
    if not [c for c in (m.get("success_criteria") or []) if str(c).strip()]:
        out.append(("lock.success-criteria", "no success criteria: nothing says when the questions are answered"))
    if not m.get("corpus_independent"):
        linked = [s for s in (m.get("source_relevance") or []) if isinstance(s, dict) and (s.get("score") or 0) >= 2
                  and str(s.get("ref", "")).startswith("documents/") and registered(fx, str(s["ref"]))]
        if not linked:
            out.append(("lock.corpus", "no registered document scored ≥ 2 in source_relevance, and corpus_independent is not true"))
    mt = m.get("methodology_type")
    if mt == "longlist":
        crit = m.get("longlist_criteria") or []
        if not crit:
            out.append(("lock.longlist", "a longlist mandate needs longlist_criteria"))
        else:
            total = sum(float(c.get("weight") or 0) for c in crit if isinstance(c, dict))
            if abs(total - 1.0) > 0.001:
                out.append(("lock.weights", f"longlist_criteria weights sum to {round(total, 4)}, not 1.0"))
            unnamed = [c for c in crit if not (isinstance(c, dict) and c.get("id") and c.get("rubric"))]
            if unnamed:
                out.append(("lock.longlist", f"{len(unnamed)} criterion(s) without an id or a rubric"))
    if mt == "comparative":
        if len(m.get("comparison_subjects") or []) < 2:
            out.append(("lock.comparative", "a comparative mandate needs at least two comparison_subjects"))
        dims = m.get("comparative_dimensions") or []
        if not dims or any(not (isinstance(x, dict) and x.get("id") and x.get("type")) for x in dims):
            out.append(("lock.comparative", "every comparative dimension needs an id and a type"))
    return out


# ── the evidence gate (spec §4.4, §6.8) ──────────────────────────────────────
def gate_report(fx: Facility, m: dict) -> dict:
    share, thr, verdict = fx.gate(m)
    fs = [f for f in fx.findings_for(m["id"]) if fx.live(f)]
    blocking = fx.open_blocking(m["id"])
    return {"mandate": m["id"], "primary_share": None if share is None else round(share, 3), "threshold": thr, "verdict": verdict,
            "established": sum(1 for f in fs if f.get("status") == "established"), "provisional": sum(1 for f in fs if f.get("status") == "provisional"),
            "provisional_material": [f["id"] for f in fs if f.get("status") == "provisional" and f.get("material")],
            "blocking_challenges": [c["id"] for c in blocking],
            "open_challenges": [c["id"] for c in fx.challenges if c.get("mandate_id") == m["id"] and c.get("status") == "open"],
            "ship": verdict == "pass" and not blocking}


# ── history, for the append-only rule ────────────────────────────────────────
class History:
    """The first committed version of a file, when the facility lives in git."""

    def __init__(self, fac: Path, enabled: bool):
        self.top = None
        if enabled:
            r = subprocess.run(["git", "-C", str(fac), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
            if r.returncode == 0:
                self.top = Path(r.stdout.strip())

    def first(self, path: Path):
        if not self.top:
            return None
        rel = path.resolve().relative_to(self.top.resolve()).as_posix()
        log = subprocess.run(["git", "-C", str(self.top), "log", "--diff-filter=A", "--format=%H", "--", rel], capture_output=True, text=True).stdout.split()
        if not log:
            return None
        blob = subprocess.run(["git", "-C", str(self.top), "show", f"{log[-1]}:{rel}"], capture_output=True, text=True)
        if blob.returncode != 0:
            return None
        try:
            import yaml
            return yaml.safe_load(blob.stdout)
        except Exception:
            return None


def chain(fx: Facility, fid: str) -> set:
    """Every finding in fid's supersession chain, both directions."""
    seen, todo = set(), [fid]
    back = {f["id"]: f.get("supersedes") for f in fx.findings}
    while todo:
        x = todo.pop()
        if x in seen or x is None:
            continue
        seen.add(x)
        todo.append(back.get(x))
        todo.append(fx.superseded_by.get(x))
    return seen


def refs_of(f):
    return {str(e.get("ref")) for e in (f.get("evidence") or []) if isinstance(e, dict) and e.get("ref")}


def check(fx: Facility, strict: bool = False, history: bool = True) -> dict:
    P = Problems()
    R = fx.fac / "research"
    if not fx.cap:
        P.error("manifest.yaml", "enable", "capabilities.research is not in the manifest — the capability is not enabled here")
    elif fx.cap.get("enabled") is False:
        P.warn("manifest.yaml", "enable", "capabilities.research.enabled is false")
    if fx.cap.get("version") and PLUGIN_VERSION and str(fx.cap["version"]) != str(PLUGIN_VERSION):
        P.warn("manifest.yaml", "version.drift", f"enabled at {fx.cap['version']}, installed {PLUGIN_VERSION}")

    # ── schema, ids, counters ────────────────────────────────────────────────
    records = {}
    for kind, sub in DIRS.items():
        spec = KINDS.get(kind) or {}
        d = R / sub
        highest = 0
        for p in sorted(d.glob("*.yaml")) if d.is_dir() else []:
            doc = yload(p)
            rel = p.relative_to(fx.fac).as_posix()
            if not isinstance(doc, dict):
                P.error(rel, "yaml", "not a YAML mapping")
                continue
            doc["_path"] = p
            if doc.get("id") != p.stem:
                P.error(rel, "id.filename", f"id {doc.get('id')!r} does not match the file name")
            if not ID_RE[kind].match(str(doc.get("id"))):
                P.error(rel, "id.format", f"id {doc.get('id')!r} is not {spec.get('id_format')}")
            else:
                highest = max(highest, int(str(doc["id"]).rsplit("-", 1)[1]))
            for field in spec.get("required") or []:
                v = doc.get(field)
                if v is None or v == "" or (field in ("questions", "methodology", "evidence") and not v):
                    P.error(rel, "required", f"missing {field}")
            for field, allowed in (spec.get("enums") or {}).items():
                if not isinstance(allowed, list):
                    continue
                if field.endswith("[].state"):
                    for q in doc.get(field.split("[]")[0]) or []:
                        if isinstance(q, dict) and q.get("state") not in allowed:
                            P.error(rel, "enum", f"question {q.get('id')} state {q.get('state')!r} is not one of {allowed}")
                    continue
                v = get(doc, field)
                if v is not None and v not in allowed:
                    P.error(rel, "enum", f"{field} {v!r} is not one of {allowed}")
            records.setdefault(kind, []).append(doc)
        counter = int((fx.state.get("counters") or {}).get(COUNTER[kind], 0))
        if highest > counter:
            P.error("state/research.json", "counter", f"counters.{COUNTER[kind]} is {counter}, behind {highest} on disk — the next id would collide")

    mandates = {m["id"]: m for m in records.get("research-mandate", [])}
    steps = {s["id"]: s for s in records.get("research-step", [])}
    findings = {f["id"]: f for f in records.get("research-finding", [])}
    rel = lambda d: d["_path"].relative_to(fx.fac).as_posix()  # noqa: E731

    # ── mandates: lifecycle and the lock checklist ───────────────────────────
    for m in mandates.values():
        if m.get("status") in LOCKED_OR_LATER:
            for code, msg in lock_failures(fx, m):
                P.error(rel(m), code, f"{m['status']} but fails the lock checklist: {msg}")
        if m.get("status") == "closed-negative" and not str(m.get("null_result_statement") or "").strip():
            P.error(rel(m), "closed-negative", "closed-negative requires null_result_statement — what was searched, over what period, what was not found")
        if m.get("status") == "standing" and not (m.get("standing") or {}).get("cadence"):
            P.error(rel(m), "standing", "a standing mandate names its cadence (standing.cadence)")
        qids = [q.get("id") for q in m.get("questions") or [] if isinstance(q, dict)]
        if len(qids) != len(set(qids)):
            P.error(rel(m), "questions", "question ids repeat")
        for q in m.get("questions") or []:
            for fid in q.get("answered_by") or []:
                f = findings.get(fid)
                if not f:
                    P.error(rel(m), "ref.answered_by", f"{q.get('id')} is answered by {fid}, which does not exist")
                elif f.get("mandate_id") != m["id"] or q.get("id") not in (f.get("answers") or []):
                    P.error(rel(m), "ref.answered_by", f"{fid} does not answer {m['id']} {q.get('id')}")

    # ── steps ────────────────────────────────────────────────────────────────
    for s in steps.values():
        if s.get("mandate_id") not in mandates:
            P.error(rel(s), "ref.mandate", f"mandate {s.get('mandate_id')} does not exist")
        for fid in s.get("findings_produced") or []:
            if fid not in findings:
                P.error(rel(s), "ref.finding", f"findings_produced names {fid}, which does not exist")
        if s.get("status") == "complete" and not s.get("completed_at"):
            P.warn(rel(s), "step.complete", "complete without completed_at")

    # ── findings ─────────────────────────────────────────────────────────────
    events = fx.events
    ref = lambda e: e.get("id") or e.get("ref")  # noqa: E731 — the house log writes `id`; older research lines wrote `ref`
    person_established = {ref(e) for e in events if e.get("event") == "research.finding.established" and not str(e.get("actor", "")).startswith("research-")}
    for f in findings.values():
        r = rel(f)
        m = mandates.get(f.get("mandate_id"))
        if not m:
            P.error(r, "ref.mandate", f"mandate {f.get('mandate_id')} does not exist")
        else:
            qids = {q.get("id") for q in m.get("questions") or [] if isinstance(q, dict)}
            off = [a for a in f.get("answers") or [] if a not in qids]
            if off:
                P.error(r, "ref.answers", f"answers {off}, not questions of {m['id']}")
        if f.get("step_id") not in steps:
            P.error(r, "ref.step", f"step {f.get('step_id')} does not exist")
        elif steps[f["step_id"]].get("mandate_id") != f.get("mandate_id"):
            P.error(r, "ref.step", f"step {f['step_id']} belongs to another mandate")
        ev = [e for e in f.get("evidence") or [] if isinstance(e, dict)]
        n = f.get("independent_sources")
        if not isinstance(n, int) or n < 0:
            P.error(r, "independence", "independent_sources must be a whole number")
        elif n > len(ev):
            P.error(r, "independence", f"independent_sources is {n} but there are {len(ev)} evidence items")
        if (f.get("source_tier") == "speculative") != (f.get("confidence") == "speculative"):
            P.error(r, "tier.speculative", "a speculative source tier and speculative confidence go together")
        if f.get("material") and f.get("source_tier") in ("primary", "secondary") and f.get("epistemic_status") != "unknown":
            bare = [i for i, e in enumerate(ev) if not str(e.get("excerpt") or "").strip()]
            if bare:
                msg = f"a material {f['source_tier']} finding needs an excerpt on every evidence item (missing on #{', #'.join(str(i + 1) for i in bare)})"
                if f.get("migrated_from"):   # inherited from the old facility, not introduced here: reported, never blocking
                    P.warn(r, "excerpt.inherited", msg + " — inherited from the migrated facility; add one with research-step validate")
                else:
                    P.error(r, "excerpt", msg)
        for key in ("supersedes",):
            t = f.get(key)
            if t:
                old = findings.get(t)
                if not old:
                    P.error(r, "supersession", f"supersedes {t}, which does not exist")
                else:
                    same_q = set(f.get("answers") or []) & set(old.get("answers") or [])
                    if old.get("mandate_id") != f.get("mandate_id"):
                        P.error(r, "supersession.scope", f"supersedes {t} from another mandate — supersession is scoped to one mandate")
                    elif not same_q:
                        P.error(r, "supersession.scope", f"supersedes {t}, which answers none of the same questions")
                    elif old.get("category") != f.get("category"):
                        P.error(r, "supersession.scope", f"supersedes {t} across categories ({old.get('category')} → {f.get('category')})")
                    if str(old.get("created") or "") > str(f.get("created") or ""):
                        P.error(r, "supersession.order", f"supersedes {t}, which is newer")
        for key in ("contradicts", "supports"):
            for t in f.get(key) or []:
                if t not in findings:
                    P.error(r, f"ref.{key}", f"{key} {t}, which does not exist")
        ch = chain(fx, f["id"])
        own = [t for t in f.get("supports") or [] if t in ch]
        if own:
            P.error(r, "self-corroboration", f"supports {own}: a finding never corroborates itself or its own supersession chain")
        if f.get("status") == "established" and f.get("material"):
            basis = False
            if isinstance(n, int) and n >= 2 and not f.get("derives_from"):
                basis = True
            for g in findings.values():
                if f["id"] in (g.get("supports") or []) and g["id"] not in ch and fx.live(g) \
                        and not (refs_of(g) & refs_of(f)) and not (set(g.get("derives_from") or []) & (refs_of(f) | set(f.get("derives_from") or []))):
                    basis = True
            if f["id"] in person_established:
                basis = True
            if f.get("migrated_from"):   # spec §11.2: migrated findings arrive established; the old facility accepted them
                basis = True
            if not basis:
                P.error(r, "established.basis", "established with one origin: needs an independent source that agrees, a corroborating finding from another origin, or a person's confirmation (research.finding.established)")
    # supersession cycles
    for f in findings.values():
        seen, x = set(), f["id"]
        while x:
            if x in seen:
                P.error(rel(f), "supersession.cycle", f"the supersession chain from {f['id']} loops")
                break
            seen.add(x)
            x = (findings.get(x) or {}).get("supersedes")

    # ── challenges, changes, candidates ──────────────────────────────────────
    ruled = {}
    for e in events:
        if e.get("event") == "research.challenge.ruled":
            ruled.setdefault(ref(e), []).append(e)
    for c in records.get("research-challenge", []):
        r = rel(c)
        if c.get("finding_id") not in findings:
            P.error(r, "ref.finding", f"against {c.get('finding_id')}, which does not exist")
        if c.get("mandate_id") not in mandates:
            P.error(r, "ref.mandate", f"mandate {c.get('mandate_id')} does not exist")
        if c.get("status") in ("accepted", "rejected", "resolved"):
            if not c.get("resolved_by"):
                P.error(r, "ruling", f"{c['status']} with no resolved_by — a ruling names the person who made it")
            elif str(c.get("resolved_by")).startswith("research-"):
                P.error(r, "ruling", f"ruled by {c['resolved_by']} — only a person rules on a challenge; the walk proposes")
            if c.get("status") == "rejected" and not str(c.get("resolution") or "").strip():
                P.error(r, "ruling", "rejected with no reason — rejecting is a recorded ruling")
            for e in ruled.get(c["id"], []):
                if str(e.get("actor", "")).startswith("research-"):
                    P.error(r, "ruling", f"the log shows {e.get('actor')} ruling on it")
    for x in records.get("research-change", []):
        r = rel(x)
        if x.get("mandate_id") not in mandates:
            P.error(r, "ref.mandate", f"mandate {x.get('mandate_id')} does not exist")
        for t in (x.get("before") or []) + (x.get("after") or []):
            if t not in findings:
                P.error(r, "ref.finding", f"names {t}, which does not exist")
        for new in x.get("after") or []:
            for old in x.get("before") or []:
                if new in findings and findings[new].get("supersedes") != old and old in findings:
                    P.warn(r, "change.delta", f"{new} does not supersede {old} — a change records a supersession")
    for c in records.get("research-candidate", []):
        r = rel(c)
        m = mandates.get(c.get("mandate_id"))
        if not m:
            P.error(r, "ref.mandate", f"mandate {c.get('mandate_id')} does not exist")
            continue
        crit = {x.get("id"): float(x.get("weight") or 0) for x in m.get("longlist_criteria") or [] if isinstance(x, dict)}
        for s in c.get("scores") or []:
            if crit and s.get("criterion") not in crit:
                P.error(r, "score.criterion", f"scored on {s.get('criterion')!r}, not a criterion of {m['id']}")
            if not s.get("finding_ids"):
                if c.get("migrated_from"):
                    P.warn(r, "score.relink", f"the {s.get('criterion')} score (migrated) " + ("cites sources no finding carries" if s.get("sources") else "cited no source in the old facility") + " — re-link or re-score it with research-longlist")
                else:
                    P.error(r, "score.evidence", f"the {s.get('criterion')} score cites no finding")
            for fid in s.get("finding_ids") or []:
                if fid not in findings:
                    P.error(r, "score.evidence", f"cites {fid}, which does not exist")

    # ── append-only against history ──────────────────────────────────────────
    H = History(fx.fac, history)
    if history and not H.top:
        P.warn("research/", "history", "not in a git repository: the append-only rule is enforced on write by the server, not re-checked here")
    for kind in ("research-finding", "research-challenge", "research-change"):
        life = set(KINDS[kind].get("lifecycle_fields") or []) | {"_path"}
        for doc in records.get(kind, []):
            first = H.first(doc["_path"])
            if not isinstance(first, dict):
                continue
            moved = sorted(k for k in set(first) | set(doc) if k not in life and first.get(k) != doc.get(k))
            if moved:
                P.error(rel(doc), "append-only", f"changed after it was first committed: {', '.join(moved)} — write a new record that supersedes it")

    # ── the library: every citation in a study or article resolves ───────────
    # A document citing a since-superseded finding is not invalid — it is due for re-issue (routine.yaml
    # research.library-moved); one citing a finding that does not exist, or a study citing another mandate's
    # finding, is a broken reference.
    from _research import library  # noqa: E402
    lib = library(fx)
    for d in lib["studies"] + lib["articles"]:
        for c in d["citations"]:
            if c["state"] == "missing":
                P.error(d["path"], "ref.citation", f"cites {c['id']}, which does not exist")
            elif d["kind"] == "study" and c.get("mandate") != d["mandate"]:
                P.error(d["path"], "ref.citation", f"cites {c['id']}, which belongs to {c.get('mandate')} — a study cites its own mandate's findings; an article compiles across mandates")
        if not d["citations"]:
            P.warn(d["path"], "citation.none", "cites no finding — a research document keeps its evidence")

    # ── the gate, as a warning; the walk marker ──────────────────────────────
    for m in fx.mandates:
        if m.get("status") in ("in-progress", "standing"):
            g = gate_report(fx, m)
            if g["verdict"] == "below":
                P.warn(f"research/mandates/{m['id']}.yaml", "gate", f"primary share {g['primary_share']} below {g['threshold']} over established findings")
    act = (fx.state.get("walk") or {}).get("active")
    if isinstance(act, dict) and act.get("expires_at") and str(act["expires_at"]) < dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"):
        P.warn("state/research.json", "walk.abandoned", f"walk {act.get('run_id')} marker expired {act['expires_at']} without a close")
    ok = not P.errors and not (strict and P.warnings)
    return {"ok": ok, "errors": len(P.errors), "warnings": len(P.warnings), "problems": P.items}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    ap.add_argument("--lock")
    ap.add_argument("--gate")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--no-history", action="store_true")
    ap.add_argument("--as-of")
    a = ap.parse_args(argv)
    fac = Path(a.facility)
    if not (fac / "manifest.yaml").exists() and (fac / "project-state" / "manifest.yaml").exists():
        fac = fac / "project-state"
    if not (fac / "manifest.yaml").exists():
        print(f"check: no manifest.yaml in {a.facility}", file=sys.stderr)
        return 2
    fx = Facility(fac, to_date(a.as_of) or dt.date.today())
    if a.lock or a.gate:
        mid = a.lock or a.gate
        m = fx.mandate.get(mid)
        if not m:
            print(f"check: no mandate {mid}", file=sys.stderr)
            return 2
        if a.lock:
            fails = lock_failures(fx, m)
            out = {"mandate": mid, "can_lock": not fails, "failures": [{"code": c, "message": t} for c, t in fails]}
            if a.json:
                print(json.dumps(out, indent=1))
            else:
                print(f"{mid}: {'may lock' if not fails else 'cannot lock'}")
                for c, t in fails:
                    print(f"  ✗ {c}: {t}")
            return 0 if not fails else 1
        g = gate_report(fx, m)
        if a.json:
            print(json.dumps(g, indent=1))
        else:
            share = "—" if g["primary_share"] is None else f"{round(100 * g['primary_share'])}%"
            print(f"{mid}: primary share {share} of {g['established']} established (gate {round(100 * g['threshold'])}%) · {g['provisional']} provisional · "
                  f"{len(g['blocking_challenges'])} blocking challenge(s) → {'may ship' if g['ship'] else 'may not ship'}")
            for c in g["blocking_challenges"]:
                print(f"  ✗ blocking challenge {c} open")
            if g["verdict"] != "pass":
                print(f"  ✗ evidence gate: {g['verdict']}")
        return 0 if g["ship"] else 1
    out = check(fx, a.strict, not a.no_history)
    if a.json:
        print(json.dumps(out, indent=1, default=str))
    else:
        for p in out["problems"]:
            print(f"{'✗' if p['level'] == 'error' else '·'} {p['where']}: [{p['code']}] {p['message']}")
        print(f"research check: {out['errors']} error(s), {out['warnings']} warning(s)" + (" — clean" if out["ok"] else ""))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
