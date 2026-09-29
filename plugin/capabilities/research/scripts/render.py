#!/usr/bin/env python3
"""render — compose a mandate's deliverable so it keeps its evidence (docs/RESEARCH-CAPABILITY-SPEC.md §6.8).

    python3 render.py <facility> RES-M-NNN --draft DRAFT.md --out FILE.html [--as-of YYYY-MM-DD] [--json]

research-brief writes the draft from templates/sections.md; this renders it. It REFUSES (exit 1, writing nothing)
when the mandate may not ship — the evidence gate below its threshold, or a blocking challenge open — and when the
draft cites a finding that does not exist, belongs to another mandate, or is superseded or withdrawn. Otherwise it
writes one self-contained HTML file in which every citation carries its finding's source tier, confidence, epistemic
status and establishment, a provisional finding is marked provisional, and an "Objections that stand" section lists
every open material or minor challenge against a cited finding — tier, confidence and standing objections stay
inside the document, where a reader meets them. Frontmatter records the gate and every finding cited.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAP = HERE.parent
sys.path.insert(0, str(CAP / "views"))
sys.path.insert(0, str(CAP / "validator" / "scripts"))
from _research import BASE_CSS, CITE, TOKENS, Facility, esc, md, split_front, to_date  # noqa: E402
import check as checker  # noqa: E402

def render(fx: Facility, mid: str, draft: str) -> dict:
    m = fx.mandate.get(mid)
    if not m:
        return {"refused": [f"no mandate {mid}"]}
    g = checker.gate_report(fx, m)
    refusals = []
    if g["verdict"] != "pass":
        refusals.append(f"the evidence gate: {g['verdict']} (primary share {g['primary_share']} against {g['threshold']})")
    refusals += [f"blocking challenge {c} is open" for c in g["blocking_challenges"]]
    front, body = split_front(draft)
    cited = sorted({i.strip() for mm in CITE.finditer(body) for i in mm.group(1).split(",")})
    for fid in cited:
        f = fx.by_id.get(fid)
        if not f:
            refusals.append(f"the draft cites {fid}, which does not exist")
        elif f.get("mandate_id") != mid:
            refusals.append(f"the draft cites {fid}, which belongs to {f.get('mandate_id')}")
        elif fx.superseded(f):
            refusals.append(f"the draft cites {fid}, superseded by {fx.superseded_by[fid]} — cite the current finding")
        elif f.get("status") == "withdrawn":
            refusals.append(f"the draft cites {fid}, which is withdrawn")
    if not cited:
        refusals.append("the draft cites no finding — a deliverable keeps its evidence")
    if refusals:
        return {"refused": refusals, "gate": g}

    def badge(fid):
        f = fx.by_id[fid]
        prov = f.get("status") != "established"
        return (f'<span class="cite{" prov" if prov else ""}" title="{esc(f.get("claim"))}"><b>{esc(fid)}</b> {esc(f.get("source_tier"))} · {esc(f.get("confidence"))}'
                f' · {esc(f.get("epistemic_status"))}{" · provisional" if prov else ""}</span>')
    standing = [c for c in fx.challenges if c.get("finding_id") in cited and c.get("status") == "open" and c.get("severity") in ("material", "minor")]
    objections = "".join(f'<li><b>{esc(c["id"])}</b> against {esc(c["finding_id"])} — {esc(c.get("kind"))}, {esc(c.get("severity"))}: {esc(c.get("argument"))}</li>' for c in standing)
    title = m.get("headline") or mid
    share = "—" if g["primary_share"] is None else f"{round(100 * g['primary_share'])}%"
    css = (".cite{font-family:var(--mono);font-size:.72rem;border:1px solid var(--line);border-radius:4px;padding:0 5px;margin:0 2px;white-space:nowrap;color:var(--muted)}"
           ".cite b{color:var(--accent);font-weight:500}.cite.prov{border-style:dashed;color:var(--warn)}h2{font-family:var(--serif);margin-top:32px}"
           ".objections{border-left:3px solid var(--warn);background:var(--warn-soft);padding:10px 16px;border-radius:0 6px 6px 0}")
    doc = (f"<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
           f"<title>{esc(title)}</title><style>{TOKENS}{BASE_CSS}{css}</style></head><body><div class=\"wrap\">"
           f"<div class=\"eyebrow\">research deliverable · {esc(mid)} · generated {esc(str(fx.today))}</div>"
           f"<p class=\"cites\">Evidence gate: primary share {share} of {g['established']} established finding(s) against {round(100 * g['threshold'])}% · "
           f"{g['provisional']} provisional · {len(cited)} finding(s) cited · no blocking challenge open.</p>"
           f"{md(body, badge)}"
           + (f"<h2>Objections that stand</h2><div class=\"objections\"><ul>{objections}</ul></div>" if objections else "")
           + "</div></body></html>\n")
    meta = {"kind": "research-deliverable", "mandate_id": mid, "generated_at": str(fx.today), "generator": "research-brief",
            "gate": {k: g[k] for k in ("primary_share", "threshold", "established", "provisional")}, "findings": cited,
            "challenges_open": [c["id"] for c in standing]}
    return {"html": doc, "meta": meta, "gate": g}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    ap.add_argument("mandate")
    ap.add_argument("--draft", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--as-of")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    fac = Path(a.facility)
    fx = Facility(fac if (fac / "manifest.yaml").exists() else fac / "project-state", to_date(a.as_of) or dt.date.today())
    res = render(fx, a.mandate, Path(a.draft).read_text(encoding="utf-8"))
    if "refused" in res:
        if a.json:
            print(json.dumps({"refused": res["refused"]}, indent=1))
        else:
            print(f"render: refused — {a.mandate} may not ship:")
            for r in res["refused"]:
                print(f"  ✗ {r}")
        return 1
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(res["html"], encoding="utf-8")
    print(json.dumps(res["meta"], indent=1) if a.json else f"render: {a.out} — {len(res['meta']['findings'])} finding(s) cited, {len(res['meta']['challenges_open'])} objection(s) disclosed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
