#!/usr/bin/env python3
"""promote — render a finding as an intel proposal for the house inbox (docs/RESEARCH-CAPABILITY-SPEC.md §6.12).

    python3 promote.py <facility> RES-F-NNN [--entity INT-E-NNN|"name"] [--as-of YYYY-MM-DD]

Prints templates/intel-proposal.md filled from the finding, and the path it belongs at
(documents/inbox/research-promotion-<RES-F id>.md). research-mandate promote writes it there through project-state —
the ONLY write a promotion makes. intel-ingest drains it into an intel claim that cites the finding; the finding then
gains a became: edge. Refuses (exit 1) when intel is not enabled on the project, when capabilities.research.crossings.
intel is `off`, or when the finding is superseded, withdrawn or still provisional (only established evidence crosses).
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAP = HERE.parent
sys.path.insert(0, str(CAP / "views"))
from _research import Facility, to_date  # noqa: E402

# research category → intel claim category (INTEL-CI-SPEC §3.7); unmapped categories go to intel as `market`
INTEL_CATEGORY = {"pricing": "pricing", "offering": "product", "technology": "product", "organisation": "leadership", "programme": "partnership",
                  "market": "market", "statistic": "market", "regulation": "compliance", "event": "go-to-market", "literature": "market", "method": "product"}
# research source tier → intel source class (INTEL-CI-SPEC §3.8)
INTEL_CLASS = {"primary": "vendor-primary", "secondary": "press", "tertiary": "third-party-research", "speculative": "inference"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    ap.add_argument("finding")
    ap.add_argument("--entity", default=None)
    ap.add_argument("--as-of")
    a = ap.parse_args(argv)
    fac = Path(a.facility)
    fx = Facility(fac if (fac / "manifest.yaml").exists() else fac / "project-state", to_date(a.as_of) or dt.date.today())
    caps = fx.manifest.get("capabilities") or {}
    intel = caps.get("intel") or {}
    why = None
    if not intel or intel.get("enabled") is False:
        why = "intel is not enabled on this project — a promotion has nowhere to land"
    elif str((fx.cap.get("crossings") or {}).get("intel", "auto")) == "off":
        why = "capabilities.research.crossings.intel is off"
    f = fx.by_id.get(a.finding)
    if not f:
        why = why or f"no finding {a.finding}"
    elif fx.superseded(f):
        why = why or f"{a.finding} is superseded by {fx.superseded_by[a.finding]} — promote the current finding"
    elif f.get("status") != "established":
        why = why or f"{a.finding} is {f.get('status')} — only established evidence crosses into intel"
    if why:
        print(f"promote: refused — {why}", file=sys.stderr)
        return 1
    tpl = (CAP / "templates" / "intel-proposal.md").read_text(encoding="utf-8")
    body = tpl.split("-->", 1)[1].lstrip("\n") if "-->" in tpl else tpl.split("---\n", 2)[2]
    ev = "\n".join(f"- \"{e.get('excerpt') or ''}\" — {e.get('ref')} (source date {e.get('source_date') or '?'})" for e in f.get("evidence") or [] if isinstance(e, dict))
    epi = f.get("epistemic_status")
    front = (f"---\nkind: research-promotion\ntarget: intel\nproposed_by: research-mandate\nfinding: {f['id']}\nmandate: {f.get('mandate_id')}\n"
             f"entity_hint: \"{a.entity or 'for intel to resolve'}\"\nproposed_at: {fx.today}\n---\n\n")
    body = (body.replace("<one-line claim>", f["claim"]).replace("<the finding's claim>", f["claim"]).replace("<each evidence item: excerpt, ref, source date>", "\n" + ev)
            .replace("<tier>", str(f.get("source_tier"))).replace("<confidence>", str(f.get("confidence"))).replace("<status>", str(epi), 1)
            .replace("<n>", str(f.get("independent_sources"))).replace("<provisional|established>", str(f.get("status")))
            .replace("<intel category>", INTEL_CATEGORY.get(str(f.get("category")), "market")).replace("<mapped>", str(epi), 1)
            .replace("<mapped>", INTEL_CLASS.get(str(f.get("source_tier")), "inference")).replace("<RES-F id>", f["id"])
            .replace("<RES-M id>", str(f.get("mandate_id"))).replace("<RES-S id>", str(f.get("step_id"))))
    print(f"# → documents/inbox/research-promotion-{f['id']}.md", file=sys.stderr)
    print(front + body, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
