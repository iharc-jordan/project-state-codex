"""_research — shared reading and derivation for the research capability's report lenses.

Every rule the reports display is computed here once, so the three reports can never disagree
about what "stale", "answered" or "counts toward the gate" means:

  freshness        fresh < half-life ≤ aging ≤ 2× half-life < stale   (spec §4.4, OCI §3.3)
  superseded       another finding names this one in `supersedes`
  gate-eligible    established, not superseded, not withdrawn          (spec §4.4)
  question state   open · answered · aging · stale · reopened · dropped  (spec §4.8)

Read-only. Nothing here writes into the substrate.
"""
from __future__ import annotations

import datetime as dt
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("research views: PyYAML is required (pip install pyyaml)")

DEFAULT_HALF_LIVES = {"statistic": 365, "market": 365, "organisation": 365, "offering": 270, "pricing": 90,
                      "programme": 180, "regulation": 180, "technology": 270, "event": 60, "literature": 730, "method": 1095}
TIERS = ["primary", "secondary", "tertiary", "speculative"]
EPISTEMIC = ["verified", "reported", "inferred", "hypothesis", "unknown"]
TERMINAL = ("complete", "closed-negative", "killed")


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def yload(p: Path):
    try:
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def to_date(v):
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def load_dir(d: Path) -> list[dict]:
    out = []
    for p in sorted(d.glob("*.yaml")):
        x = yload(p)
        if isinstance(x, dict):
            x.setdefault("id", p.stem)
            out.append(x)
    return out


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or url).removeprefix("www.")
    except Exception:
        return url


class Facility:
    """Everything the reports read, loaded once, with the derivations attached."""

    def __init__(self, fac: Path, today: dt.date):
        self.fac, self.today = fac, today
        self.manifest = yload(fac / "manifest.yaml") or {}
        self.cap = (self.manifest.get("capabilities") or {}).get("research") or {}
        self.name = (self.manifest.get("project") or {}).get("name") or fac.parent.name
        self.scope = (self.manifest.get("project") or {}).get("scope_one_liner")
        self.half = {**DEFAULT_HALF_LIVES, **(self.cap.get("half_lives_days") or {})}
        R = fac / "research"
        self.mandates = load_dir(R / "mandates")
        self.steps = load_dir(R / "steps")
        self.findings = load_dir(R / "findings")
        self.challenges = load_dir(R / "challenges")
        self.candidates = load_dir(R / "candidates")
        self.changes = load_dir(R / "changes")
        self.runs = []
        for p in sorted((R / "runs").glob("RUN-*.json")) if (R / "runs").is_dir() else []:
            try:
                self.runs.append(json.loads(p.read_text()))
            except Exception:
                pass
        try:
            self.state = json.loads((fac / "state" / "research.json").read_text())
        except Exception:
            self.state = {}
        self.events = []
        log = fac / "logs" / "activity.ndjson"
        if log.is_file():
            for line in log.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if str(e.get("event", "")).startswith("research."):
                    self.events.append(e)
        self.reports = sorted(p.name for p in (R / "reports").glob("RES-M-*")) if (R / "reports").is_dir() else []

        self.by_id = {f["id"]: f for f in self.findings}
        self.superseded_by = {}
        for f in self.findings:
            if f.get("supersedes"):
                self.superseded_by[f["supersedes"]] = f["id"]
        self.mandate = {m["id"]: m for m in self.mandates}

    # ── per-finding ──────────────────────────────────────────────────────────
    def source_date(self, f):
        ds = [to_date(e.get("source_date") or e.get("retrieved_at")) for e in (f.get("evidence") or []) if isinstance(e, dict)]
        ds = [d for d in ds if d]
        return max(ds) if ds else to_date(f.get("created"))

    def freshness(self, f) -> str:
        d = self.source_date(f)
        if not d:
            return "undated"
        hl = int(self.half.get(str(f.get("category")), 365))
        age = (self.today - d).days
        return "fresh" if age < hl else ("aging" if age <= 2 * hl else "stale")

    def days_to_stale(self, f):
        d = self.source_date(f)
        if not d:
            return None
        return 2 * int(self.half.get(str(f.get("category")), 365)) - (self.today - d).days

    def superseded(self, f) -> bool:
        return f["id"] in self.superseded_by

    def live(self, f) -> bool:
        return not self.superseded(f) and f.get("status") != "withdrawn"

    def gate_eligible(self, f) -> bool:
        return self.live(f) and f.get("status") == "established"

    def not_triangulated(self, f) -> bool:
        refs = [e for e in (f.get("evidence") or []) if isinstance(e, dict)]
        return bool(f.get("derives_from")) or (len(refs) >= 2 and int(f.get("independent_sources") or 0) < 2)

    def challenged(self, fid):
        return [c for c in self.challenges if c.get("finding_id") == fid]

    # ── per-mandate ──────────────────────────────────────────────────────────
    def findings_for(self, mid):
        return [f for f in self.findings if f.get("mandate_id") == mid]

    def question_state(self, m, q) -> str:
        """open · answered · aging · stale · reopened · dropped — only open/answered/dropped are stored."""
        if q.get("state") == "dropped":
            return "dropped"
        ans = [self.by_id[i] for i in (q.get("answered_by") or []) if i in self.by_id]
        ans = [f for f in ans if self.gate_eligible(f)]
        if not ans:
            return "open"
        fr = {self.freshness(f) for f in ans}
        if "fresh" in fr or "undated" in fr:
            return "answered"
        if fr == {"stale"}:
            return "reopened" if m.get("status") == "standing" else "stale"
        return "aging"

    def changed_recently(self, mid, qid, days=7) -> bool:
        return any(x.get("mandate_id") == mid and x.get("subject") == qid and x.get("significance") == "material"
                   and to_date(x.get("detected_at")) and (self.today - to_date(x.get("detected_at"))).days <= days
                   for x in self.changes)

    def gate(self, m):
        """(primary share over gate-eligible findings, threshold, verdict) — tier_audit's arithmetic."""
        el = [f for f in self.findings_for(m["id"]) if self.gate_eligible(f)]
        thr = float(m.get("primary_source_min_ratio") or self.cap.get("defaults", {}).get("primary_source_min_ratio") or 0.5)
        if not el:
            return None, thr, "no evidence"
        share = sum(1 for f in el if f.get("source_tier") == "primary") / len(el)
        return share, thr, ("pass" if share >= thr else "below")

    def open_blocking(self, mid):
        return [c for c in self.challenges if c.get("mandate_id") == mid and c.get("status") == "open" and c.get("severity") == "blocking"]

    def last_run(self):
        return self.runs[-1] if self.runs else None


