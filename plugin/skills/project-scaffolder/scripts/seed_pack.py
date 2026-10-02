#!/usr/bin/env python3
"""Seed a facility from its loaded packs, and adopt the seeds an operator approved.

WHY THIS IS A SCRIPT
--------------------
Bundled pack seeds describe starting milestones and risks whose due
dates are *date expressions* (`anchor-120d`, `end-1w`, `50%`). Resolving those is arithmetic, and
arithmetic done by prose drifts - the same reason check-pack-integrity.py exists. So the three
mechanical steps live here, and project-scaffolder's `seed-pack` / `adopt-seeds` operations call it:

  seed    1. merge every loaded pack's reporting-matrix-defaults into reporting-matrix.yaml
             (an id that already exists is left alone - an operator's edit outranks a pack default)
          2. queue one DRAFT card per pack per seed kind (milestones, risks) into outbox/queue/,
             with every date expression already resolved against the manifest
  adopt   3. once the operator has approved a card (moved it to outbox/approved/), write each
             proposed entity as milestones/M<NN>-<slug>.yaml or risks/R-<NN>-<slug>.yaml
  reanchor 4. when the event or launch date moves, move the seeded milestones that nobody has
             re-dated by hand, and leave every other one exactly as it is

KPI seeds are never written here: route them through `project-goal-tracker`.
Capability packs are skipped: their own enable step seeds them.

Review-not-author: nothing in step 2 becomes a live entity until a human approves the card, and the
card's artifact is the source adopt reads - so an operator who edits a date in the draft gets their
date, not the pack's.

USAGE
-----
    seed_pack.py seed  --state <project-state dir> [--today YYYY-MM-DD] [--dry-run] [--no-matrix | --no-seeds]
    seed_pack.py adopt --state <project-state dir> --card <card-id>
    seed_pack.py reanchor --state <project-state dir> [--dry-run]   (after start/end/anchor dates move)
    common: [--packs-root <repo or plugin root>] [--actor <email>] [--json]
"""
import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR  pyyaml is required (pip install pyyaml)")
    sys.exit(1)

DEFAULT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATE_EXPR = re.compile(r"^(?:(start|end|anchor)(?:([+-])(\d+)([dw]))?|(\d{1,3})%)$")
SEED_KINDS = ("milestones", "risks")  # kpis are offered through project-goal-tracker
LEVEL = {"low": 1, "medium": 2, "high": 3}
PAYLOAD_MARK = "<!-- seed-payload: adopt reads the YAML block below; edit it to change what is written -->"


# ── small io helpers ──────────────────────────────────────────────────────────
def ry(path):
    with io.open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def wtext(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def dump(obj):
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=100)


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(state, event, actor, **detail):
    line = {"ts": now_iso(), "actor": actor, "skill": "project-scaffolder", "event": event}
    line.update(detail)
    os.makedirs(os.path.join(state, "logs"), exist_ok=True)
    with io.open(os.path.join(state, "logs", "activity.ndjson"), "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", v.strip()):
        return dt.date.fromisoformat(v.strip())
    return None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


# ── date expressions (PACK-SPEC, project-types fields) ────────────────────────
def resolve_due(expr, start, end, anchor):
    """Return (date | None, missing-reason | None). Pure; the tests pin it."""
    m = DATE_EXPR.match(str(expr).strip()) if expr is not None else None
    if not m:
        return None, f"not a date expression: {expr!r}"
    base_name, sign, n, unit, pct = m.groups()
    if pct is not None:
        if not (start and end):
            return None, "needs project.start_date and project.end_date"
        span = (end - start).days
        return start + dt.timedelta(days=round(span * int(pct) / 100)), None
    base = {"start": start, "end": end, "anchor": anchor}[base_name]
    if base is None:
        field = {"start": "project.start_date", "end": "project.end_date",
                 "anchor": "phases.anchor_date"}[base_name]
        return None, f"needs {field}"
    days = int(n or 0) * (7 if unit == "w" else 1)
    return base + dt.timedelta(days=-days if sign == "-" else days), None


def manifest_dates(manifest):
    proj, phases = manifest.get("project") or {}, manifest.get("phases") or {}
    return {"start": as_date(proj.get("start_date")), "end": as_date(proj.get("end_date")),
            "anchor": as_date(phases.get("anchor_date"))}


