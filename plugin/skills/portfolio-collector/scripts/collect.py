#!/usr/bin/env python3
"""portfolio-collector — snapshot, index, understand.

The deterministic engine under the portfolio-collector skill. Reads each member project's own
project-state/ AS IT IS, writes dated snapshots into the PORTFOLIO project's substrate, compiles
the cross-member index (one flat file per entity kind, every row tagged with member and path),
recompiles the registry, regenerates one cited understanding page per member, and — on the
weekly run — writes the change note. Read-only toward members: it never writes, locks or logs
inside a member project. Spec: docs/PORTFOLIO-CAPABILITY-SPEC.md §6.2.

USAGE
    collect.py [--portfolio DIR] [all | MEMBER-ID] [--dry-run] [--force] [--week]
               [--as-of YYYY-MM-DD] [--actor NAME] [--json] [--transport auto|mcp|files]

    --portfolio   the portfolio's project-state/ directory (default: walk up from cwd)
    all           every member with status active | paused | closing   (default)
    MEMBER-ID     one member, even if paused
    --dry-run     report what would be read and written; write nothing
    --force       ignore the unchanged-revision short-circuit
    --week        also write portfolio/reports/week-<date>.md (the scheduled run passes this)
    --as-of       compute "today" from this date (fixtures, evals); default: today UTC
    --json        print the run summary as JSON instead of a table
    --transport   how members are read (member_source.py). auto (default): through the local
                  project-state server when it serves the member, else the files; a location.type:
                  server member through the cloud server. mcp: through a server or not at all.
                  files: the files only (server members are then unreachable, reason remote).

Members are located by portfolio/members/<id>.yaml location.type: local (a path under workspace_root),
registry (a workspace-registry "org/project", resolved to its folder; the reach still applies), server
(an "org/project" in the cloud, read with its org's token from ~/.config/project-state/mcp-tokens.json, or $PS_MCP_URL and a bearer token), hub or appliance (a local
clone recorded on the row). Every snapshot records how it was read in read_via.

Requires PyYAML (already required by the other guards). Stdlib otherwise.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("collect.py: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from member_source import (FileSource, McpClient, McpError, McpSource, cloud_tokens,  # noqa: E402
                           cloud_folders, entitlement_status, local_server_cmd, parse_yaml, registry_cloud_rows, registry_folder, registry_rows)

ACTOR_DEFAULT = "portfolio-collector"
ACTIVE_STATUSES = {"active", "paused", "closing"}
OPEN_MILESTONE = {"planned", "in_progress", "at_risk", "blocked", "overdue"}
DONE_MILESTONE = {"complete", "completed", "done"}
CANCELLED_MILESTONE = {"cancelled", "canceled", "withdrawn"}
PENDING_DECISION = {"pending", "proposed", "open", "draft"}


# ── small io helpers ─────────────────────────────────────────────────────────
def yload(p: Path):
    try:
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None
    except Exception as e:  # malformed
        raise RuntimeError(f"malformed: {p}: {e}") from e


def ydump(obj) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=110)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def iso(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date(v) -> dt.date | None:
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return dt.datetime.strptime(s[: 10 if fmt == "%Y-%m-%d" else len(s)], fmt).date()
        except ValueError:
            continue
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None


def parse_ts(v) -> dt.datetime | None:
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.replace(tzinfo=None)
    try:
        return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        d = parse_date(v)
        return dt.datetime(d.year, d.month, d.day) if d else None


def days_between(a: dt.date | None, b: dt.date | None) -> int | None:
    if a is None or b is None:
        return None
    return (b - a).days


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


# ── run context ──────────────────────────────────────────────────────────────
class Run:
    def __init__(self, args):
        self.args = args
        self.today = dt.date.fromisoformat(args.as_of) if args.as_of else dt.datetime.utcnow().date()
        self.now = dt.datetime(self.today.year, self.today.month, self.today.day, 5, 30, 0) if args.as_of else dt.datetime.utcnow().replace(microsecond=0)
        self.ps = find_portfolio(Path(args.portfolio).resolve() if args.portfolio else Path.cwd())
        manifest = yload(self.ps / "manifest.yaml") or {}
        cap = ((manifest.get("capabilities") or {}).get("portfolio")) or {}
        if not cap or cap.get("enabled") is False:
            die("portfolio capability is not enabled in this project's manifest")
        # the cloud server's own collect reads its members from folders it materialized; a portfolio that lives
        # in the cloud has no disk to reach, so workspace_root may be absent there (and nothing on disk is read)
        folders = cloud_folders()
        self.server_side, self.cloud_folders = folders is not None, folders or {}
        for key in (("subject",) if self.server_side else ("workspace_root", "subject")):
            v = cap.get(key)
            # the app now writes these through manifest_set (scalar); a one-element list is still
            # accepted for manifests written by the older list-only config_add action
            if isinstance(v, list):
                v = next((x for x in v if x), None)
                cap[key] = v
            if not v or str(v).strip() == "REQUIRED":
                die(f"capabilities.portfolio.{key} is REQUIRED — enable refuses without it; nothing collected")
        self.cap = cap
        self.portfolio_name = ((manifest.get("project") or {}).get("name")) or self.ps.parent.name
        wr = cap.get("workspace_root")
        if self.server_side or not wr or str(wr).strip() == "REQUIRED":
            # inside the cloud server there is no disk to reach, whatever the manifest says: a workspace_root
            # resolved from the server's working copy would land in its own cache
            self.workspace_root = Path("/nonexistent-workspace-root")
        else:
            wr = Path(str(wr))
            self.workspace_root = (wr if wr.is_absolute() else (self.ps / wr)).resolve()
        idx = cap.get("index") or {}
        self.activity_window = int(idx.get("activity_window_days", 30))
        self.deadline_window = int(idx.get("deadline_window_days", 90))
        self.silence_days = int(cap.get("silence_threshold_days", 14))
        self.stale_days = int(cap.get("harvest_stale_after_days", 3))
        self.cadence_days = int(cap.get("snapshot_cadence_days", 7))
        self.state_path = self.ps / "state" / "portfolio.json"
        try:
            self.state = json.loads(read_text(self.state_path) or "{}")
        except json.JSONDecodeError:
            self.state = {}
        self.state.setdefault("schema_version", 1)
        self.state.setdefault("counters", {"dependency": 0, "finding": 0})
        self.state.setdefault("cursors", {})
        self.events: list[dict] = []
        self.summary: list[dict] = []
        self.writes: list[str] = []
        self._local = None                    # MCP clients, started on first use
        self._clouds: dict[str, McpClient | bool] = {}   # token → a cloud client (a service token per org, or one for all)
        self._local_refs: dict[str, str] = {}  # member folder → the local server's "org/project"
        self.cloud_error: str | None = None

    # the local project-state server, serving this portfolio (and so the registry within its reach)
    def local(self) -> McpClient | None:
        if self._local is None and self.args.transport != "files":
            cmd = local_server_cmd(Path(__file__))
            if cmd:
                try:
                    self._local = McpClient(cmd=[*cmd, "--root", str(self.ps)], env={**os.environ, "PROJECT_STATE_NO_OS_ACTOR": "1"})
                    for row in self._local.call("project_list", {}).get("projects", []):
                        if row.get("folder") and row.get("access") == "viewer":
                            self._local_refs[str(Path(row["folder"]).resolve())] = row["project"]
                except (McpError, OSError) as e:
                    print(f"warn: the local project-state server did not start: {e}", file=sys.stderr)
                    self._local = False
            else:
                self._local = False
        return self._local or None

    # The cloud client for one org's projects: that org's service token (mcp-tokens.json), else the any-org token.
    # A portfolio on this disk reads its cloud members unattended this way, each with its own org's token.
    def cloud(self, org: str | None = None) -> McpClient | None:
        url, by_org, default = cloud_tokens()
        tok = by_org.get(org) if org else None
        tok = tok or default or (None if org else next(iter(by_org.values()), None))
        if not (url and tok):
            self.cloud_error = f"no cloud token for {org}" if org and by_org else "no cloud server configured (a token in ~/.config/project-state/mcp-tokens.json, or $PS_MCP_URL and a token)"
            return None
        if tok not in self._clouds:
            try:
                self._clouds[tok] = McpClient(url=url, token=tok)
            except McpError as e:
                self._clouds[tok] = False
                self.cloud_error = str(e)
        return self._clouds[tok] or None

    def cloud_clients(self) -> list[McpClient]:
        """One client per token configured: each lists the projects its org's token can see."""
        url, by_org, default = cloud_tokens()
        orgs = list(by_org) + ([None] if default else [])
        return [c for c in (self.cloud(o) for o in orgs) if c] if url else []

    # ref → the cloud's own word on where that project's home is (server, or local for a Published mirror),
    # else the registry's last reading of it
    def cloud_home(self, ref: str) -> str | None:
        if not hasattr(self, "_cloud_homes"):
            self._cloud_homes = {str(r.get("ref")): r.get("home") for r in registry_cloud_rows()}
            if self.args.transport != "files":
                for c in self.cloud_clients():
                    try:
                        self._cloud_homes.update({r["project"]: r.get("home") for r in c.call("project_list", {}).get("projects", [])})
                    except McpError:
                        pass
        return self._cloud_homes.get(ref)

    def cloud_source(self, ref: str):
        if ref in self.cloud_folders:  # the cloud server's own collect: a copy it materialized for this caller
            return FileSource(self.cloud_folders[ref], via="cloud"), None
        client = None if self.server_side or self.args.transport == "files" else self.cloud(ref.split("/")[0])
        if not client:
            return None, "remote"
        return McpSource(client, ref, "cloud"), None

    # a member folder on this disk → how to read it (auto: through the local server when it serves it)
    def source_for(self, p: Path):
        if self.args.transport != "files" and self.local():
            ref = self._local_refs.get(str(p.resolve()))
            if ref:
                return McpSource(self._local, ref, "local-mcp"), None
        if self.args.transport == "mcp":
            return None, "remote"  # the server does not serve it and files were ruled out
        return FileSource(p), None

    def close(self):
        for c in (self._local, *self._clouds.values()):
            if c:
                c.close()

    # writes go through here so --dry-run can refuse them all in one place
    def write(self, rel: str, content: str):
        self.writes.append(rel)
        if self.args.dry_run:
            return
        p = self.ps / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def log(self, event: str, detail: str, data: dict | None = None):
        line = {"ts": iso(self.now), "actor": self.args.actor, "event": event, "detail": detail}
        if data:
            line["data"] = data
        self.events.append(line)


