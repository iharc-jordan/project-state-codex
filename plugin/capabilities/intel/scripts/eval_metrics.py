#!/usr/bin/env python3
"""eval_metrics — the OCI §13.2 headline metrics over an intel facility (docs/INTEL-CI-SPEC.md §14.3).

    python3 eval_metrics.py <facility> [--golden golden.yaml] [--answers DIR] [--as-of YYYY-MM-DD] [--json] [--md]

Measures the projections the competitive skills wrote (profiles, battlecards, deal briefs, briefs, win-loss
analyses, kept answers) and, with --answers, the replies to the golden set's questions:

  unsupported material claim rate   material lines with no valid citation ÷ material lines          target 0
  citation validity                 cited ids that exist, are about the subject (or us), and were      ≥ 0.98
                                    current when the projection was generated
  inference labelling accuracy      lines citing inferred / hypothesis claims that say so, and lines   ≥ 0.98
                                    saying "verified" that cite a verified claim
  unknown recall                    golden unknown questions answered unknown, not confabulated        1.00
  staleness disclosure              stale claims used without being marked stale                       0
  conflict surfacing                open conflicts shown with both sides where either side is cited    1.00

plus the golden set's own check: every golden fact is a current claim with its known status and category.

A material line is a list item, a table row or a paragraph in a section that asserts something. Sections that
are questions, instructions or admissions (discovery questions, talk track, avoid saying, do not, missing
context, what we do not know, watching next) are not material; a line may also end `<!-- non-material -->`.
Reads only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intel_lib import CITE_RE, EVIDENCE_RE, ID_RE, Facility, to_date, yload  # noqa: E402

NON_MATERIAL_SECTIONS = re.compile(r"discovery questions|questions for the next call|talk track|avoid saying|^do not|does not know|do not know|not known|missing context|watching next|open questions|recommended actions|proposed next|sample$|^confidence", re.I)
LABEL = {"inferred": re.compile(r"\binferred\b|\binference\b", re.I), "hypothesis": re.compile(r"\bhypothes[ie]s\b", re.I)}
NON_MATERIAL_LINE = re.compile(r"^\**(not known|proposed next action)\b", re.I)
UNKNOWN_SAID = re.compile(r"\bunknown\b|not known|no evidence|not published|do not know|don't know|no (?:public )?(?:source|figure|data)", re.I)
TARGETS = {"unsupported_material_claim_rate": ("≤", 0.0), "citation_validity": ("≥", 0.98), "inference_labelling": ("≥", 0.98),
           "unknown_recall": ("≥", 1.0), "staleness_disclosure_violations": ("≤", 0), "conflict_surfacing": ("≥", 1.0)}


def material_lines(body: str):
    """(section, line) for every material line of a projection body."""
    section, out, in_comment = "", [], False
    for raw in body.splitlines():
        line = raw.strip()
        if "<!--" in line and "-->" not in line:
            in_comment = True
            continue
        if in_comment:
            in_comment = "-->" not in line
            continue
        if not line or line.startswith(">") or line.startswith("<!--"):
            continue
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            continue
        if NON_MATERIAL_SECTIONS.search(section) or NON_MATERIAL_LINE.search(line) or line.endswith("<!-- non-material -->"):
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) or not c for c in cells):
                continue  # separator
            if not CITE_RE.search(line) and not ID_RE.search(line):
                # a header row has no ids and names columns; a data row without ids is unsupported
                if any(c.lower() in ("claims", "claim", "differentiator", "line", "reason", "provable by", "") for c in cells):
                    continue
        out.append((section, line))
    return out


def cited(line: str):
    """Every claim id the line names: in a citation bracket, or listed bare (a "claims written" list)."""
    return list(dict.fromkeys(ID_RE.findall(line)))


def generated_on(p):
    return to_date(p["front"].get("generated_at") or p["front"].get("answered_at")) or None


def measure(f: Facility, golden=None, answers_dir=None):
    projections = f.projections()
    self_id = f.self_id
    m = {k: {"num": 0, "den": 0, "fail": []} for k in ("unsupported", "citation", "inference", "stale", "conflict", "unknown", "golden")}
    for p in projections:
        on = generated_on(p) or f.as_of
        subject = p["front"].get("subject")
        subject = subject.get("entity") if isinstance(subject, dict) else subject
        body_ids = set(cited(p["body"]))
        for section, line in material_lines(p["body"]):
            ids = cited(line)
            m["unsupported"]["den"] += 1
            if not ids and not EVIDENCE_RE.search(line):
                m["unsupported"]["num"] += 1
                m["unsupported"]["fail"].append(f"{p['path']}: [{section}] {line[:110]}")
            for i in ids:
                c = f.claims.get(i)
                m["citation"]["den"] += 1
                ok = c is not None
                why = "does not exist"
                if ok and subject and subject.startswith("INT-E-") and f.subject(c) not in (subject, self_id):
                    ok, why = False, f"is about {f.subject(c)}, not {subject} or us"
                if ok and not f.current(c, on) and f.superseded_by.get(i) not in ids:
                    ok, why = False, f"was superseded by {f.superseded_by.get(i)} before this was generated"
                if ok:
                    m["citation"]["num"] += 1
                else:
                    m["citation"]["fail"].append(f"{p['path']}: {i} {why}")
            cs = [f.claims[i] for i in ids if i in f.claims]
            for status, rx in LABEL.items():
                if any(c.get("epistemic_status") == status for c in cs) and all(c.get("epistemic_status") in ("inferred", "hypothesis") for c in cs):
                    m["inference"]["den"] += 1
                    if rx.search(line) or (status == "inferred" and LABEL["hypothesis"].search(line)):
                        m["inference"]["num"] += 1
                    else:
                        m["inference"]["fail"].append(f"{p['path']}: cites {status} claim(s) without saying so — {line[:90]}")
            if re.search(r"\bverified\b", line, re.I) and cs:
                m["inference"]["den"] += 1
                if any(c.get("epistemic_status") == "verified" for c in cs):
                    m["inference"]["num"] += 1
                else:
                    m["inference"]["fail"].append(f"{p['path']}: says verified but cites no verified claim — {line[:90]}")
            for c in cs:
                if f.freshness(c, on) == "stale" and f.current(c, on):
                    m["stale"]["den"] += 1
                    if not re.search(r"\bstale\b|outdated", line, re.I):
                        m["stale"]["num"] += 1
                        m["stale"]["fail"].append(f"{p['path']}: {c['id']} was stale on {on} and the line does not say so")
        for a, b in f.open_conflicts():
            ca, cb = f.claims[a], f.claims[b]
            recorded = max(to_date(ca.get("created")) or dt.date.min, to_date(cb.get("created")) or dt.date.min)
            if recorded > on or not ({a, b} & body_ids):
                continue
            m["conflict"]["den"] += 1
            if {a, b} <= body_ids and re.search(r"contested|conflict|disagree", p["body"], re.I):
                m["conflict"]["num"] += 1
            else:
                m["conflict"]["fail"].append(f"{p['path']}: cites {' and '.join(sorted({a, b} & body_ids))} of the open conflict {a} / {b} without showing both sides")
    # golden set: the store holds the known answers, and the unknown questions are answered unknown
    g = golden or {}
    for fact in g.get("facts") or []:
        m["golden"]["den"] += 1
        c = f.claims.get(fact.get("claim"))
        ok = c is not None and f.current(c) and c.get("epistemic_status") == fact.get("status") and c.get("category") == fact.get("category") and f.subject(c) == fact.get("entity")
        if ok:
            m["golden"]["num"] += 1
        else:
            m["golden"]["fail"].append(f"{fact.get('id')}: expected {fact.get('claim')} ({fact.get('entity')} · {fact.get('category')} · {fact.get('status')}) as a current claim")
    # the replies: --answers DIR/<question id>.md (an eval run), else kept answers whose frontmatter names the question
    kept = {p["front"].get("golden"): p["text"] for p in projections if p["front"].get("golden")}
    for q in g.get("unknown_questions") or []:
        f_ = Path(answers_dir) / f"{q['id']}.md" if answers_dir else None
        text = f_.read_text(encoding="utf-8") if f_ and f_.exists() else kept.get(q["id"])
        if text is None:
            continue
        if True:
            m["unknown"]["den"] += 1
            forbidden = [x for x in q.get("must_not_say") or [] if re.search(x, text, re.I)]
            if UNKNOWN_SAID.search(text) and not forbidden:
                m["unknown"]["num"] += 1
            else:
                m["unknown"]["fail"].append(f"{q['id']}: {'said ' + ', '.join(forbidden) if forbidden else 'did not answer unknown'} — {q['question']}")
    rate = lambda k, empty=1.0: round(m[k]["num"] / m[k]["den"], 4) if m[k]["den"] else empty  # noqa: E731
    metrics = {
        "unsupported_material_claim_rate": {"value": rate("unsupported", 0.0), "of": m["unsupported"]["den"], "fail": m["unsupported"]["fail"]},
        "citation_validity": {"value": rate("citation"), "of": m["citation"]["den"], "fail": m["citation"]["fail"]},
        "inference_labelling": {"value": rate("inference"), "of": m["inference"]["den"], "fail": m["inference"]["fail"]},
        "unknown_recall": {"value": rate("unknown") if m["unknown"]["den"] else None, "of": m["unknown"]["den"], "fail": m["unknown"]["fail"]},
        "staleness_disclosure_violations": {"value": m["stale"]["num"], "of": m["stale"]["den"], "fail": m["stale"]["fail"]},
        "conflict_surfacing": {"value": rate("conflict"), "of": m["conflict"]["den"], "fail": m["conflict"]["fail"]},
    }
    for k, v in metrics.items():
        op, t = TARGETS[k]
        v["target"] = f"{op} {t}"
        v["pass"] = None if v["value"] is None else (v["value"] <= t if op == "≤" else v["value"] >= t)
    golden_ok = {"value": rate("golden") if m["golden"]["den"] else None, "of": m["golden"]["den"], "fail": m["golden"]["fail"]}
    measured = [v["pass"] for v in metrics.values() if v["pass"] is not None]
    return {"as_of": str(f.as_of), "projections": len(projections), "metrics": metrics, "golden_facts": golden_ok,
            "unmeasured": [k for k, v in metrics.items() if v["pass"] is None], "pass": bool(measured) and all(measured) and golden_ok["value"] in (None, 1.0)}


def markdown(out, title="Intel evaluation"):
    lines = [f"# {title}", "", f"As of {out['as_of']} · {out['projections']} projection(s) measured · **{'PASS' if out['pass'] else 'FAIL'}**", "",
             "| Metric | Value | Target | Over | Pass |", "|---|---|---|---|---|"]
    for k, v in out["metrics"].items():
        lines.append(f"| {k.replace('_', ' ')} | {'—' if v['value'] is None else v['value']} | {v['target']} | {v['of']} | {'—' if v['pass'] is None else 'yes' if v['pass'] else '**no**'} |")
    gf = out["golden_facts"]
    lines.append(f"| golden facts held as current claims | {'—' if gf['value'] is None else gf['value']} | = 1.0 | {gf['of']} | {'—' if gf['value'] is None else 'yes' if gf['value'] == 1.0 else '**no**'} |")
    fails = [(k, x) for k, v in {**out["metrics"], "golden_facts": gf}.items() for x in v["fail"]]
    if fails:
        lines += ["", "## Failures", ""] + [f"- **{k}** — {x}" for k, x in fails]
    if out["unmeasured"]:
        lines += ["", f"Not measured in this run: {', '.join(out['unmeasured'])} (pass --answers with the replies to the golden questions)."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    ap.add_argument("--golden")
    ap.add_argument("--answers")
    ap.add_argument("--as-of")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args(argv)
    f = Facility(a.facility, a.as_of)
    out = measure(f, yload(Path(a.golden)) if a.golden else None, a.answers)
    if a.json:
        print(json.dumps(out, indent=1, default=str))
    else:
        print(markdown(out), end="")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