def _iso(d):
    return d.isoformat() if d else "null"


def seed_basis_lines(expr, basis):
    return (f"seed_due: '{expr}'\n"
            f"seed_basis: {{start: {_iso(basis['start'])}, end: {_iso(basis['end'])}, "
            f"anchor: {_iso(basis['anchor'])}}}\n")


# ── pack discovery ────────────────────────────────────────────────────────────
def find_pack(root, pid):
    for cand in [os.path.join(root, "packs", pid)] + glob.glob(
        os.path.join(root, "capabilities", "*", "packs", pid)
    ):
        if os.path.exists(os.path.join(cand, "manifest.yaml")):
            return cand
    return None


def ordered_packs(manifest):
    """Primary work pack (project.kind) first, then packs_loaded in order, de-duplicated."""
    proj = manifest.get("project") or {}
    loaded = proj.get("packs_loaded") or manifest.get("packs_loaded") or []
    if isinstance(loaded, str):
        loaded = [loaded]
    kind = proj.get("kind")
    order = ([kind] if kind in loaded else []) + [p for p in loaded if p != kind]
    return [str(p) for p in order]


def matrix_defaults(pack_dir):
    path = os.path.join(pack_dir, "reporting-matrix-defaults.yaml")
    if not os.path.exists(path):
        return []
    data = ry(path) or {}
    out = []
    for e in (data.get("defaults") or []) + (data.get("entries") or []):
        if isinstance(e, dict):
            out.append(dict(e))
    for g in data.get("stakeholder_groups") or []:
        for e in (g or {}).get("reports") or []:
            if isinstance(e, dict):
                out.append({"stakeholder_group": g.get("id"), **e})
    return out


# ── step 1: matrix merge ──────────────────────────────────────────────────────
MATRIX_HEADER = """# Stakeholder reporting matrix. Seeded from loaded packs by project-scaffolder seed-pack;
# customise freely - a re-seed never overwrites an entry whose id already exists.
schema_version: 2
manifest_kind: reporting_matrix

entries:
"""
ENTRY_KEYS = ["id", "stakeholder_group", "report", "cadence", "active_phases", "format", "surface",
              "generator", "profile", "description"]


def merge_matrix(state, packs, dry_run):
    path = os.path.join(state, "reporting-matrix.yaml")
    text = io.open(path, encoding="utf-8").read() if os.path.exists(path) else MATRIX_HEADER
    existing = {str(e.get("id")) for e in ((yaml.safe_load(text) or {}).get("entries") or [])
                if isinstance(e, dict) and e.get("id")}
    added = []
    for pid, pdir, _ in packs:
        for e in matrix_defaults(pdir):
            eid = str(e.get("id") or slug(e.get("report") or ""))
            if not eid or eid in existing:
                continue
            entry = {"id": eid}
            for k in ENTRY_KEYS[1:]:
                if e.get(k) is not None:
                    entry[k] = e[k]
            if e.get("skill") and "generator" not in entry:
                entry["generator"] = e["skill"]
            # `optional: true` in a pack default means opt-in ("if the team wants it"): seed it
            # present but switched off, so a re-seed never starts a report nobody asked for.
            entry["enabled"] = not bool(e.get("optional"))
            entry["seeded_from"] = pid
            existing.add(eid)
            added.append(entry)
    if added and not dry_run:
        block = "".join("\n" + "\n".join(("  - " if i == 0 else "    ") + l
                                        for i, l in enumerate(dump(e).rstrip("\n").split("\n"))) + "\n"
                        for e in added)
        lines = text.split("\n")
        at = next((i for i, l in enumerate(lines) if re.match(r"^entries:\s*(\[\s*\])?\s*$", l)), None)
        if at is None:
            text = text.rstrip("\n") + "\n\nentries:\n" + block
        else:
            lines[at] = "entries:"
            # insert before the next top-level key after entries:, else at the end
            nxt = next((j for j in range(at + 1, len(lines)) if re.match(r"^[A-Za-z_]", lines[j])), None)
            if nxt is None:
                text = "\n".join(lines).rstrip("\n") + "\n" + block
            else:
                text = "\n".join(lines[:nxt]).rstrip("\n") + "\n" + block + "\n" + "\n".join(lines[nxt:])
        yaml.safe_load(text)  # never write a matrix that does not parse
        wtext(path, text)
    return added


