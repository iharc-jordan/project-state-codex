"""intel_lib — read an intel-enabled project-state folder the way every intel script needs it.

Shared by monitor.py, winloss.py and eval_metrics.py (and importable by the view builders). It reads only:
the manifest's `capabilities.intel` block, intel/entities, intel/claims, intel/changes, intel/winloss,
intel/watch.yaml, the projections under intel/, and state/intel.json. It writes nothing — the skills write,
through project-state. Freshness is derived here from the half-life table, never read from a file.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("intel: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

DEFAULT_HALF_LIVES = {"pricing": 90, "packaging": 90, "product": 180, "feature": 180, "integration": 180, "positioning": 180, "messaging": 180, "go-to-market": 180, "security": 180,
                      "customer": 270, "partnership": 270, "compliance": 270, "leadership": 365, "funding": 365, "market": 365, "objection": 120, "win-loss": 120, "sales-tactic": 120, "product-gap": 120}
DEFAULT_MATERIAL_CATEGORIES = ["pricing", "packaging", "product", "feature", "positioning", "security", "compliance", "partnership", "customer"]
REASON_CATEGORIES = ["price", "product-fit", "feature-gap", "integration", "security-compliance", "relationship", "incumbent", "execution", "timing", "procurement-terms", "budget", "trust", "other"]
CITE_RE = re.compile(r"\[(INT-C-\d{3,}(?:\s*(?:,|→|->)\s*INT-C-\d{3,})*)\]")
# evidence a projection may cite besides claims: the deal's own context (deal briefs), a tender, win-loss records
EVIDENCE_RE = re.compile(r"\[(?:context\.md|deal context|tender t-\d{4}-\d{3,}|INT-W-\d{3,})[^\]]*\]", re.I)
ID_RE = re.compile(r"INT-C-\d{3,}")

# claim category → OCI change type (§5.6); a delta in a category not listed is a positioning change
CHANGE_TYPE = {"pricing": "pricing", "packaging": "packaging", "product": "launch", "feature": "launch", "security": "launch", "compliance": "launch",
               "integration": "integration", "positioning": "positioning", "messaging": "positioning", "go-to-market": "positioning", "market": "positioning",
               "customer": "customer", "partnership": "partnership", "leadership": "leadership", "funding": "funding",
               "objection": "sentiment-shift", "win-loss": "sentiment-shift", "sales-tactic": "sentiment-shift", "product-gap": "sentiment-shift"}
# who owns a change in each category — OCI §7.4: an event nobody owns is noise
AFFECTED = {"pricing": ["sales", "finance"], "packaging": ["sales", "product-marketing"], "product": ["product", "sales"], "feature": ["product", "sales"],
            "security": ["product", "sales"], "compliance": ["product", "sales"], "integration": ["product", "partnerships"],
            "positioning": ["product-marketing", "sales"], "messaging": ["product-marketing"], "go-to-market": ["product-marketing", "sales"], "market": ["leadership"],
            "customer": ["sales"], "partnership": ["partnerships", "leadership"], "leadership": ["leadership"], "funding": ["leadership"],
            "objection": ["sales"], "win-loss": ["sales", "product"], "sales-tactic": ["sales"], "product-gap": ["product"]}


def to_date(v):
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def yload(p: Path):
    try:
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def split_front(text: str):
    """(frontmatter dict, body) of a projection; ({}, text) when it has none."""
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end > 0:
            try:
                fm = yaml.safe_load(text[4:end]) or {}
            except Exception:
                fm = {}
            return (fm if isinstance(fm, dict) else {}), text[end + 4:].lstrip("\n")
    return {}, text


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Facility:
    """One project-state folder with the intel capability."""

    def __init__(self, root, as_of=None):
        self.root = Path(root)
        if not (self.root / "manifest.yaml").exists() and (self.root / "project-state" / "manifest.yaml").exists():
            self.root = self.root / "project-state"
        if not (self.root / "manifest.yaml").exists():
            raise SystemExit(f"intel: no manifest.yaml in {root}")
        self.as_of = to_date(as_of) if as_of else dt.date.today()
        self.manifest = yload(self.root / "manifest.yaml") or {}
        self.block = ((self.manifest.get("capabilities") or {}).get("intel") or {})
        self.comp = self.block.get("competitive") or {}
        self.half = {**DEFAULT_HALF_LIVES, **(self.comp.get("half_lives_days") or {})}
        self.state = self._json(self.root / "state" / "intel.json")
        self.entities = self._dir("entities")
        self.claims = self._dir("claims")
        self.changes = self._dir("changes")
        self.winloss = self._dir("winloss")
        self.watch = yload(self.root / "intel" / "watch.yaml") or {}
        # supersession: old id → new id (the newest, if a claim was superseded twice by mistake)
        self.superseded_by = {}
        for c in sorted(self.claims.values(), key=lambda c: str(c.get("created") or "")):
            if c.get("supersedes"):
                self.superseded_by[c["supersedes"]] = c["id"]

    @staticmethod
    def _json(p: Path):
        import json
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _dir(self, name):
        out = {}
        d = self.root / "intel" / name
        if d.is_dir():
            for f in sorted(d.glob("INT-*.yaml")):
                doc = yload(f)
                if isinstance(doc, dict) and doc.get("id"):
                    doc["_path"] = str(f.relative_to(self.root))
                    out[doc["id"]] = doc
        return out

    # ── the registry ─────────────────────────────────────────────────────────
    @property
    def self_id(self):
        s = self.comp.get("self_entity")
        return (s[0] if isinstance(s, list) and s else s) or None

    def in_scope(self):
        """The competitors in scope: competitive.competitors, else every entity of type competitor."""
        ids = self.comp.get("competitors") or [e for e, d in self.entities.items() if d.get("type") == "competitor"]
        return [i for i in ids if i in self.entities]

    def name(self, eid):
        return (self.entities.get(eid) or {}).get("name") or eid

    # ── claims ───────────────────────────────────────────────────────────────
    def subject(self, c):
        s = c.get("subject")
        return s.get("entity") if isinstance(s, dict) else s

    def claim_date(self, c):
        return to_date(c.get("source_date")) or to_date(c.get("retrieved_at")) or to_date(c.get("created"))

    def freshness(self, c, on=None):
        """fresh below the half-life, aging to twice it, stale beyond — derived, never stored (spec §3.2)."""
        on = on or self.as_of
        d = self.claim_date(c)
        if d is None:
            return "stale"
        age = (on - d).days
        h = self.half.get(c.get("category"), 180)
        return "fresh" if age < h else "aging" if age < 2 * h else "stale"

    def current(self, c, on=None):
        """Not superseded by a claim created on or before `on`."""
        new = self.superseded_by.get(c["id"])
        if not new:
            return True
        if on is None:
            return False
        created = to_date(self.claims[new].get("created"))
        return created is None or created > on

    def current_claims(self, eid=None, categories=None):
        return [c for c in self.claims.values() if self.current(c) and (eid is None or self.subject(c) == eid) and (not categories or c.get("category") in categories)]

    def open_conflicts(self):
        seen, out = set(), []
        for c in self.claims.values():
            for o in c.get("conflicts_with") or []:
                pair = tuple(sorted([c["id"], o]))
                if pair in seen or o not in self.claims:
                    continue
                seen.add(pair)
                if self.current(self.claims[pair[0]]) and self.current(self.claims[pair[1]]):
                    out.append(pair)
        return out

    # ── projections ──────────────────────────────────────────────────────────
    def projections(self):
        """Every generated file the validator polices: profiles, battlecards, deal briefs, briefs, win-loss analyses, kept answers."""
        pats = ["intel/profiles/*.md", "intel/battlecards/*.md", "intel/deals/*/brief.md", "intel/reports/brief-*.md", "intel/reports/winloss-*.md", "intel/answers/*.md"]
        out = []
        for pat in pats:
            for f in sorted(self.root.glob(pat)):
                text = f.read_text(encoding="utf-8")
                fm, body = split_front(text)
                out.append({"path": str(f.relative_to(self.root)), "front": fm, "body": body, "text": text})
        return out