def die(msg: str):
    print(f"collect.py: {msg}", file=sys.stderr)
    sys.exit(1)


def find_portfolio(start: Path) -> Path:
    for cand in [start, *start.parents]:
        ps = cand if cand.name == "project-state" else cand / "project-state"
        m = ps / "manifest.yaml"
        if m.exists():
            data = yload(m) or {}
            if (data.get("capabilities") or {}).get("portfolio"):
                return ps
    die("no project-state/ with capabilities.portfolio found walking up from " + str(start))
    raise SystemExit  # unreachable


# ── member resolution and reading ────────────────────────────────────────────
def load_members(run: Run) -> list[dict]:
    rows = []
    for p in sorted((run.ps / "portfolio" / "members").glob("*.yaml")):
        m = yload(p) or {}
        if m.get("id") and m.get("id") != p.stem:
            print(f"warn: {p.name}: id {m['id']!r} != filename", file=sys.stderr)
        m.setdefault("id", p.stem)
        rows.append(m)
    return rows


def member_path(run: Run, m: dict) -> tuple[Path | None, str | None]:
    """A local or registry row → the member's project-state/ on this disk, inside workspace_root."""
    loc = m.get("location") or {}
    t = loc.get("type") or "none"
    if t == "local":
        raw = loc.get("path")
        if not raw:
            return None, "missing"
        p = Path(str(raw))
        p = (p if p.is_absolute() else (run.ps / p)).resolve()
    elif t == "registry":
        p = registry_folder(str(loc.get("ref") or ""))
        if p is None:
            return None, "missing"
    else:
        return None, "missing"
    reason = in_reach(run, p)
    return (None, reason) if reason else (p, None)


def in_reach(run: Run, p: Path) -> str | None:
    try:
        p.relative_to(run.workspace_root)
    except ValueError:
        return "permission"
    return None if (p / "manifest.yaml").exists() else "missing"


def disk_substrate(repo) -> Path | None:
    for d in ("project-state", ".project-state"):
        if repo and (Path(repo) / d / "manifest.yaml").exists():
            return (Path(repo) / d).resolve()
    return None


def intended_repo(run: Run, m: dict) -> str | None:
    """Where a local or registry row says the member's repo is, whether or not it is there now."""
    loc = m.get("location") or {}
    if loc.get("type") == "local" and loc.get("path"):
        p = Path(str(loc["path"]))
        return str((p if p.is_absolute() else (run.ps / p)).resolve().parent)
    if loc.get("type") == "registry":
        org, _, project = str(loc.get("ref") or "").partition("/")
        row = next((r for r in registry_rows() if str(r.get("org")) == org and str(r.get("project")) == project), None)
        return str(Path(row["path"]).resolve()) if row and row.get("path") else None
    return None


def moved_to(p: Path) -> str | None:
    h = (yload(p / "manifest.yaml") or {}).get("home") or {}
    return f"{h.get('org')}/{h.get('project')}" if isinstance(h, dict) and h.get("kind") == "server" else None


def copies(run: Run, m: dict) -> list[tuple[str, object, str | None]]:
    """The member's copies, home first: [(home | mirror | moved-copy, source or None, reason when None)].

    Decision 2026-09-27-mixed-local-and-cloud-homes, item 3: a project with a copy in each home is one
    member. Its home copy is read when it answers; otherwise the other copy, and the snapshot says so.
    """
    loc = m.get("location") or {}
    t = loc.get("type") or "none"
    if t == "none":
        return [("home", None, "missing")]
    if t in ("local", "registry"):
        p, reason = member_path(run, m)
        moved = moved_to(p) if p else None
        if moved:  # this folder is the read-only copy of a project that moved to the cloud
            return [("home", *run.cloud_source(moved)), ("moved-copy", *run.source_for(p))]
        out = [("home", *(run.source_for(p) if p else (None, reason)))]
        repo = intended_repo(run, m)
        mirror = loc.get("mirror") or next((str(r.get("ref")) for r in registry_cloud_rows()
                                            if repo and r.get("copy_on_disk") and str(Path(str(r["copy_on_disk"])).resolve()) == repo
                                            and r.get("home") != "server"), None)
        if mirror:
            out.append(("mirror", *run.cloud_source(mirror)))
        return out
    if t == "server":
        ref = str(loc.get("ref") or "")
        if not ref:
            return [("home", None, "missing")]
        row = next((r for r in registry_cloud_rows() if str(r.get("ref")) == ref), {})
        disk = disk_substrate(row.get("copy_on_disk"))
        disk_src = (None, in_reach(run, disk)) if disk and in_reach(run, disk) else (run.source_for(disk) if disk else None)
        if run.cloud_home(ref) == "local":  # the cloud holds a Published mirror; the home is a folder
            return ([("home", *disk_src)] if disk_src else []) + [("mirror", *run.cloud_source(ref))]
        return [("home", *run.cloud_source(ref))] + ([("moved-copy", *disk_src)] if disk_src else [])
    if t in ("hub", "appliance"):
        # V1: only a local clone recorded on the row is readable; never clone, never call out.
        raw = loc.get("path")
        if raw and (Path(str(raw)).expanduser() / "manifest.yaml").exists():
            return [("home", FileSource(Path(str(raw)).expanduser().resolve()), None)]
        return [("home", None, "remote")]
    return [("home", None, "missing")]