# ── step 2: seed cards ────────────────────────────────────────────────────────
def outbox_ids(state):
    ids, seeded = set(), set()
    for lane in ("queue", "approved", "dismissed", "sent"):
        for mf in glob.glob(os.path.join(state, "outbox", lane, "*.meta.yaml")):
            try:
                m = ry(mf) or {}
            except Exception:
                continue
            ids.add(m.get("id") or os.path.basename(mf)[: -len(".meta.yaml")])
            s = m.get("seed") or {}
            if s.get("pack") and s.get("kind"):
                seeded.add((s["pack"], s["kind"]))
    return ids, seeded


def build_entities(kind, items, start, end, anchor):
    ents, missing = [], []
    for it in items:
        e = {"slug": it.get("slug"), "title": it.get("title")}
        if kind == "milestones":
            due, why = resolve_due(it.get("due"), start, end, anchor)
            e["due"] = due.isoformat() if due else None
            e["due_expression"] = str(it.get("due"))
            if why:
                missing.append(f"{it.get('slug')}: {why}")
            for k in ("phase", "acceptance", "owner_role", "owner"):
                if it.get(k):
                    e[k] = it[k]
        else:
            for k in ("likelihood", "impact", "mitigation", "contingency"):
                if it.get(k):
                    e[k] = it[k]
        ents.append(e)
    return ents, missing


def card_markdown(label, pid, kind, ents, missing):
    noun = "milestones" if kind == "milestones" else "risks"
    out = [f"# Starting {noun} for {label} — review", "",
           f"The `{pid}` pack proposes these {noun} for this project. Nothing is live yet.", "",
           "Edit the YAML block at the bottom to change a date, reword a title, or delete a row;",
           "then approve the card. `project-scaffolder adopt-seeds` writes exactly what the block says.", ""]
    if kind == "milestones":
        out += ["| Milestone | Due | Phase | Done when |", "|---|---|---|---|"]
        for e in ents:
            out.append(f"| {e['title']} | {e.get('due') or '— (' + e['due_expression'] + ')'} | "
                       f"{e.get('phase', '')} | {e.get('acceptance', '')} |")
    else:
        out += ["| Risk | Likelihood | Impact | Mitigation |", "|---|---|---|---|"]
        for e in ents:
            out.append(f"| {e['title']} | {e.get('likelihood', '')} | {e.get('impact', '')} | "
                       f"{e.get('mitigation', '')} |")
    if missing:
        out += ["", "**Undated:** these rows could not be dated because a date is missing from the manifest.",
                "Set it and re-seed, or type the date into the block below:", ""]
        out += [f"- {m}" for m in missing]
    out += ["", PAYLOAD_MARK, "", "```yaml", dump({kind: ents}).rstrip("\n"), "```", ""]
    return "\n".join(out)