# ── the page shell ───────────────────────────────────────────────────────────
# The house tokens (intel and portfolio use the same ground, paper and ink), plus the
# research families. System fonts only: the app's CSP admits no external resources.
TOKENS = """
:root{--ground:#F5F7F4;--paper:#FFFFFF;--ink:#1B2230;--muted:#6B7480;--faint:#A9B1B8;--line:#DDE3DE;--rule:#B9C2BC;
--accent:#1F5F6B;--accent-soft:#E3EEF0;--crit:#C23A3A;--crit-soft:#F6E0E0;--warn:#B07600;--warn-soft:#F7ECD6;--ok:#2E7D4F;--ok-soft:#E1F0E6;
--t-primary:#1F5F6B;--t-secondary:#5C93A0;--t-tertiary:#B5C9CD;--t-spec:#E3D6C2;
--f-step:#5C93A0;--f-finding:#2E7D4F;--f-barren:#B07600;--f-red:#C23A3A;--f-change:#6B4FA0;--f-ship:#1F5F6B;--f-gate:#1B2230;--f-mandate:#A9B1B8;
--mono:ui-monospace,Menlo,monospace;--sans:system-ui,-apple-system,"Segoe UI",sans-serif;--serif:Georgia,"Times New Roman",serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--ground:#12181E;--paper:#1A222A;--ink:#E7EBEE;--muted:#A3ACB4;--faint:#5B6670;--line:#2C3640;--rule:#465262;
--accent:#6FBFC9;--accent-soft:#1E3238;--crit:#E66767;--crit-soft:#3E2222;--warn:#E0B463;--warn-soft:#3A2F17;--ok:#6CC58F;--ok-soft:#1D3327;
--t-primary:#6FBFC9;--t-secondary:#3F7F8C;--t-tertiary:#2E4A50;--t-spec:#4A3F30;
--f-step:#3F7F8C;--f-finding:#6CC58F;--f-barren:#E0B463;--f-red:#E66767;--f-change:#A58BDB;--f-ship:#6FBFC9;--f-gate:#E7EBEE;--f-mandate:#5B6670}}
:root[data-theme="dark"]{color-scheme:dark;--ground:#12181E;--paper:#1A222A;--ink:#E7EBEE;--muted:#A3ACB4;--faint:#5B6670;--line:#2C3640;--rule:#465262;
--accent:#6FBFC9;--accent-soft:#1E3238;--crit:#E66767;--crit-soft:#3E2222;--warn:#E0B463;--warn-soft:#3A2F17;--ok:#6CC58F;--ok-soft:#1D3327;
--t-primary:#6FBFC9;--t-secondary:#3F7F8C;--t-tertiary:#2E4A50;--t-spec:#4A3F30;
--f-step:#3F7F8C;--f-finding:#6CC58F;--f-barren:#E0B463;--f-red:#E66767;--f-change:#A58BDB;--f-ship:#6FBFC9;--f-gate:#E7EBEE;--f-mandate:#5B6670}
"""