def read_dir(member_ps: Path, d: str) -> list[tuple[str, dict]]:
    """The portfolio's own files (findings, dependencies)."""
    return read_member_dir(FileSource(member_ps), d)


def read_member_dir(src, d: str) -> list[tuple[str, dict]]:
    out = []
    for rel in src.listdir(d):
        try:
            data = parse_yaml(src.text(rel), rel)
        except RuntimeError:
            continue
        if isinstance(data, dict):
            data.setdefault("id", Path(rel).stem)
            out.append((rel, data))
    return out


def read_activity(src, since: dt.datetime) -> list[dict]:
    lines = []
    for raw in src.activity_text(iso(since)).splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        ts = parse_ts(obj.get("ts"))
        if ts and ts >= since:
            obj["_ts"] = ts
            lines.append(obj)
    return lines


def read_member(run: Run, m: dict, src) -> dict:
    """Everything the snapshot needs, read as-is. Absent stays absent."""
    manifest = parse_yaml(src.text("manifest.yaml"), "manifest.yaml") or {}
    try:
        state = json.loads(src.text("state.json") or "{}")
    except json.JSONDecodeError:
        state = {}
    proj = manifest.get("project") or {}
    milestones = read_member_dir(src, "milestones")
    risks = read_member_dir(src, "risks")
    decisions = read_member_dir(src, "decisions")
    people = read_member_dir(src, "people")
    cursors = read_member_dir(src, "harvest/cursors")
    docs_index = parse_yaml(src.text("documents/index.yaml"), "documents/index.yaml") or {}
    docs = docs_index.get("docs") or docs_index.get("entries") or []
    since = run.now - dt.timedelta(days=run.activity_window)
    activity = read_activity(src, since)
    caps = manifest.get("capabilities") or {}
    return dict(manifest=manifest, state=state, project=proj, milestones=milestones, risks=risks,
                decisions=decisions, people=people, cursors=cursors, docs=docs, activity=activity,
                capabilities=[k for k, v in caps.items() if isinstance(v, dict) and v.get("enabled") is not False],
                packs=proj.get("packs_loaded") or [], via=src.via)


# ── snapshot ─────────────────────────────────────────────────────────────────
# A risk's score on the 1-9 likelihood x impact scale. Members write it several ways (found 2026-09-30 in ai26-10 and
# project-state, which crashed the collect): a number, digits as text, a word ("high", "medium"), or a stray value
# ("closed"). A number wins; else likelihood x impact; else the word on the same scale; else unscored.
def risk_score(rk: dict) -> int | None:
    raw = rk.get("score")
    if isinstance(raw, bool):
        raw = None
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    scale = {"low": 1, "medium": 2, "high": 3}
    li, im = scale.get(str(rk.get("likelihood") or "").strip().lower()), scale.get(str(rk.get("impact") or "").strip().lower())
    if li and im:
        return li * im
    return {"low": 2, "medium": 4, "high": 6, "critical": 9}.get(str(raw or "").strip().lower())


def build_snapshot(run: Run, m: dict, rev: str | None, r: dict) -> dict:
    today = run.today
    ms_rows = []
    counts = Counter()
    for path, ms in r["milestones"]:
        st = str(ms.get("status") or "planned")
        pe = parse_date(ms.get("planned_end"))
        if st in DONE_MILESTONE:
            counts["complete"] += 1
        elif st in CANCELLED_MILESTONE:
            counts["cancelled"] += 1
        else:
            if st == "in_progress":
                counts["in_progress"] += 1
            elif st == "at_risk":
                counts["at_risk"] += 1
            elif st == "blocked":
                counts["blocked"] += 1
            else:
                counts["planned"] += 1
            if pe and pe < today and st not in DONE_MILESTONE:
                counts["overdue"] += 1
            ms_rows.append(dict(id=ms["id"], title=ms.get("title"), planned_end=str(pe) if pe else None,
                                owner=ms.get("owner_person") or ms.get("owner"), status=st,
                                percent_complete=ms.get("percent_complete"), path=path))
    ms_rows.sort(key=lambda x: (x["planned_end"] or "9999", x["id"]))
    total = len(r["milestones"]) - counts["cancelled"]

    high, open_risks = [], 0
    for path, rk in r["risks"]:
        if str(rk.get("status") or "open") in ("closed", "retired", "resolved"):
            continue
        open_risks += 1
        score = risk_score(rk)
        if (score or 0) >= 6:
            high.append(dict(id=rk["id"], title=rk.get("title"), score=score, owner=rk.get("owner"),
                             last_reviewed=str(parse_date(rk.get("last_reviewed")) or ""), path=path))
    high.sort(key=lambda x: -(x["score"] or 0))

    pending, recent = [], []
    for path, dc in r["decisions"]:
        st = str(dc.get("status") or "").lower()
        d = parse_date(dc.get("date"))
        if st in PENDING_DECISION:
            pending.append(dict(id=dc["id"], title=dc.get("title"), needed_by=str(parse_date(dc.get("needed_by")) or "") or None, path=path))
        elif d and (today - d).days <= 30:
            recent.append(dict(id=dc["id"], date=str(d), title=dc.get("title"), path=path))
    recent.sort(key=lambda x: x["date"], reverse=True)

    deadlines = []
    horizon = today + dt.timedelta(days=run.deadline_window)
    for x in ms_rows:
        pe = parse_date(x["planned_end"])
        if pe and today - dt.timedelta(days=7) <= pe <= horizon:
            deadlines.append(dict(date=str(pe), label=f"{x['id']} {x['title'] or ''}".strip(), source="milestone",
                                  ref=x["id"], path=x["path"], owner=x["owner"], status=x["status"]))
    for x in pending:
        nb = parse_date(x["needed_by"])
        if nb and nb <= horizon:
            deadlines.append(dict(date=str(nb), label=f"Decision: {x['title']}", source="decision", ref=x["id"],
                                  path=x["path"], owner=None, status="pending"))
    deadlines.sort(key=lambda x: x["date"])

    in_flight = defaultdict(list)
    for x in ms_rows:
        if x["owner"] and x["status"] in ("in_progress", "at_risk", "blocked"):
            in_flight[x["owner"]].append(x["id"])
    people = []
    for path, pp in r["people"]:
        people.append(dict(id=pp["id"], name=pp.get("full_name") or pp.get("name"), role=pp.get("role_on_project") or pp.get("role"),
                           in_flight_milestones=in_flight.get(pp["id"], []), path=path))
    for owner, ids in in_flight.items():  # owners with no people file still count
        if not any(p["id"] == owner for p in people):
            people.append(dict(id=owner, name=None, role=None, in_flight_milestones=ids, path=None))

    acts = r["activity"]
    last_ts = max((a["_ts"] for a in acts), default=None)
    ev7 = sum(1 for a in acts if a["_ts"] >= run.now - dt.timedelta(days=7))

    surfaces = []
    for path, c in r["cursors"]:
        upd = parse_ts(c.get("updated_at")) or parse_ts(c.get("cursor"))
        age = (run.now - upd).days if upd else None
        surfaces.append(dict(surface=c.get("surface") or Path(path).stem.split("--")[-1], cursor_age_days=age,
                             last_run=iso(upd) if upd else None, path=path))
    dismissed = [dict(doc=d.get("slug") or d.get("id"), title=d.get("title"), surface=d.get("surface"),
                      contact=d.get("contact"), keywords=d.get("keywords") or d.get("tags") or [],
                      dismissed=str(parse_date(d.get("triage_timestamp")) or ""))
                 for d in r["docs"] if str(d.get("triage_state") or "") == "dismissed"]
    untriaged = sum(1 for d in r["docs"] if str(d.get("status") or "") == "inbox" and str(d.get("triage_state") or "unprocessed") == "unprocessed")

    snap = {
        "kind": "portfolio-snapshot",
        "member_id": m["id"],
        "captured_at": iso(run.now),
        "source_rev": rev,
        "read_via": r["via"],
        "read_copy": r["copy"],
        **({"copy_as_of": r["copy_as_of"], "home_unreachable": r["home_unreachable"]} if r["copy"] != "home" else {}),
        "reachable": True,
        "project": {
            "name": r["project"].get("name"), "kind": r["project"].get("kind"),
            "one_liner": (str(r["project"].get("one_liner") or "").strip() or None),
            "current_phase": r["state"].get("current_phase") or (r["manifest"].get("phases") or {}).get("current_phase"),
            "phase_entered": (r["state"].get("pointers") or {}).get("phase_entered"),
            "packs_loaded": r["packs"], "capabilities_enabled": r["capabilities"],
        },
        "milestones": {"total": total, "complete": counts["complete"], "in_progress": counts["in_progress"],
                        "at_risk": counts["at_risk"], "blocked": counts["blocked"], "overdue": counts["overdue"],
                        "planned": counts["planned"], "next_due": ms_rows[:5]},
        "risks": {"open": open_risks, "high": high},
        "decisions": {"pending": pending, "recent": recent[:5]},
        "deadlines": deadlines,
        "people": people,
        "activity": {"last_event_at": iso(last_ts) if last_ts else None, "events_7d": ev7,
                      f"events_{run.activity_window}d": len(acts)},
        "harvest": {"delegated_to_portfolio": [], "surfaces": surfaces,
                     "inbox": {"untriaged": untriaged, "dismissed_30d": len(dismissed), "dismissed_items": dismissed}},
        "health": r["state"].get("health") or {},
        "gaps": [f"no owner on {x['id']}" for x in ms_rows if not x["owner"]][:5],
    }
    # the reverse edge: entities citing a portfolio finding
    became = []
    for kind, rows in (("risks", r["risks"]), ("decisions", r["decisions"]), ("milestones", r["milestones"])):
        for path, e in rows:
            src = str(e.get("source") or "")
            if src.startswith("portfolio:"):
                became.append(dict(finding=src.split(":", 1)[1], entity=path))
    snap["_became"] = became
    return snap