def seed(args):
    state = os.path.abspath(args.state)
    manifest = ry(os.path.join(state, "manifest.yaml")) or {}
    proj, phases = manifest.get("project") or {}, manifest.get("phases") or {}
    start, end = as_date(proj.get("start_date")), as_date(proj.get("end_date"))
    anchor = as_date(phases.get("anchor_date"))
    today = as_date(args.today) or dt.date.today()

    packs, skipped = [], []
    for pid in ordered_packs(manifest):
        pdir = find_pack(args.packs_root, pid)
        if not pdir:
            skipped.append(f"{pid}: not found under {args.packs_root}")
            continue
        pm = ry(os.path.join(pdir, "manifest.yaml")) or {}
        if (pm.get("pack") or {}).get("axis") == "capability":
            skipped.append(f"{pid}: capability pack — seeded by the capability's enable step")
            continue
        packs.append((pid, pdir, pm))

    added = [] if args.no_matrix else merge_matrix(state, packs, args.dry_run)

    ids, seeded = outbox_ids(state)
    cards = []
    for pid, pdir, pm in ([] if getattr(args, "no_seeds", False) else packs):
        label = ((pm.get("picker") or {}).get("label") or (pm.get("pack") or {}).get("name") or pid)
        for kind in SEED_KINDS:
            spath = os.path.join(pdir, "seeds", f"{kind}.yaml")
            if not os.path.exists(spath):
                continue
            cid = f"{today.isoformat()}-seed-{pid}-{kind}"
            if cid in ids or (pid, kind) in seeded:
                skipped.append(f"{pid} {kind}: already queued or adopted")
                continue
            ents, missing = build_entities(kind, (ry(spath) or {}).get(kind) or [], start, end, anchor)
            if not ents:
                continue
            art = f"{cid}.md"
            meta = {
                "id": cid,
                "kind": "seed",
                "title": f"Starting {kind} for {label} — review ({len(ents)})",
                "produced_by": "project-scaffolder",
                "produced_at": now_iso(),
                "status": "queued",
                "surface": "none",
                "action_required": (
                    f"Review the {len(ents)} proposed {kind}. Edit or delete rows in the YAML block, then "
                    f"approve. On approval run `project-scaffolder adopt-seeds {cid}` to write them."
                ),
                "artifact": art,
                "seed": {"pack": pid, "kind": kind, "count": len(ents), "undated": len(missing)},
            }
            if not args.dry_run:
                q = os.path.join(state, "outbox", "queue")
                wtext(os.path.join(q, art), card_markdown(label, pid, kind, ents, missing))
                wtext(os.path.join(q, f"{cid}.meta.yaml"), dump(meta))
            cards.append({"id": cid, "pack": pid, "kind": kind, "count": len(ents), "undated": missing})

    if not args.dry_run and (added or cards):
        log(state, "pack.seeded", args.actor, id=f"{today.isoformat()}-seed-pack",
            summary=(f"Seeded from {', '.join(p for p, _, _ in packs) or 'no packs'}: "
                     f"{len(added)} matrix entr{'y' if len(added) == 1 else 'ies'} added, "
                     f"{len(cards)} draft card(s) queued for review."))
    return {"packs": [p for p, _, _ in packs], "matrix_added": [e["id"] for e in added],
            "cards": cards, "skipped": skipped, "dry_run": bool(args.dry_run)}


# ── step 3: adopt ─────────────────────────────────────────────────────────────
def parse_payload(md):
    at = md.find(PAYLOAD_MARK)
    m = re.search(r"```yaml\n(.*?)\n```", md[at if at >= 0 else 0:], re.S)
    if not m:
        raise SystemExit("ERROR  the card's artifact has no YAML payload block")
    return yaml.safe_load(m.group(1)) or {}


def next_number(dirpath, prefix_re):
    nums = [int(m.group(1)) for f in os.listdir(dirpath) if (m := re.match(prefix_re, f))] \
        if os.path.isdir(dirpath) else []
    return (max(nums) if nums else 0) + 1


