#!/usr/bin/env python3
"""
project-jira-publisher — push project-state entities to Jira via the REST API.

Idempotent: the first publish CREATEs an issue and writes the returned key back onto
the entity file as `jira_key: PROJ-123`; subsequent runs UPDATE that issue. So you can
re-run safely after editing milestones/risks/etc. — nothing duplicates.

Config (non-secret) is read from manifest.yaml `surfaces.jira`; the token is read from
the environment so it never lands in the substrate:

  surfaces:
    jira:
      enabled: true
      base_url: https://yourco.atlassian.net
      project_key: PROJ
      issue_type: Task          # default for every kind; per-kind overrides below
      issue_types:              # optional per-kind override
        milestone: Epic
      email: you@co.com         # optional; or set JIRA_EMAIL

  env:  JIRA_API_TOKEN  (required)   JIRA_EMAIL / JIRA_BASE_URL / JIRA_PROJECT_KEY (override)

Usage:
  python3 publish.py [--state-dir DIR] [--only milestones,risks] [--dry-run]

Requires: PyYAML (pip install pyyaml). HTTP uses only the stdlib.
"""
import argparse, base64, json, os, sys, urllib.request, urllib.error
from pathlib import Path
try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

KINDS = ["milestones", "risks", "decisions", "objectives", "kpis"]
LABEL = {"milestones": "milestone", "risks": "risk", "decisions": "decision",
         "objectives": "objective", "kpis": "kpi"}


def find_state_dir(explicit):
    if explicit:
        return Path(explicit)
    d = Path.cwd()
    for _ in range(8):
        for name in ("project-state", ".project-state"):
            c = d / name
            if (c / "manifest.yaml").exists():
                return c
        if d.parent == d:
            break
        d = d.parent
    sys.exit("Could not find a project-state/ with manifest.yaml. Pass --state-dir.")


def load_yaml(p):
    try:
        return yaml.safe_load(p.read_text()) or {}
    except Exception as e:
        print(f"  ! skip {p.name}: {e}")
        return None


def write_back_key(path, key):
    """Add/replace `jira_key: KEY` without disturbing the rest of the file."""
    text = path.read_text()
    lines = text.splitlines()
    out, found = [], False
    for ln in lines:
        if ln.startswith("jira_key:"):
            out.append(f"jira_key: {key}")
            found = True
        else:
            out.append(ln)
    if not found:
        out.append(f"jira_key: {key}")
    path.write_text("\n".join(out) + "\n")


def issue_for(kind, data):
    """Map a substrate entity → (summary, description, labels)."""
    eid = str(data.get("id", ""))
    if kind == "milestones":
        summ = data.get("title") or eid
        body = [f"Milestone {eid}", "", data.get("narrative", "") or "",
                f"\nPercent complete: {data.get('percent_complete', 0)}%",
                f"Status: {data.get('status', '')}",
                f"Planned end: {data.get('planned_end', '')}",
                f"Technical progress: {data.get('technical_progress', '') or ''}"]
        labels = ["milestone", _slug(data.get("status"))]
    elif kind == "risks":
        summ = data.get("title") or eid
        body = [f"Risk {eid}", "", f"Exposure: {data.get('exposure', data.get('score', ''))}",
                f"\nMitigation: {data.get('mitigation', '') or ''}",
                f"Status: {data.get('status', '')}"]
        labels = ["risk", _slug(data.get("status"))]
    elif kind == "decisions":
        summ = data.get("title") or eid
        body = [f"Decision {eid}", "", data.get("decision", "") or data.get("narrative", "") or "",
                f"\nRationale: {data.get('rationale', '') or ''}",
                f"Date: {data.get('date', '')}"]
        labels = ["decision"]
    elif kind == "objectives":
        summ = data.get("title") or eid
        body = [f"Objective {eid} ({data.get('horizon', '')})", "",
                data.get("description", "") or data.get("narrative", "") or "",
                f"\nHow to meet it: {data.get('guidance', '') or ''}",
                f"Status: {data.get('status', '')}"]
        labels = ["objective", _slug(data.get("horizon"))]
    else:  # kpis
        summ = data.get("metric") or eid
        unit = data.get("unit", "")
        body = [f"KPI {eid}", "",
                f"{data.get('baseline', '')} → {data.get('current', '')} → target {data.get('target', '')} {unit}".strip(),
                f"Direction: {data.get('direction', '')}",
                f"How it's measured: {data.get('method', '') or ''}",
                f"How to move it: {data.get('guidance', '') or ''}"]
        labels = ["kpi"]
    labels = [l for l in labels if l]
    return summ[:240], "\n".join(str(b) for b in body if b is not None), labels