BASE_CSS = """
*{box-sizing:border-box}body{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0}
.wrap{max-width:1040px;margin:0 auto;padding:28px 20px 64px}h1{font-family:var(--serif);font-weight:600;font-size:2rem;line-height:1.1;margin:0;text-wrap:balance}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.lede{color:var(--muted);max-width:68ch;margin:8px 0 22px}
.scope{border-left:3px solid var(--accent);background:var(--accent-soft);padding:10px 14px;border-radius:0 6px 6px 0;margin:0 0 22px;font-size:.93rem}
section{margin-bottom:48px}section>header .q{font-family:var(--serif);font-size:1.45rem;font-weight:600;text-wrap:balance}section>header .w{color:var(--muted);font-size:.9rem;margin-top:2px;max-width:78ch}
.fig{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:16px 18px 14px;margin-top:14px}
svg{width:100%;height:auto;display:block;font-family:var(--sans)}svg text{fill:var(--ink);font-size:12px}svg .mut{fill:var(--muted);font-size:11px}svg .mono{font-family:var(--mono);font-size:10px;fill:var(--muted)}svg .grid{stroke:var(--line);stroke-width:1}
.counts{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 30px}.counts .c{border:1px solid var(--line);border-radius:8px;background:var(--paper);padding:10px 14px;min-width:104px}
.counts .c b{display:block;font-family:var(--serif);font-size:1.6rem;font-weight:600;line-height:1;font-variant-numeric:tabular-nums}.counts .c span{font-family:var(--mono);font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.counts .c.alert{border-color:var(--crit);background:var(--crit-soft)}.counts .c.alert b{color:var(--crit)}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.88rem}th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-family:var(--mono);font-size:.68rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500}tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}.id{font-family:var(--mono);font-size:.78rem;color:var(--muted);white-space:nowrap}.mut{color:var(--muted)}.small{font-size:.82rem}
.chip{display:inline-block;font-family:var(--mono);font-size:.68rem;letter-spacing:.03em;padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--muted);white-space:nowrap}
.chip.ok{border-color:var(--ok);color:var(--ok);background:var(--ok-soft)}.chip.warn{border-color:var(--warn);color:var(--warn);background:var(--warn-soft)}
.chip.crit{border-color:var(--crit);color:var(--crit);background:var(--crit-soft)}.chip.acc{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}.chip.solid{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.78rem;color:var(--muted);margin-top:10px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.cites{font-family:var(--mono);font-size:.72rem;color:var(--muted);margin:10px 0 0;line-height:1.7}.cites b{color:var(--accent);font-weight:500}
.fixture{font-family:var(--mono);font-size:.7rem;color:var(--warn);border:1px dashed var(--warn);border-radius:4px;padding:2px 8px;display:inline-block;margin-left:8px;vertical-align:4px}
"""


def page(title: str, body: str, css: str, artifact: bool) -> str:
    """A self-contained report. --artifact emits the body-only form the Artifact publisher wraps."""
    style = f"<style>{TOKENS}{BASE_CSS}{css}</style>"
    if artifact:
        return f"<title>{esc(title)}</title>\n{style}\n<div class=\"wrap\">{body}</div>\n"
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{esc(title)}</title>{style}</head><body><div class=\"wrap\">{body}</div></body></html>\n")