def adopt(args):
    state = os.path.abspath(args.state)
    lanes = {lane: os.path.join(state, "outbox", lane, f"{args.card}.meta.yaml")
             for lane in ("queue", "approved", "dismissed", "sent")}
    lane = next((l for l, p in lanes.items() if os.path.exists(p)), None)
    if lane is None:
        raise SystemExit(f"ERROR  no outbox card {args.card!r}")
    if lane != "approved":
        raise SystemExit(f"ERROR  card {args.card!r} is in outbox/{lane}/ — only an approved card is adopted "
                         "(review-not-author). Approve it first.")
    meta_path = lanes["approved"]
    meta = ry(meta_path) or {}
    if meta.get("adopted_at"):
        return {"card": args.card, "written": [], "skipped": ["already adopted " + meta["adopted_at"]]}
    kind = (meta.get("seed") or {}).get("kind")
    if kind not in SEED_KINDS:
        raise SystemExit(f"ERROR  card {args.card!r} is not a seed card")
    pack = (meta.get("seed") or {}).get("pack")
    md = io.open(os.path.join(state, "outbox", "approved", meta.get("artifact") or f"{args.card}.md"),
                 encoding="utf-8").read()
    ents = parse_payload(md).get(kind) or []
    manifest = ry(os.path.join(state, "manifest.yaml")) or {}
    phase = ((manifest.get("phases") or {}).get("current_phase")
             or _state_phase(state))
    ts, today = now_iso(), dt.date.today().isoformat()
    basis = manifest_dates(manifest)

    if kind == "milestones":
        d, pre, rx = os.path.join(state, "milestones"), "M", r"^M(\d+)-"
    else:
        d, pre, rx = os.path.join(state, "risks"), "R-", r"^R-(\d+)-"
    os.makedirs(d, exist_ok=True)
    have = {re.sub(rx, "", f)[: -len(".yaml")] for f in os.listdir(d) if re.match(rx, f)}
    n = next_number(d, rx)
    written, skipped = [], []
    for e in ents:
        s = slug(e.get("slug") or e.get("title") or "")
        if not s or not e.get("title"):
            skipped.append(f"row without slug/title: {e}")
            continue
        if s in have:
            skipped.append(f"{s}: a {kind[:-1]} with this slug already exists")
            continue
        eid = f"{pre}{n:02d}-{s}"
        common = {"created": ts, "created_by": args.actor, "last_modified": ts,
                  "last_modified_by": args.actor, "phase": e.get("phase") or phase,
                  "seeded_from": pack, "seed_card": args.card}
        if kind == "milestones":
            doc = {"id": eid, "kind": "milestone", "title": e["title"],
                   "description": e.get("acceptance") or "",
                   "owner_person": e.get("owner"), "planned_start": None,
                   "planned_end": e.get("due"), "actual_start": None, "actual_end": None,
                   "percent_complete": 0, "technical_progress": "", "deliverables": [],
                   "status": "planned", "at_risk_reason": None, **common}
            ev = "milestone.created"
        else:
            li, im = e.get("likelihood") or "medium", e.get("impact") or "medium"
            doc = {"id": eid, "kind": "risk", "title": e["title"], "likelihood": li, "impact": im,
                   "score": LEVEL.get(li, 2) * LEVEL.get(im, 2), "owner": None,
                   "mitigation": e.get("mitigation") or "", "contingency": e.get("contingency") or "",
                   "status": "open", "last_reviewed": today, **common}
            ev = "risk.created"
        text = dump(doc)
        if kind == "milestones" and e.get("due_expression"):
            # What reanchor needs: the expression, and the dates it was resolved against. A
            # planned_end that no longer equals that resolution was edited by a person.
            text += seed_basis_lines(e["due_expression"], basis)
        wtext(os.path.join(d, f"{eid}.yaml"), text)
        log(state, ev, args.actor, id=eid, summary=f"Adopted from seed card {args.card} ({pack}): {e['title']}")
        have.add(s)
        written.append(eid)
        n += 1

    meta["adopted_at"], meta["adopted"] = ts, written
    wtext(meta_path, dump(meta))
    log(state, "seeds.adopted", args.actor, id=args.card,
        summary=f"{len(written)} {kind} written from {pack}; {len(skipped)} skipped.")
    return {"card": args.card, "written": written, "skipped": skipped}


# ── step 4: reanchor ──────────────────────────────────────────────────────────
DONE = {"complete", "completed", "done", "delivered", "accepted", "cancelled"}


def reanchor(args):
    """Move seeded milestones after start/end/anchor dates change.

    Only a milestone whose planned_end still equals what its seed expression gave against the
    dates it was adopted with is moved; a hand-edited date, a completed milestone, or one without
    seed_due is left alone and reported. Edits are line-level, so comments and field order survive.
    """
    state = os.path.abspath(args.state)
    now = manifest_dates(ry(os.path.join(state, "manifest.yaml")) or {})
    d = os.path.join(state, "milestones")
    moved, kept = [], []
    for f in sorted(glob.glob(os.path.join(d, "*.yaml"))):
        text = io.open(f, encoding="utf-8").read()
        try:
            m = yaml.safe_load(text) or {}
        except Exception:
            continue
        expr = m.get("seed_due")
        if not expr:
            continue
        mid = m.get("id") or os.path.basename(f)[:-5]
        if str(m.get("status") or "").lower() in DONE:
            kept.append(f"{mid}: {m.get('status')}")
            continue
        b = m.get("seed_basis") or {}
        was, _ = resolve_due(expr, as_date(b.get("start")), as_date(b.get("end")), as_date(b.get("anchor")))
        cur = as_date(m.get("planned_end"))
        if was is None or cur != was:
            kept.append(f"{mid}: planned_end {cur} was set by hand (seed gave {was}) — left alone")
            continue
        new, why = resolve_due(expr, now["start"], now["end"], now["anchor"])
        if new is None:
            kept.append(f"{mid}: {why}")
            continue
        if new == cur:
            continue
        moved.append({"id": mid, "from": cur.isoformat(), "to": new.isoformat(), "expr": expr})
        if args.dry_run:
            continue
        ts = now_iso()
        text = re.sub(r"(?m)^planned_end:.*$", f"planned_end: '{new.isoformat()}'", text, count=1)
        text = re.sub(r"(?m)^seed_basis:.*$", seed_basis_lines(expr, now).split("\n")[1], text, count=1)
        for key, val in (("last_modified", f"'{ts}'"), ("last_modified_by", args.actor)):
            if re.search(rf"(?m)^{key}:", text):
                text = re.sub(rf"(?m)^{key}:.*$", f"{key}: {val}", text, count=1)
            else:
                text = text.rstrip("\n") + f"\n{key}: {val}\n"
        yaml.safe_load(text)  # never write a milestone that does not parse
        wtext(f, text)
        log(state, "milestone.updated", args.actor, id=mid,
            summary=f"Re-anchored {mid} ({expr}): planned_end {cur} → {new}.")
    if moved and not args.dry_run:
        log(state, "milestones.reanchored", args.actor, id=f"{dt.date.today().isoformat()}-reanchor",
            summary=f"{len(moved)} seeded milestone(s) moved to the new dates; {len(kept)} left alone.")
    return {"moved": moved, "kept": kept, "dry_run": bool(args.dry_run)}