def _slug(x):
    return str(x).strip().lower().replace(" ", "-") if x else ""


def jira_request(cfg, method, path, payload=None):
    url = cfg["base_url"].rstrip("/") + path
    auth = base64.b64encode(f"{cfg['email']}:{cfg['token']}".encode()).decode()
    req = urllib.request.Request(url, method=method, headers={
        "Authorization": f"Basic {auth}", "Content-Type": "application/json",
        "Accept": "application/json"})
    if payload is not None:
        req.data = json.dumps(payload).encode()
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"  ! Jira {method} {path} → {e.code}: {e.read().decode()[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir")
    ap.add_argument("--only", help="comma list: " + ",".join(KINDS))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--emit-json", action="store_true",
                    help="Print the publish plan (one object per entity) as JSON and exit — "
                         "for driving the publish through an available Atlassian connector instead of REST. "
                         "Milestones map to Epic, everything else to Task.")
    args = ap.parse_args()

    state = find_state_dir(args.state_dir)
    manifest = load_yaml(state / "manifest.yaml") or {}
    jira = (manifest.get("surfaces") or {}).get("jira") or {}

    cfg = {
        "base_url": os.environ.get("JIRA_BASE_URL") or jira.get("base_url", ""),
        "project_key": os.environ.get("JIRA_PROJECT_KEY") or jira.get("project_key", ""),
        "email": os.environ.get("JIRA_EMAIL") or jira.get("email", ""),
        "token": os.environ.get("JIRA_API_TOKEN", ""),
    }
    issue_types = {**({"milestones": "Task", "risks": "Task", "decisions": "Task",
                       "objectives": "Task", "kpis": "Task"}),
                   **{f"{k}s" if not k.endswith("s") else k: v
                      for k, v in (jira.get("issue_types") or {}).items()}}
    default_type = jira.get("issue_type", "Task")

    kinds = [k.strip() for k in args.only.split(",")] if args.only else KINDS
    kinds = [k for k in kinds if k in KINDS]

    if args.emit_json:
        plan = []
        for kind in kinds:
            d = state / kind
            if not d.is_dir():
                continue
            for path in sorted(d.glob("*.yaml")):
                data = load_yaml(path)
                if not data:
                    continue
                summary, description, labels = issue_for(kind, data)
                plan.append({
                    "path": str(path), "kind": kind, "id": str(data.get("id", "")),
                    "issuetype": "Epic" if kind == "milestones" else "Task",
                    "summary": summary, "description": description, "labels": labels,
                    "jira_key": data.get("jira_key"),
                })
        print(json.dumps(plan))
        return

    if not args.dry_run:
        missing = [k for k in ("base_url", "project_key", "email", "token") if not cfg[k]]
        if missing:
            sys.exit("Missing Jira config: " + ", ".join(missing) +
                     " (set surfaces.jira.* in manifest + JIRA_API_TOKEN/JIRA_EMAIL in env).")

    created = updated = 0
    for kind in kinds:
        d = state / kind
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.yaml")):
            data = load_yaml(path)
            if not data:
                continue
            summary, description, labels = issue_for(kind, data)
            itype = issue_types.get(kind, default_type)
            key = data.get("jira_key")
            if args.dry_run:
                print(f"  {'UPDATE ' + key if key else 'CREATE'}  [{itype}] {summary}  labels={labels}")
                continue
            fields = {"project": {"key": cfg["project_key"]}, "summary": summary,
                      "description": description, "issuetype": {"name": itype}, "labels": labels}
            if key:
                jira_request(cfg, "PUT", f"/rest/api/2/issue/{key}", {"fields": fields})
                print(f"  updated {key}  {summary}")
                updated += 1
            else:
                res = jira_request(cfg, "POST", "/rest/api/2/issue", {"fields": fields})
                new_key = res.get("key")
                write_back_key(path, new_key)
                print(f"  created {new_key}  {summary}")
                created += 1

    if args.dry_run:
        print("\n(dry run — nothing sent to Jira)")
    else:
        print(f"\nDone: {created} created, {updated} updated.")


if __name__ == "__main__":
    main()