def is_fixture(fx: "Facility") -> bool:
    return "FIXTURE" in str(fx.scope or "")


# ── the shared model: what every view draws from ───────────────────────────
# One derivation for the At a glance report, the Timeline report and the Console's Research tab (through
# view_capability research → build-research-glance.py --json), so no two views can disagree.
FAMILIES = [("mandate", "mandate moves"), ("step", "steps that found something"), ("barren", "barren steps"), ("finding", "findings"),
            ("red", "red team"), ("change", "changes"), ("ship", "shipped, briefed, retro"), ("gate", "parked for a person")]


def family(e) -> str | None:
    ev = str(e.get("event"))
    if ev.startswith("research.mandate."):
        return "mandate"
    if ev == "research.step.completed":
        return "barren" if int(e.get("findings") or 0) == 0 else "step"
    if ev == "research.finding.logged":
        return "finding"
    if ev in ("research.challenge.raised", "research.challenge.ruled"):
        return "red"
    if ev == "research.change.detected":
        return None if e.get("significance") == "noise" else "change"
    if ev in ("research.deliverable.shipped", "research.brief.generated", "research.retro.recorded"):
        return "ship"
    if ev == "research.walk.gated":
        return "gate"
    return None


def needs(fx: "Facility") -> list[dict]:
    """What is waiting on a person, most urgent first (the glance's picture 2 and the digest's walk-gated check)."""
    need, gated_text = [], ""
    run = fx.last_run()
    if run:
        for g in run.get("gates") or []:
            if g.get("status", "open") == "open":
                need.append({"severity": "urgent" if "blocking" in str(g.get("why", "")).lower() or "RES-C" in str(g.get("question")) else "soon",
                             "what": g.get("question"), "why": g.get("why"), "mandate": g.get("mandate_id"), "handler": g.get("skill") or "—",
                             "source": f"parked by {run['run_id']}"})
                gated_text += " " + str(g.get("question"))
    for m in fx.mandates:
        if m.get("status") in ("killed",):
            continue
        for c in fx.open_blocking(m["id"]):
            if c["id"] not in gated_text:
                need.append({"severity": "urgent", "what": f"Blocking challenge {c['id']} on {c.get('finding_id')}", "why": c.get("argument"),
                             "mandate": m["id"], "handler": "research-redteam", "source": "open"})
        if m.get("status") == "draft" and int(m.get("iteration") or 1) >= 2 and m["id"] not in gated_text:
            need.append({"severity": "soon", "what": f"Lock or kill {m['id']}", "why": f"A draft for {m.get('iteration')} iterations.",
                         "mandate": m["id"], "handler": "research-mandate", "source": "drifting"})
        prov = [f for f in fx.findings_for(m["id"]) if fx.live(f) and f.get("status") == "provisional" and f.get("material")]
        if prov and m.get("status") not in TERMINAL:
            need.append({"severity": "soon", "what": f"{len(prov)} material finding{'s wait' if len(prov) != 1 else ' waits'} for corroboration",
                         "why": "Provisional findings do not count toward the gate until an independent origin agrees or a person confirms: " + ", ".join(f["id"] for f in prov),
                         "mandate": m["id"], "handler": "research-step validate", "source": "provisional"})
        for q in m.get("questions") or []:
            if fx.question_state(m, q) in ("reopened", "stale"):
                need.append({"severity": "soon", "what": f"{q.get('id')} reopened: the evidence that answered it has gone stale", "why": q.get("text"),
                             "mandate": m["id"], "handler": "research-walk", "source": "stale evidence"})
    # a study or article whose evidence has moved since it was written: a superseded, withdrawn or missing citation
    lib = library(fx)
    for d in lib["studies"] + lib["articles"]:
        if d["kind"] == "study" and d["status"] in ("draft", "blocked"):
            continue
        gone = [c["id"] for c in d["citations"] if c["state"] in ("superseded", "withdrawn", "missing")]
        if gone:
            verb = f"research-brief article {d['slug']}" if d["kind"] == "article" else "research-brief draft"
            need.append({"severity": "ondeck", "what": f"{'Recompile' if d['kind'] == 'article' else 'Re-issue'} “{d['title']}”",
                         "why": f"It cites {', '.join(gone)}, since superseded or withdrawn — readers of {d['path']} see what the research no longer holds.",
                         "mandate": d.get("mandate") or ", ".join(d.get("mandates") or []), "handler": verb, "source": "evidence moved"})
    need.sort(key=lambda r: {"urgent": 0, "soon": 1}.get(r["severity"], 2))
    return need