# ── index ────────────────────────────────────────────────────────────────────
def compile_index(run: Run, members: list[dict], latest: dict[str, dict], raw: dict[str, dict]) -> dict:
    """latest: member_id -> snapshot; raw: member_id -> the read_member() bundle."""
    idx = defaultdict(list)
    tags = defaultdict(list)

    def tag(member, kind, eid, tlist):
        for t in tlist or []:
            tags[str(t).lower()].append(dict(member=member, kind=kind, id=eid))

    for m in members:
        mid = m["id"]; s = latest.get(mid); r = raw.get(mid)
        row = dict(member=mid, name=m.get("name"), status=m.get("status"), member_kind=m.get("member_kind"),
                   priority=m.get("priority"), owner=m.get("owner"), tags=m.get("tags") or [], added=str(m.get("added") or ""))
        if s:
            row.update(current_phase=s["project"]["current_phase"], milestones=f"{s['milestones']['complete']}/{s['milestones']['total']}",
                       at_risk=s["milestones"]["at_risk"] + s["milestones"]["blocked"], open_risks=s["risks"]["open"],
                       max_risk_score=max((x["score"] or 0 for x in s["risks"]["high"]), default=None),
                       pending_decisions=len(s["decisions"]["pending"]),
                       next_deadline=(s["deadlines"][0] if s["deadlines"] else None),
                       last_event_at=s["activity"]["last_event_at"], events_7d=s["activity"]["events_7d"],
                       harvest_worst_age=max((x["cursor_age_days"] or 0 for x in s["harvest"]["surfaces"]), default=None),
                       reachable=s["reachable"], snapshot=s["captured_at"][:10])
        idx["members"].append(row)
        tag(mid, "member", mid, m.get("tags"))
        if not r:
            continue
        for path, ms in r["milestones"]:
            idx["milestones"].append(dict(member=mid, id=ms["id"], path=path, title=ms.get("title"), status=ms.get("status"),
                                          planned_end=str(parse_date(ms.get("planned_end")) or "") or None,
                                          percent_complete=ms.get("percent_complete"), owner=ms.get("owner_person") or ms.get("owner"),
                                          tags=ms.get("tags") or []))
            tag(mid, "milestone", ms["id"], ms.get("tags"))
        for path, rk in r["risks"]:
            idx["risks"].append(dict(member=mid, id=rk["id"], path=path, title=rk.get("title"), status=rk.get("status"),
                                     score=risk_score(rk), owner=rk.get("owner"), last_reviewed=str(parse_date(rk.get("last_reviewed")) or "") or None,
                                     tags=rk.get("tags") or [], source=rk.get("source")))
            tag(mid, "risk", rk["id"], rk.get("tags"))
        for path, dc in r["decisions"]:
            idx["decisions"].append(dict(member=mid, id=dc["id"], path=path, title=dc.get("title"), status=dc.get("status"),
                                         date=str(parse_date(dc.get("date")) or "") or None,
                                         needed_by=str(parse_date(dc.get("needed_by")) or "") or None, tags=dc.get("tags") or []))
            tag(mid, "decision", dc["id"], dc.get("tags"))
        for d in r["docs"]:
            idx["documents"].append(dict(member=mid, id=d.get("slug") or d.get("id"), path="documents/index.yaml", title=d.get("title"),
                                         status=d.get("status"), triage_state=d.get("triage_state"), kind=d.get("kind")))
        for a in r["activity"]:
            line = {k: v for k, v in a.items() if k != "_ts"}; line["member"] = mid
            idx["activity"].append(line)
        if s:
            for x in s["deadlines"]:
                idx["deadlines"].append(dict(member=mid, **x))
            for p in s["people"]:
                idx["people_raw"].append((mid, p, s))

    # people: one row per person across members
    people = defaultdict(lambda: dict(members=[], next_90d=0))
    for mid, p, s in idx.pop("people_raw", []):
        owned = [d for d in s["deadlines"] if d.get("owner") == p["id"]]
        people[p["id"]]["members"].append(dict(member=mid, path=p.get("path"), role=p.get("role"),
                                               in_flight=p.get("in_flight_milestones") or [],
                                               owned_deadlines=[d["ref"] for d in owned]))
        people[p["id"]]["next_90d"] += len(owned)
    idx["people"] = [dict(person=k, **v) for k, v in sorted(people.items())]
    idx["deadlines"].sort(key=lambda x: x["date"])
    idx["activity"].sort(key=lambda x: str(x.get("ts")))
    idx["tags"] = [dict(tag=k, count=len(v), entities=v) for k, v in sorted(tags.items(), key=lambda kv: (-len(kv[1]), kv[0]))]

    stamp = dict(compiled_at=iso(run.now), from_collect=iso(run.now))
    for kind in ("members", "milestones", "risks", "decisions", "people", "deadlines", "documents", "tags"):
        run.write(f"portfolio/index/{kind}.yaml", f"# portfolio/index/{kind}.yaml — DERIVED by portfolio-collector. Do not edit.\n"
                  + ydump(dict(**stamp, rows=idx[kind])))
    run.write(f"portfolio/index/activity-{run.activity_window}d.ndjson",
              "".join(json.dumps(a, default=str) + "\n" for a in idx["activity"]))
    counts = {k: len(idx[k]) for k in ("members", "milestones", "risks", "decisions", "people", "deadlines", "documents", "tags", "activity")}
    run.log("portfolio.index.compiled", f"index compiled: " + ", ".join(f"{v} {k}" for k, v in counts.items()), counts)
    return dict(counts=counts, idx=idx)


