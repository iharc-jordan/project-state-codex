#!/usr/bin/env python3
"""Validate the tender schema extension inside a project-state facility.

Complements `project-state` validate: checks tender entities, profiles, the
events stream, and state/tender.json connector structure against the schema extension
(templates/schema-extension.md). Report-only — never auto-fixes.

Usage: validate_tender_state.py [FACILITY_ROOT]
  FACILITY_ROOT defaults to walking up from cwd to find project-state/manifest.yaml.

Exit codes: 0 clean, 1 deviations found, 2 facility/package not found.
Requires PyYAML (pip install pyyaml --break-system-packages) — falls back to a
line-based check with a warning if unavailable.
"""
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

REQUIRED_FRONTMATTER = ["id", "kind", "created", "created_by", "last_modified", "last_modified_by", "phase"]
TENDER_BLOCKS = ["title", "buyer", "procurement", "dates", "matching", "qualification", "sources", "workflow", "monitoring"]
PROFILE_FIELDS = ["name", "enabled", "include", "exclude", "weights"]
WORKFLOW_STATUSES = {
    "discovered", "preliminary_match", "documents_required", "under_review", "qualified",
    "bid_no_bid_pending", "pursue", "watch", "partner_opportunity", "dismissed",
    "preparing_response", "submitted", "awarded", "unsuccessful", "cancelled", "closed",
}
QUAL_STATUSES = {"preliminary", "needs_review", "qualified", "disqualified"}
HEALTH_STATES = {"healthy", "delayed", "parsing_error", "authentication_required", "access_restricted", "paused", "unknown"}
EVENT_REQUIRED = ["ts", "actor", "event", "id", "source", "parser_version"]
ID_RE = re.compile(r"^t-\d{4}-\d{4}$")


def find_root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, "project-state", "manifest.yaml")):
            return os.path.join(d, "project-state")
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_yaml(path, problems):
    if yaml is None:
        return None
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception as e:  # report, don't crash the sweep
        problems.append(f"{path}: unparseable YAML ({e})")
        return None


def main(argv):
    root = find_root(argv[0] if argv else os.getcwd())
    if not root:
        print("No project-state/ found.", file=sys.stderr)
        return 2
    problems, warnings = [], []
    if yaml is None:
        warnings.append("PyYAML unavailable — structural checks skipped, frontmatter checked line-wise")

    manifest = load_yaml(os.path.join(root, "manifest.yaml"), problems) or {}
    # capabilities: is canonical; packages: is read as legacy configuration
    pkg = None
    if isinstance(manifest, dict):
        pkg = (manifest.get("capabilities") or {}).get("tender") or (
            manifest.get("packages") or {}
        ).get("tender")
    if not pkg or not pkg.get("enabled"):
        print("tender capability not enabled in manifest.yaml", file=sys.stderr)
        return 2

    tdir = os.path.join(root, "tenders")
    seen_ids = set()

    # Tender entities
    for fn in sorted(os.listdir(tdir)) if os.path.isdir(tdir) else []:
        path = os.path.join(tdir, fn)
        if not fn.endswith(".yaml") or not os.path.isfile(path):
            continue
        if fn in ("tenders.yaml",):
            problems.append(f"{path}: fused entity file — file-per-entity is mandatory")
            continue
        doc = load_yaml(path, problems)
        if doc is None:
            if yaml is None:
                text = open(path).read()
                for k in REQUIRED_FRONTMATTER:
                    if not re.search(rf"^{k}:", text, re.M):
                        problems.append(f"{path}: missing frontmatter '{k}'")
            continue
        for k in REQUIRED_FRONTMATTER:
            if k not in doc:
                problems.append(f"{path}: missing frontmatter '{k}'")
        if doc.get("kind") != "tender":
            problems.append(f"{path}: kind is '{doc.get('kind')}', expected 'tender'")
        tid = doc.get("id", "")
        if tid != os.path.splitext(fn)[0]:
            problems.append(f"{path}: id '{tid}' does not match filename")
        if not ID_RE.match(str(tid)) and "merged_into" not in doc:
            warnings.append(f"{path}: id not in t-YYYY-NNNN form")
        seen_ids.add(tid)
        if "merged_into" in doc:
            continue  # tombstone — minimal shape allowed
        for block in TENDER_BLOCKS:
            if block not in doc:
                problems.append(f"{path}: missing block '{block}'")
        wf = (doc.get("workflow") or {}).get("status")
        if wf and wf not in WORKFLOW_STATUSES:
            problems.append(f"{path}: unknown workflow.status '{wf}'")
        q = doc.get("qualification") or {}
        if q.get("status") and q["status"] not in QUAL_STATUSES:
            problems.append(f"{path}: unknown qualification.status '{q['status']}'")
        if q.get("human_approved") is True and q.get("status") != "qualified":
            problems.append(f"{path}: human_approved true but status is '{q.get('status')}'")
        for s in doc.get("sources") or []:
            if not s.get("portal") or not s.get("role"):
                problems.append(f"{path}: source block missing portal/role")
        if wf == "dismissed" and not (doc.get("workflow") or {}).get("dismissal_reason"):
            problems.append(f"{path}: dismissed without dismissal_reason")

    # Profiles
    pdir = os.path.join(tdir, "profiles")
    for fn in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        if not fn.endswith(".yaml"):
            continue
        path = os.path.join(pdir, fn)
        doc = load_yaml(path, problems)
        if doc is None:
            continue
        for k in REQUIRED_FRONTMATTER + PROFILE_FIELDS:
            if k not in doc:
                problems.append(f"{path}: missing '{k}'")
        if doc.get("kind") != "tender-profile":
            problems.append(f"{path}: kind is '{doc.get('kind')}', expected 'tender-profile'")
        w = doc.get("weights") or {}
        if w and sum(v for v in w.values() if isinstance(v, (int, float))) != 100:
            problems.append(f"{path}: weights sum to {sum(w.values())}, expected 100")

    # Events stream
    epath = os.path.join(tdir, "events.ndjson")
    if os.path.exists(epath):
        for n, line in enumerate(open(epath), 1):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"events.ndjson:{n}: unparseable JSON")
                continue
            for k in EVENT_REQUIRED:
                if k not in ev:
                    problems.append(f"events.ndjson:{n}: missing '{k}'")
            if ev.get("id") and ev["id"] not in seen_ids and not str(ev.get("event", "")).startswith("tender.harvest"):
                warnings.append(f"events.ndjson:{n}: references unknown tender '{ev['id']}'")

    # per-capability state file (contract: state/<capability>.json; legacy state.json read as fallback)
    spath = os.path.join(root, "state", "tender.json")
    if not os.path.exists(spath):
        spath = os.path.join(root, "state.json")
    if os.path.exists(spath):
        try:
            state = json.load(open(spath))
            for cid, c in (state.get("tender_connectors") or {}).items():
                if c.get("health") not in HEALTH_STATES:
                    problems.append(f"{os.path.basename(spath)}: connector '{cid}' has unknown health '{c.get('health')}'")
            counters = state.get("counters") or {}
            n_real = len([i for i in seen_ids])
            if counters.get("tenders") is not None and counters["tenders"] < n_real:
                warnings.append(f"{os.path.basename(spath)}: counters.tenders={counters['tenders']} < {n_real} entity files")
        except json.JSONDecodeError:
            problems.append(f"{os.path.basename(spath)}: unparseable JSON")

    for w in warnings:
        print(f"  warn  {w}")
    for p in problems:
        print(f"  FAIL  {p}")
    print(f"\ntender validate: {len(problems)} problem(s), {len(warnings)} warning(s), {len(seen_ids)} tender(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