def lifecycle(fx: "Facility", m) -> list[dict]:
    """The mandate's phases as [from, to) spans, from its own stamps and the activity log."""
    marks = [("draft", m.get("created"))]
    ev = {e.get("event"): e.get("ts") for e in fx.events if (e.get("id") or e.get("ref")) == m["id"]}
    if m.get("locked_at") or ev.get("research.mandate.locked"):
        marks.append(("locked", m.get("locked_at") or ev.get("research.mandate.locked")))
    first_step = min((str(s.get("started_at")) for s in fx.steps if s.get("mandate_id") == m["id"] and s.get("started_at")), default=None)
    if first_step and m.get("status") != "draft":
        marks.append(("standing" if m.get("status") == "standing" else "in-progress", ev.get("research.mandate.started") or ev.get("research.mandate.made-standing") or first_step))
    end = m.get("completed_at") or m.get("killed_at") or ev.get("research.mandate.completed") or ev.get("research.mandate.closed-negative") or ev.get("research.mandate.killed")
    if m.get("status") in TERMINAL:
        marks.append((m.get("status"), end or (marks[-1][1])))
    marks = [(p, str(t)[:10]) for p, t in marks if t]
    spans = []
    for i, (p, t) in enumerate(marks):
        spans.append({"phase": p, "from": t, "to": marks[i + 1][1] if i + 1 < len(marks) else None})
    return spans