# ── registry, checks ─────────────────────────────────────────────────────────
def checks_for(run: Run, m: dict, s: dict | None, cursor: dict) -> list[dict]:
    out = []
    if m.get("status") not in ACTIVE_STATUSES:
        return out
    if cursor.get("reachable") is False:
        out.append(dict(id="portfolio.member-unreachable", severity="urgent", member=m["id"], reason=cursor.get("reason")))
        return out
    if not s:
        return out
    if m.get("status") == "active":
        last = parse_ts(s["activity"]["last_event_at"])
        silent = (run.now - last).days if last else None
        if silent is None or silent >= run.silence_days:
            out.append(dict(id="portfolio.member-silent", severity="soon", member=m["id"], days=silent))
        for sf in s["harvest"]["surfaces"]:
            if sf["cursor_age_days"] is not None and sf["cursor_age_days"] > run.stale_days:
                out.append(dict(id="portfolio.harvest-stale", severity="soon", member=m["id"], surface=sf["surface"], days=sf["cursor_age_days"]))
    return out


def compile_registry(run: Run, members: list[dict], latest: dict, checks: list[dict]) -> dict:
    rows = []
    for m in members:
        s = latest.get(m["id"])
        row = dict(id=m["id"], name=m.get("name"), status=m.get("status"), member_kind=m.get("member_kind"), priority=m.get("priority"),
                   owner=m.get("owner"), source_row=m.get("source_row"), added=str(m.get("added") or ""))
        if s:
            row.update(current_phase=s["project"]["current_phase"], milestones=f"{s['milestones']['complete']}/{s['milestones']['total']}",
                       at_risk=s["milestones"]["at_risk"] + s["milestones"]["blocked"], open_risks=s["risks"]["open"],
                       top_risk=(f"{s['risks']['high'][0]['id']} ({s['risks']['high'][0]['score']})" if s["risks"]["high"] else None),
                       pending_decisions=len(s["decisions"]["pending"]),
                       next_deadline=({k: s["deadlines"][0][k] for k in ("date", "label", "owner")} if s["deadlines"] else None),
                       last_event_at=s["activity"]["last_event_at"], events_7d=s["activity"]["events_7d"],
                       harvest_worst_age=max((x["cursor_age_days"] or 0 for x in s["harvest"]["surfaces"]), default=None),
                       last_snapshot=s["captured_at"][:10], reachable=True)
        else:
            cur = run.state["cursors"].get(m["id"]) or {}
            row.update(reachable=cur.get("reachable"), last_snapshot=cur.get("last_snapshot"))
        row["checks"] = [c["id"] for c in checks if c["member"] == m["id"]]
        if m.get("status") == "proposed":
            row["days_waiting"] = days_between(parse_date(m.get("added")), run.today)
        rows.append(row)
    reg = dict(compiled_at=iso(run.now), from_collect=iso(run.now), members=rows,
               counts=dict(Counter(m.get("status") for m in members)),
               checks=checks)
    run.write("portfolio/registry.yaml", "# portfolio/registry.yaml — DERIVED by portfolio-collector. Do not edit; edit the member row.\n" + ydump(reg))
    run.log("portfolio.registry.compiled", f"registry compiled: {len(rows)} members", reg["counts"])
    return reg


# ── understanding page ───────────────────────────────────────────────────────
def n(x) -> str:
    return "none" if x in (None, "", []) else str(x)