def _state_phase(state):
    try:
        return json.load(io.open(os.path.join(state, "state.json"), encoding="utf-8")).get("current_phase")
    except Exception:
        return None


NOREPLY = re.compile(r"(^|[.@])no-?reply|users\.noreply\.github\.com$", re.I)


def resolve_actor(state):
    """The person responsible for these writes (project-state SKILL "Who the actor is").

    $PROJECT_STATE_ACTOR, else the repository's git user.email (never a no-reply address), else an
    explicit machine actor. A skill name is never passed off as a person.
    """
    env = os.environ.get("PROJECT_STATE_ACTOR", "").strip()
    if env:
        return env
    try:
        import subprocess
        email = subprocess.run(["git", "-C", state, "config", "user.email"], capture_output=True,
                               text=True, timeout=5).stdout.strip()
        if email and "@" in email and not NOREPLY.search(email):
            return email
    except Exception:
        pass
    return "project-scaffolder (automated)"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("op", choices=["seed", "adopt", "reanchor"])
    ap.add_argument("--state", required=True, help="the facility's project-state/ directory")
    ap.add_argument("--packs-root", default=os.environ.get("PROJECT_STATE_ROOT", DEFAULT_ROOT))
    ap.add_argument("--actor", default=None, help="who to record; default resolves per project-state")
    ap.add_argument("--today")
    ap.add_argument("--card")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-matrix", action="store_true", help="skip step 1 (matrix merge)")
    ap.add_argument("--no-seeds", action="store_true", help="skip step 2 (seed cards) - the old seed-matrix")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.exists(os.path.join(args.state, "manifest.yaml")):
        raise SystemExit(f"ERROR  no manifest.yaml in {args.state}")
    if not args.actor:
        args.actor = resolve_actor(os.path.abspath(args.state))
    if args.op == "adopt" and not args.card:
        raise SystemExit("ERROR  adopt needs --card")
    res = {"seed": seed, "adopt": adopt, "reanchor": reanchor}[args.op](args)
    if args.json:
        print(json.dumps(res, indent=2))
    elif args.op == "seed":
        print(f"packs: {', '.join(res['packs']) or '(none)'}{'  [dry run]' if res['dry_run'] else ''}")
        print(f"matrix entries added: {len(res['matrix_added'])}  {', '.join(res['matrix_added'])}")
        for c in res["cards"]:
            extra = f"  ({len(c['undated'])} undated)" if c["undated"] else ""
            print(f"queued: {c['id']}  {c['count']} {c['kind']}{extra}")
        for s in res["skipped"]:
            print(f"skipped: {s}")
    elif args.op == "reanchor":
        for m in res["moved"]:
            print(f"{'would move' if res['dry_run'] else 'moved'}: {m['id']}  {m['from']} → {m['to']}  ({m['expr']})")
        for k in res["kept"]:
            print(f"kept: {k}")
        if not res["moved"]:
            print("nothing to move")
    else:
        print(f"written: {', '.join(res['written']) or '(none)'}")
        for s in res["skipped"]:
            print(f"skipped: {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