def model(fx: "Facility", window_days: int = 120) -> dict:
    live = [m for m in fx.mandates if m.get("status") != "killed"]
    accepted = {c.get("finding_id") for c in fx.challenges if c.get("status") == "accepted"}
    ruled_at = {}
    for e in fx.events:
        if e.get("event") == "research.challenge.ruled":
            ruled_at[e.get("id") or e.get("ref")] = str(e.get("ts"))[:10]

    def stale_on(f):
        d = fx.source_date(f)
        return (d + dt.timedelta(days=2 * int(fx.half.get(str(f.get("category")), 365)))).isoformat() if d else None

    def aging_on(f):
        d = fx.source_date(f)
        return (d + dt.timedelta(days=int(fx.half.get(str(f.get("category")), 365)))).isoformat() if d else None

    findings = []
    for f in fx.findings:
        findings.append({"id": f["id"], "mandate": f.get("mandate_id"), "step": f.get("step_id"), "answers": f.get("answers") or [], "claim": f.get("claim"),
                         "tier": f.get("source_tier"), "confidence": f.get("confidence"), "epistemic": f.get("epistemic_status"), "status": f.get("status"),
                         "material": bool(f.get("material")), "independent": f.get("independent_sources"), "category": f.get("category"),
                         "freshness": fx.freshness(f), "source_date": str(fx.source_date(f) or ""), "aging_on": aging_on(f), "stale_on": stale_on(f),
                         "created": str(f.get("created") or "")[:10], "superseded_by": fx.superseded_by.get(f["id"]), "supersedes": f.get("supersedes"),
                         "live": fx.live(f), "gate": fx.gate_eligible(f), "not_triangulated": fx.not_triangulated(f), "challenged": f["id"] in accepted,
                         "open_challenges": [c["id"] for c in fx.challenged(f["id"]) if c.get("status") == "open"],
                         "hosts": sorted({host(str(e.get("ref"))) if str(e.get("ref", "")).startswith("http") else "documents" for e in f.get("evidence") or [] if isinstance(e, dict) and e.get("ref")})})
    mandates = []
    for m in sorted(live, key=lambda m: m["id"]):
        mf = [f for f in fx.findings_for(m["id"]) if fx.live(f)]
        est = [f for f in mf if f.get("status") == "established"]
        share, thr, verdict = fx.gate(m)
        qs = []
        for q in m.get("questions") or []:
            ans = [fx.by_id[i] for i in q.get("answered_by") or [] if i in fx.by_id and fx.gate_eligible(fx.by_id[i])]
            qs.append({"id": q.get("id"), "text": q.get("text"), "state": fx.question_state(m, q), "answered_by": q.get("answered_by") or [],
                       "tiers": dict(Counter(f.get("source_tier") for f in ans)), "moved": fx.changed_recently(m["id"], q.get("id")),
                       "stale_on": max((stale_on(f) for f in ans if stale_on(f)), default=None)})
        mandates.append({"id": m["id"], "headline": m.get("headline"), "status": m.get("status"), "type": m.get("methodology_type"), "iteration": m.get("iteration"),
                         "cadence": (m.get("standing") or {}).get("cadence"), "created": str(m.get("created") or "")[:10],
                         "gate": {"share": None if share is None else round(share, 3), "threshold": thr, "verdict": verdict},
                         "tiers": dict(Counter(f.get("source_tier") for f in est)), "epistemic": dict(Counter(f.get("epistemic_status") for f in mf)),
                         "established": len(est), "provisional": sum(1 for f in mf if f.get("status") == "provisional"),
                         "not_triangulated": sum(1 for f in est if fx.not_triangulated(f)), "blocking": [c["id"] for c in fx.open_blocking(m["id"])],
                         "questions": qs, "lifecycle": lifecycle(fx, m), "null_result": m.get("null_result_statement"),
                         "steps": sum(1 for s in fx.steps if s.get("mandate_id") == m["id"]),
                         "barren": sum(1 for s in fx.steps if s.get("mandate_id") == m["id"] and s.get("status") == "complete" and not s.get("findings_produced"))})
    start = fx.today - dt.timedelta(days=window_days)
    spine = Counter()
    for e in fx.events:
        d, fam = to_date(e.get("ts")), family(e)
        if d and fam and start <= d <= fx.today:
            spine[(d.isoformat(), fam)] += 1
    open_ch = [c for c in fx.challenges if c.get("status") == "open"]
    need = needs(fx)
    return {
        "generator": "capabilities/research/views/_research.py model", "as_of": fx.today.isoformat(), "project": fx.name, "scope": fx.scope,
        "fixture": is_fixture(fx), "half_lives": fx.half, "last_brief": fx.state.get("last_brief"), "last_sweep": fx.state.get("last_sweep"),
        "walk": {"active": (fx.state.get("walk") or {}).get("active"), "last_run": (fx.state.get("walk") or {}).get("last_run")},
        # a draft's questions are not yet committed to, so they do not count (as the glance counts them)
        "counts": {"mandates_active": sum(1 for m in live if m.get("status") not in TERMINAL), "questions": sum(len(m["questions"]) for m in mandates if m["status"] != "draft"),
                   "answered": sum(1 for m in mandates if m["status"] != "draft" for q in m["questions"] if q["state"] in ("answered", "aging")),
                   "established": sum(1 for f in findings if f["live"] and f["status"] == "established"),
                   "provisional": sum(1 for f in findings if f["live"] and f["status"] == "provisional"),
                   "open_challenges": len(open_ch), "blocking": sum(1 for c in open_ch if c.get("severity") == "blocking"), "waiting": len(need),
                   "stale": sum(1 for f in findings if f["live"] and f["freshness"] == "stale")},
        "mandates": mandates, "findings": findings,
        "challenges": [{"id": c["id"], "mandate": c.get("mandate_id"), "finding": c.get("finding_id"), "kind": c.get("kind"), "severity": c.get("severity"),
                        "status": c.get("status"), "argument": c.get("argument"), "proposed": c.get("proposed_resolution"), "resolution": c.get("resolution"),
                        "resolved_by": c.get("resolved_by"), "created": str(c.get("created") or "")[:10], "ruled": ruled_at.get(c["id"]) or (str(c.get("resolved_at"))[:10] if c.get("resolved_at") else None)}
                       for c in fx.challenges],
        "changes": [{"id": x["id"], "mandate": x.get("mandate_id"), "subject": x.get("subject"), "detected_at": str(x.get("detected_at"))[:10],
                     "significance": x.get("significance"), "before": x.get("before") or [], "after": x.get("after") or [], "summary": x.get("summary")} for x in fx.changes],
        "steps": [{"id": s["id"], "mandate": s.get("mandate_id"), "mode": s.get("mode"), "description": s.get("description"), "status": s.get("status"),
                   "started": str(s.get("started_at") or "")[:10], "completed": str(s.get("completed_at") or "")[:10] or None,
                   "findings": len(s.get("findings_produced") or []), "barren": s.get("status") == "complete" and not s.get("findings_produced"), "run": s.get("run_id")} for s in fx.steps],
        "runs": [{"run_id": r.get("run_id"), "started": str(r.get("started") or "")[:10], "status": r.get("status"), "actions": len(r.get("actions") or []),
                  "gates": len(r.get("gates") or [])} for r in fx.runs],
        "candidates": [{"id": c["id"], "mandate": c.get("mandate_id"), "name": c.get("name"), "status": c.get("status"), "total": c.get("total"), "rank": c.get("rank")} for c in fx.candidates],
        "waiting": need,
        "spine": [{"date": d, "family": fam, "n": n} for (d, fam), n in sorted(spine.items())],
        "families": [{"id": k, "label": l} for k, l in FAMILIES],
        "reports": fx.reports,
        "library": library(fx),
    }