def understanding_page(run: Run, m: dict, s: dict, prev: dict | None, deps: list[dict], index: dict) -> str:
    p, ms, rk, dc, act, hv = s["project"], s["milestones"], s["risks"], s["decisions"], s["activity"], s["harvest"]
    L = []
    L.append("---")
    L.append(ydump(dict(kind="portfolio-understanding", member=m["id"], as_of=s["captured_at"][:10], source_rev=s["source_rev"],
                        regenerated_by="portfolio-collector", regenerable=True)).rstrip())
    L.append("---\n")
    L.append(f"# {m.get('name') or m['id']} — what we understand\n")
    L.append(f"*As of {s['captured_at'][:10]} (rev {n(s['source_rev'])}). Every line cites the member file it came from. Regenerated on each collect; do not edit.*\n")
    one = p.get("one_liner") or ""
    L.append(f"**What it is.** {one + ' ' if one else ''}Kind: {n(p.get('kind'))}; packs: {', '.join(p.get('packs_loaded') or []) or 'none'}; capabilities: {', '.join(p.get('capabilities_enabled') or []) or 'none'}. `manifest.yaml`\n")
    at_risk = [x for x in ms["next_due"] if x["status"] in ("at_risk", "blocked")]
    nxt = ms["next_due"][0] if ms["next_due"] else None
    L.append(f"**Where it is.** Phase {n(p.get('current_phase'))}. {ms['complete']} of {ms['total']} milestones complete; {ms['in_progress'] + ms['at_risk'] + ms['blocked']} in flight"
             + (f", {len(at_risk)} at risk or blocked ({', '.join(x['id'] for x in at_risk)})" if at_risk else "")
             + (f", {ms['overdue']} overdue" if ms["overdue"] else "")
             + (f". Next due: {nxt['id']} on {nxt['planned_end']} ({nxt['status']})." if nxt and nxt["planned_end"] else ".")
             + " `state.json`, `milestones/`\n")
    if s.get("read_copy") and s["read_copy"] != "home":
        what = "its Published mirror in the cloud" if s["read_copy"] == "mirror" else "the copy left on disk when it moved to the cloud"
        L.append(f"**Read from a copy.** The home copy did not answer ({s.get('home_unreachable') or 'unreachable'}); this page reads {what}, "
                 f"as of {n(s.get('copy_as_of'))}. Anything newer at home is not here.\n")
    who = []
    for pp in s["people"]:
        load = f"{len(pp['in_flight_milestones'])} in flight" if pp["in_flight_milestones"] else "nothing in flight"
        who.append(f"{pp.get('name') or pp['id']} ({pp.get('role') or 'role not recorded'}; {load})")
    L.append(f"**Who.** {'; '.join(who) if who else 'no people recorded'}. `people/`\n")
    L.append("**What is open.**")
    for x in rk["high"]:
        L.append(f"- Risk {x['id']}, score {n(x['score'])}: {n(x['title'])}. `{x['path']}`")
    for x in dc["pending"]:
        L.append(f"- Decision pending: {n(x['title'])}" + (f", needed by {x['needed_by']}" if x.get("needed_by") else "") + f". `{x['path']}`")
    if hv["inbox"]["untriaged"]:
        L.append(f"- {hv['inbox']['untriaged']} inbox document(s) untriaged. `documents/index.yaml`")
    if not rk["high"] and not dc["pending"] and not hv["inbox"]["untriaged"]:
        L.append("- nothing above the line: no high risks, no pending decisions, inbox triaged.")
    L.append("")
    if prev and "_unchanged_since" in prev:
        L.append(f"**What changed since the last collect.** Nothing — the member's files are unchanged since the collect of {prev['_unchanged_since'][:10]}. {act['events_7d']} events in 7 days. `logs/activity.ndjson`\n")
    elif prev:
        moved = []
        pm = {x["id"]: x for x in prev["milestones"]["next_due"]}
        for x in ms["next_due"]:
            q = pm.get(x["id"])
            if q and (q["status"] != x["status"] or q.get("percent_complete") != x.get("percent_complete")):
                moved.append(f"{x['id']} {n(q.get('percent_complete'))}% {q['status']} → {n(x.get('percent_complete'))}% {x['status']}")
        new_risks = [x["id"] for x in rk["high"] if x["id"] not in {y["id"] for y in prev["risks"]["high"]}]
        new_dec = [x["id"] for x in dc["recent"] if x["id"] not in {y["id"] for y in prev["decisions"]["recent"]}]
        bits = (moved + [f"new risk {i}" for i in new_risks] + [f"decision recorded {i}" for i in new_dec]) or ["no milestone, risk or decision movement"]
        L.append(f"**What changed since the last collect ({prev['captured_at'][:10]}).** {'; '.join(bits)}. {act['events_7d']} events in 7 days. `logs/activity.ndjson {prev['captured_at']} → {s['captured_at']}`\n")
    else:
        L.append(f"**What changed since the last collect.** First collect — nothing to compare. {act['events_7d']} events in 7 days. `logs/activity.ndjson`\n")
    mine = [d for d in deps if m["id"] in (d.get("from", {}).get("member"), d.get("to", {}).get("member"))]
    if mine:
        L.append("**What it depends on and what depends on it.** " + "; ".join(
            f"{d['id']}: {d['from']['member']}{(' ' + str(d['from'].get('ref'))) if d['from'].get('ref') else ''} {d.get('type')} {d['to']['member']}{(' ' + str(d['to'].get('ref'))) if d['to'].get('ref') else ''} ({d.get('status')})"
            for d in mine) + ". `portfolio/dependencies/`\n")
    else:
        L.append("**What it depends on and what depends on it.** No dependencies declared. `portfolio/dependencies/`\n")
    if hv["surfaces"]:
        L.append("**Harvest.** " + " · ".join(f"{x['surface']} {n(x['cursor_age_days'])} d" for x in hv["surfaces"])
                 + (" — current." if all((x["cursor_age_days"] or 0) <= run.stale_days for x in hv["surfaces"]) else " — stale surfaces present.") + " `harvest/cursors/`\n")
    else:
        L.append("**Harvest.** No harvest cursors recorded — this member has not harvested. `harvest/cursors/`\n")
    shared = [t for t in index["idx"]["tags"] if any(e["member"] == m["id"] for e in t["entities"]) and len({e["member"] for e in t["entities"]}) > 1]
    if shared:
        L.append("**Words this project uses that others also use.** " + " · ".join(
            f"{t['tag']} (also {', '.join(sorted({e['member'] for e in t['entities']} - {m['id']}))})" for t in shared[:8]) + ". `portfolio/index/tags.yaml`\n")
    else:
        L.append("**Words this project uses that others also use.** None shared yet. `portfolio/index/tags.yaml`\n")
    L.append("---")
    L.append(f"_Cited paths are relative to the member's `project-state/`. To ask something this page does not answer: `/portfolio-reviewer query \"…\" --member {m['id']}`._\n")
    return "\n".join(L)


# ── weekly change note ───────────────────────────────────────────────────────
def week_note(run: Run, members: list[dict], latest: dict, prevs: dict, checks: list[dict], index: dict, findings: list[dict]) -> str:
    L = ["---", ydump(dict(kind="portfolio-week", week_ending=str(run.today), from_collect=iso(run.now),
                            members_collected=len(latest), members_unreachable=sum(1 for c in checks if c["id"] == "portfolio.member-unreachable"),
                            checks_fired=sorted({c["id"] for c in checks}), generated_by="portfolio-collector")).rstrip(), "---\n",
         f"# {run.portfolio_name} — what changed, week ending {run.today}\n"]
    active = [m for m in members if m.get("status") in ACTIVE_STATUSES]
    proposed = [m for m in members if m.get("status") == "proposed"]
    L.append(f"**{len(active)} members collected · {len(proposed)} proposed in the hopper · checks fired: {len(checks)}.**\n")
    L.append("## By member\n")
    for m in active:
        s = latest.get(m["id"]); prev = prevs.get(m["id"])
        if not s:
            cur = run.state["cursors"].get(m["id"]) or {}
            L.append(f"**{m['id']}** — unreachable ({cur.get('reason')}).\n"); continue
        ms = s["milestones"]
        L.append(f"**{m['id']}** · {n(s['project']['current_phase'])} · {ms['complete']}/{ms['total']} · {s['activity']['events_7d']} events")
        bits = []
        if prev and "_unchanged_since" in prev:
            # an unchanged member with one snapshot in its history: the collect keeps a marker, not a snapshot, as the
            # previous (collect_member). Found 2026-09-29 by the cloud scheduler's second weekly collect: this read
            # prev["milestones"] from the marker and the whole collect failed.
            bits.append(f"- unchanged since {str(prev['_unchanged_since'])[:10]}")
        elif prev:
            pm = {x["id"]: x for x in prev["milestones"]["next_due"]}
            for x in ms["next_due"]:
                q = pm.get(x["id"])
                if q and (q["status"] != x["status"] or q.get("percent_complete") != x.get("percent_complete")):
                    bits.append(f"- {x['id']} {n(q.get('percent_complete'))}% → {n(x.get('percent_complete'))}%, {x['status']}. `{x['path']}`")
            for x in s["risks"]["high"]:
                if x["id"] not in {y["id"] for y in prev["risks"]["high"]}:
                    bits.append(f"- New risk {x['id']} (score {n(x['score'])}): {n(x['title'])}. `{x['path']}`")
            for x in s["decisions"]["recent"]:
                if x["id"] not in {y["id"] for y in prev["decisions"]["recent"]}:
                    bits.append(f"- Decision recorded: {n(x['title'])}. `{x['path']}`")
        for x in s["decisions"]["pending"]:
            bits.append(f"- Decision still pending: {n(x['title'])}" + (f", needed by {x['needed_by']}" if x.get("needed_by") else "") + f". `{x['path']}`")
        for c in checks:
            if c["member"] == m["id"]:
                bits.append(f"- **Check fired: {c['id'].split('.')[-1]}**" + (f" ({c.get('surface')}, {c.get('days')} d)" if c.get("surface") else (f" ({c.get('days')} d)" if c.get("days") is not None else "")) + ".")
        L.extend(bits or ["- no movement recorded"]); L.append("")
    L.append("## Across members\n")
    soon = [d for d in index["idx"]["deadlines"] if parse_date(d["date"]) and 0 <= (parse_date(d["date"]) - run.today).days <= 14]
    L.append(f"- Deadlines in the next 14 days: {len(soon)}" + (" — " + "; ".join(f"{d['date']} {d['member']} {d['label']} ({n(d.get('owner'))})" for d in soon) if soon else "") + ". `portfolio/index/deadlines.yaml`")
    moved = [f for f in findings if str(f.get("last_seen") or "") >= str(run.today - dt.timedelta(days=7))]
    L.append(f"- Findings that moved this week: {len(moved)}" + (" — " + "; ".join(f"{f['id']} {f.get('type')} ({f.get('status')})" for f in moved) if moved else "") + ".")
    L.append("- Hopper: " + ("; ".join(f"{m['id']} waiting {n(days_between(parse_date(m.get('added')), run.today))} d" for m in proposed) if proposed else "empty") + ".\n")
    c = index["counts"]
    L.append("## Index\n")
    L.append("Recompiled " + iso(run.now) + ": " + " · ".join(f"{v} {k}" for k, v in c.items()) + ".\n")
    L.append("---\n_Generated by the weekly collect. To ask anything this does not answer: `/portfolio-reviewer query \"…\"`._\n")
    return "\n".join(L)


# ── main ─────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target", nargs="?", default="all")
    ap.add_argument("--portfolio")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--week", action="store_true")
    ap.add_argument("--as-of")
    ap.add_argument("--actor", default=ACTOR_DEFAULT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--transport", choices=["auto", "mcp", "files"], default="auto")
    ap.add_argument("--core", action="store_true", help="Core only: member rows, snapshots, the registry (the paid outputs are skipped)")
    args = ap.parse_args(argv)
    run = Run(args)
    # the paid outputs (decision 2026-09-27-capability-entitlements): the cloud server decides for its own collect
    # (--core); a local install decides offline, and is not checked while it trusts no key
    ent = {"enforced": False, "entitled": True} if run.server_side else entitlement_status("portfolio", Path(__file__), str(run.today))
    core = args.core or not ent["entitled"]
    PAID = ["index", "understanding pages", "at-a-glance", "weekly note", "finding lineage"]
    if core:
        run.log("portfolio.collect.core", "Core collect: " + ", ".join(PAID) + " skipped",
                dict(skipped=PAID, reason="--core" if args.core else ent.get("reason")))

    members = load_members(run)
    if not members and str(run.cap.get("discovery", "auto")) != "auto":
        die("portfolio/members/ is empty — run /portfolio-onboarding first")
    # an empty registry with discovery on is the app's fresh-enable state: propose what is under the
    # workspace, write nothing else, and tell the operator to activate rows (onboarding's job)
    targets = [m for m in members if (args.target == "all" and m.get("status") in ACTIVE_STATUSES) or m["id"] == args.target]
    if args.target != "all" and not targets:
        die(f"no member row {args.target!r}")

    latest: dict[str, dict] = {}
    prevs: dict[str, dict] = {}
    raw: dict[str, dict] = {}
    became_edges: list[dict] = []

    # snapshots per member, oldest → newest (for "what changed" and the unchanged short-circuit)
    def snapshots(mid: str) -> list[dict]:
        d = run.ps / "portfolio" / "snapshots" / mid
        # by day, then the day's first file before its -HHMM re-collects ("-" sorts before ".", so plain name order
        # put 2026-09-22-0530.yaml before 2026-09-22.yaml and made the older one "latest")
        files = sorted(d.glob("*.yaml"), key=lambda f: (f.stem[:10], len(f.stem), f.stem)) if d.exists() else []
        return [s for s in (yload(f) for f in files) if s]

    def previous_snapshot(mid: str) -> dict | None:
        s = snapshots(mid)
        return s[-1] if s else None

    for m in targets:
        mid = m["id"]
        cursor = run.state["cursors"].setdefault(mid, {})
        # the home copy first; another copy only when the home does not answer (item 3, the two-copy rule)
        src = rev = copy = None
        home_reason = home_detail = None
        for label, cand, why in copies(run, m):
            if cand is None:
                detail = run.cloud_error if why == "remote" else None
            else:
                try:
                    rev = cand.rev(); src, copy = cand, label
                    break
                except McpError as e:
                    why, detail = "remote", str(e)
            if label == "home" and home_reason is None:
                home_reason, home_detail = why, detail
        if src is None:
            reason = home_reason or "missing"
            cursor.update(reachable=False, reason=reason, checked_at=iso(run.now))
            run.log("portfolio.member.unreachable", f"{mid}: {reason}", dict(member=mid, reason=reason, **({"detail": home_detail} if home_detail else {})))
            run.summary.append(dict(member=mid, result="unreachable", reason=reason))
            continue
        copy_note = {} if copy == "home" else dict(copy=copy, copy_as_of=src.as_of(), home_unreachable=home_reason or "unreachable")
        if copy != "home":
            run.log("portfolio.member.read-from-copy", f"{mid}: {copy} ({home_reason})",
                    dict(member=mid, copy=copy, home_unreachable=home_reason, **({"detail": home_detail} if home_detail else {})))
        prev = previous_snapshot(mid)
        if prev and prev.get("source_rev") == rev and not args.force:
            # unchanged: reuse the latest snapshot for index/registry, write no new file, and compare
            # the understanding page against the snapshot BEFORE it (or say it is unchanged since it)
            hist = snapshots(mid)
            latest[mid] = prev; prevs[mid] = hist[-2] if len(hist) > 1 else {"_unchanged_since": prev["captured_at"]}
            cursor.update(reachable=True, last_source_rev=rev, checked_at=iso(run.now))
            try:
                raw[mid] = read_member(run, m, src)
            except RuntimeError as e:
                run.summary.append(dict(member=mid, result="malformed", reason=str(e))); continue
            run.summary.append(dict(member=mid, result="unchanged", rev=rev, via=src.via, **copy_note))
            continue
        try:
            r = read_member(run, m, src)
            r.update(copy=copy, copy_as_of=copy_note.get("copy_as_of"), home_unreachable=copy_note.get("home_unreachable"))
        except RuntimeError as e:
            cursor.update(reachable=False, reason="malformed", checked_at=iso(run.now))
            run.log("portfolio.member.unreachable", f"{mid}: malformed", dict(member=mid, reason="malformed", detail=str(e)))
            run.summary.append(dict(member=mid, result="unreachable", reason="malformed")); continue
        snap = build_snapshot(run, m, rev, r)
        became_edges += [dict(member=mid, **e) for e in snap.pop("_became")]
        day = str(run.today)
        rel = f"portfolio/snapshots/{mid}/{day}.yaml"
        if (run.ps / rel).exists() and (yload(run.ps / rel) or {}).get("source_rev") != rev:
            rel = f"portfolio/snapshots/{mid}/{day}-{run.now.strftime('%H%M')}.yaml"
        run.write(rel, "# portfolio-snapshot — written by portfolio-collector; never edited.\n" + ydump(snap))
        cursor.update(reachable=True, last_snapshot=day, last_source_rev=rev, checked_at=iso(run.now))
        cursor.pop("reason", None)
        run.log("portfolio.snapshot.captured", f"{mid} @ {rev}", dict(member=mid, source_rev=rev, reachable=True))
        latest[mid] = snap; prevs[mid] = prev; raw[mid] = r
        run.summary.append(dict(member=mid, result="snapshot", rev=rev, via=src.via, path=rel, **copy_note))

    # members not targeted this run still appear in the index/registry from their latest snapshot
    for m in members:
        if m["id"] not in latest and m.get("status") in ACTIVE_STATUSES:
            prev = previous_snapshot(m["id"])
            if prev:
                latest[m["id"]] = prev

    # after the loop, in order (Core: the registry and checks only; nothing already written is removed)
    index = {"counts": {}} if core else compile_index(run, members, latest, raw)
    checks = []
    for m in members:
        checks += checks_for(run, m, latest.get(m["id"]), run.state["cursors"].get(m["id"]) or {})
    compile_registry(run, members, latest, checks)

    deps = [d for _, d in read_dir(run.ps, "portfolio/dependencies")]
    for m in ([] if core else members):
        s = latest.get(m["id"])
        if s and m.get("status") in ACTIVE_STATUSES:
            run.write(f"portfolio/understanding/{m['id']}.md", understanding_page(run, m, s, prevs.get(m["id"]), deps, index))
            run.log("portfolio.understanding.generated", m["id"], dict(member=m["id"], path=f"portfolio/understanding/{m['id']}.md"))

    # "at a glance" — the report the app renders in place (surfaces.yaml → reports). Every paid collect.
    try:
        if core:
            raise StopIteration
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from render_glance import render as render_glance
        page = render_glance(run, members, latest, prevs, checks, index)
        run.write("portfolio/reports/at-a-glance.html", page)
        run.write(f"portfolio/reports/at-a-glance-{run.today}.html", page)
        run.log("portfolio.report.generated", "portfolio/reports/at-a-glance.html", dict(kind="at-a-glance", path="portfolio/reports/at-a-glance.html"))
    except StopIteration:
        pass
    except Exception as e:  # the report is derived; a render failure must not fail the collect
        print(f"warn: at-a-glance render failed: {e}", file=sys.stderr)

    findings = [f for _, f in read_dir(run.ps, "portfolio/findings")]
    if args.week and not core:
        rel = f"portfolio/reports/week-{run.today}.md"
        run.write(rel, week_note(run, members, latest, prevs, checks, index, findings))
        run.log("portfolio.report.generated", rel, dict(kind="week", path=rel))

    # discovery: the workspace registry's projects within reach first (as registry rows, which keep resolving
    # when a folder moves), then its cloud projects (as server rows; one with a copy on this disk is left to
    # that copy), then any */project-state/ under workspace_root the registry does not list
    proposed_new = []
    if str(run.cap.get("discovery", "auto")) == "auto":
        known, ids = set(), {m["id"] for m in members}
        refs = {str((m.get("location") or {}).get("ref")) for m in members if (m.get("location") or {}).get("ref")}
        for m in members:
            p, _ = member_path(run, m)
            if p:
                known.add(p.resolve())

        def propose(mid: str, ps: Path | None, location: dict, where: str, name: str | None = None):
            name = name or (((yload(ps / "manifest.yaml") or {}).get("project") or {}).get("name") if ps else None) or mid
            row = dict(id=mid, kind="portfolio-member", name=name, member_kind="other", status="proposed", priority="P3",
                       owner=None, location=location, relationship="", tags=[], source_row="discovery", added=str(run.today),
                       retired=None, notes=f"discovered {run.today} {where}; activate to collect",
                       created=iso(run.now), created_by=args.actor, last_modified=iso(run.now), last_modified_by=args.actor)
            run.write(f"portfolio/members/{mid}.yaml", ydump(row))
            run.log("portfolio.member.added", f"{mid} proposed by discovery", dict(member=mid, status="proposed", source="discovery"))
            proposed_new.append(mid); ids.add(mid)
            if ps:
                known.add(ps.resolve())
            if location.get("ref"):
                refs.add(location["ref"])

        for row in registry_rows():
            if row.get("archived") or row.get("stateType") not in (None, "project-state") or not row.get("project"):
                continue
            ref = f"{row.get('org')}/{row.get('project')}"
            ps = registry_folder(ref)
            mid = slug(str(row["project"]))
            if not ps or ps.resolve() == run.ps.resolve() or ps.resolve() in known or mid in ids:
                continue
            try:
                ps.relative_to(run.workspace_root)
            except ValueError:
                continue  # outside the portfolio's reach
            propose(mid, ps, dict(type="registry", ref=ref), "in the workspace registry")
        for row in registry_cloud_rows():
            ref = str(row.get("ref") or "")
            if not ref or row.get("archived") or row.get("copy_on_disk") or ref in refs:
                continue
            mid = slug(ref.rsplit("/", 1)[-1])
            if mid in ids:
                continue
            propose(mid, None, dict(type="server", ref=ref), "in the workspace registry's cloud list", name=row.get("name"))
        for cand in (sorted(run.workspace_root.iterdir()) if run.workspace_root.is_dir() else []):
            ps = cand / "project-state"
            if not (ps / "manifest.yaml").exists():
                continue
            if ps.resolve() == run.ps.resolve() or ps.resolve() in known or cand.name in ids:
                continue
            propose(cand.name, ps, dict(type="local", path=os.path.relpath(ps, run.ps), remote=None), "under workspace_root")

    # lineage: findings cited by member entities
    for e in ([] if core else became_edges):
        fp = run.ps / "portfolio" / "findings" / f"{e['finding']}.yaml"
        f = yload(fp)
        if not f:
            continue
        edges = f.setdefault("became", []) or []
        if not any(x.get("member") == e["member"] and x.get("entity") == e["entity"] for x in edges):
            edges.append(dict(member=e["member"], entity=e["entity"], at=iso(run.now), kind="accepted"))
            f["became"] = edges
            run.write(f"portfolio/findings/{e['finding']}.yaml", ydump(f))

    # state + log
    run.state["last_collect"] = iso(run.now)
    run.state["last_index"] = iso(run.now)
    run.write("state/portfolio.json", json.dumps(run.state, indent=2) + "\n")
    if not args.dry_run:
        with open(run.ps / "logs" / "activity.ndjson", "a", encoding="utf-8") as f:
            for line in run.events:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

    run.close()
    out = dict(portfolio=str(run.ps), as_of=str(run.today), dry_run=args.dry_run, core=core, **({"skipped": PAID} if core else {}), members=run.summary,
               checks=checks, index=index["counts"], discovered=proposed_new, writes=len(run.writes), events=len(run.events))
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"portfolio-collector — {run.portfolio_name} — as of {run.today}{' (dry run)' if args.dry_run else ''}")
        for s in run.summary:
            print(f"  {s['member']:<24} {s['result']:<11} {s.get('rev') or s.get('reason') or ''}" + (f"  via {s['via']}" if s.get("via") else "")
                  + (f"  from the {s['copy']} (home: {s['home_unreachable']}; copy as of {s.get('copy_as_of')})" if s.get("copy") else ""))
        print("  index: " + ", ".join(f"{v} {k}" for k, v in index["counts"].items()))
        for c in checks:
            print(f"  check {c['id']:<30} {c['member']}" + (f" {c.get('surface')}" if c.get("surface") else "") + (f" {c.get('days')} d" if c.get("days") is not None else ""))
        if proposed_new:
            print("  discovered → proposed: " + ", ".join(proposed_new))
        print(f"  {len(run.writes)} file(s) written, {len(run.events)} event(s) logged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