# ── the reading layer: Markdown with finding citations (studies, articles, deliverables) ───────────
# One renderer for every document research produces, so a citation looks the same in a deliverable (scripts/render.py),
# the Library report and the Console's reader: [RES-F-004, RES-F-011] becomes a chip per finding, drawn by `badge`.
import re  # noqa: E402

CITE = re.compile(r"\[(RES-F-\d{3,}(?:\s*,\s*RES-F-\d{3,})*)\]")


def split_front(text: str):
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end > 0:
            return text[4:end], text[end + 4:].lstrip("\n")
    return "", text


def inline(s: str, badge) -> str:
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return CITE.sub(lambda m: " ".join(badge(i.strip()) for i in m.group(1).split(",")), s)


def md(body: str, badge) -> str:
    out, para, lst = [], [], None
    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>" + inline(" ".join(para), badge) + "</p>")
            para = []
        if lst:
            out.append(f"<{lst[0]}>" + "".join(f"<li>{inline(x, badge)}</li>" for x in lst[1]) + f"</{lst[0]}>")
            lst = None
    for raw in body.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("<!--"):
            continue
        h = re.match(r"^(#{1,4})\s+(.*)", line)
        li = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)", line)
        if h:
            flush()
            n = len(h.group(1))
            out.append(f"<h{n}>{inline(h.group(2), badge)}</h{n}>")
        elif li:
            if para:
                flush()
            kind = "ol" if re.match(r"^\s*\d+\.", line) else "ul"
            if not lst or lst[0] != kind:
                flush()
                lst = (kind, [])
            lst[1].append(li.group(1))
        elif not line.strip():
            flush()
        else:
            if lst:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)





# ── the library: studies and articles, and whether their evidence still holds ──────────────────────
# A STUDY is a mandate's deliverable (research-brief draft → research/reports/RES-M-NNN-<slug>-YYYY-MM-DD.md, rendered
# to .html beside it): bounded mandates ship one; a standing mandate's latest is a *living* study. An ARTICLE is a topic
# page compiled across mandates (research-brief article → research/topics/<slug>.md, spec §4.1): a projection, never
# edited, regenerated when its evidence moves. Both are read against the evidence as it stands TODAY: a citation to a
# finding since superseded, withdrawn, gone stale, still provisional or under an open challenge is flagged in place.
def citation_state(fx: "Facility", fid: str, generated=None) -> dict:
    f = fx.by_id.get(fid)
    if not f:
        return {"id": fid, "state": "missing"}
    st = {"id": fid, "claim": f.get("claim"), "tier": f.get("source_tier"), "confidence": f.get("confidence"), "epistemic": f.get("epistemic_status"),
          "status": f.get("status"), "freshness": fx.freshness(f), "mandate": f.get("mandate_id"), "state": "ok"}
    if fx.superseded(f):
        new = fx.by_id.get(fx.superseded_by[fid]) or {}
        st.update(state="superseded", by=fx.superseded_by[fid], by_claim=new.get("claim"), since=str(new.get("created") or "")[:10])
    elif f.get("status") == "withdrawn":
        st["state"] = "withdrawn"
    elif any(c.get("status") == "open" for c in fx.challenged(fid)):
        st.update(state="challenged", challenges=[c["id"] for c in fx.challenged(fid) if c.get("status") == "open"])
    elif fx.freshness(f) == "stale":
        st["state"] = "stale"
    elif f.get("status") == "provisional":
        st["state"] = "provisional"
    return st


def first_paragraph(body: str, heading: str | None = None) -> str | None:
    lines, on = body.splitlines(), heading is None
    para = []
    for ln in lines:
        if ln.startswith("#"):
            if para:
                break
            on = heading is None or heading.lower() in ln.lower()
            continue
        if on and ln.strip() and not ln.strip().startswith(("<!--", ">", "|")):
            para.append(ln.strip())
        elif para:
            break
    text = re.sub(r"\s+([.,;:])", r"\1", CITE.sub("", " ".join(para))).replace("  ", " ").strip()   # an excerpt, not the evidence
    return text or None


def library(fx: "Facility") -> dict:
    R = fx.fac / "research"
    studies, articles = [], []
    for p in sorted((R / "reports").glob("RES-M-*.md")) if (R / "reports").is_dir() else []:
        if "-delta-" in p.name:   # the weekly delta brief is a report about change, not a study
            continue
        text = p.read_text(encoding="utf-8")
        front_raw, body = split_front(text)
        front = yaml.safe_load(front_raw) if front_raw else {}
        front = front if isinstance(front, dict) else {}
        mid = front.get("mandate_id") or p.name[:9]
        m = fx.mandate.get(mid) or {}
        cited = list(dict.fromkeys(i.strip() for mm in CITE.finditer(body) for i in mm.group(1).split(",")))
        cites = [citation_state(fx, i) for i in cited]
        status = str(front.get("status") or ("shipped" if any((e.get("id") or e.get("ref")) and p.name in str(e.get("id") or e.get("ref")) and e.get("event") == "research.deliverable.shipped" for e in fx.events) else "draft"))
        if m.get("status") == "standing":
            status = "living"
        elif status == "draft" and fx.open_blocking(mid):
            status = "blocked"
        h1 = next((ln[2:].strip() for ln in body.splitlines() if ln.startswith("# ")), None)
        studies.append({"path": f"research/reports/{p.name}", "html": f"research/reports/{p.with_suffix('.html').name}" if p.with_suffix(".html").exists() else None,
                        "kind": "study", "mandate": mid, "mandate_status": m.get("status"), "method": m.get("methodology_type"),
                        "title": front.get("title") or h1 or m.get("headline") or p.stem, "status": status,
                        "generated_at": str(front.get("generated_at") or "")[:10] or None, "answer": first_paragraph(body, "answer") or first_paragraph(body),
                        "citations": cites, "health": dict(Counter(c["state"] for c in cites)), "blocking": [c["id"] for c in fx.open_blocking(mid)],
                        "gate": front.get("gate"), "markdown": body[:60000]})
    for p in sorted((R / "topics").glob("*.md")) if (R / "topics").is_dir() else []:
        text = p.read_text(encoding="utf-8")
        front_raw, body = split_front(text)
        front = yaml.safe_load(front_raw) if front_raw else {}
        front = front if isinstance(front, dict) else {}
        cited = list(dict.fromkeys(i.strip() for mm in CITE.finditer(body) for i in mm.group(1).split(",")))
        cites = [citation_state(fx, i) for i in cited]
        h1 = next((ln[2:].strip() for ln in body.splitlines() if ln.startswith("# ")), None)
        articles.append({"path": f"research/topics/{p.name}", "kind": "article", "slug": front.get("slug") or p.stem, "title": front.get("title") or h1 or p.stem,
                         "lede": front.get("lede") or first_paragraph(body), "mandates": front.get("mandates") or sorted({c.get("mandate") for c in cites if c.get("mandate")}),
                         "compiled_at": str(front.get("compiled_at") or "")[:10] or None, "tags": front.get("tags") or [],
                         "citations": cites, "health": dict(Counter(c["state"] for c in cites)), "markdown": body[:60000]})
    return {"studies": sorted(studies, key=lambda d: (d["mandate"], d["generated_at"] or "")), "articles": articles}
