#!/usr/bin/env python3
"""winloss — the numbers behind an intel-winloss analysis (OCI win-loss-analyzer, capabilities/intel/README.md).

    python3 winloss.py <facility> [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--as-of YYYY-MM-DD] [--json]

Reads intel/winloss/INT-W-*.yaml (and the claims they generated) and computes what OCI §7.5 requires of any
aggregate: the sample behind every pattern, the divergence between what sellers recorded and what buyers
evidenced, and patterns segmented before they are generalised. A pattern whose direction differs between
segments is reported per segment and flagged, never as one line. Below `competitive.winloss.min_sample`
records a pattern is anecdote and is labelled so.

Reads only; the skill writes the analysis projection (intel/reports/winloss-*.md) from this output.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intel_lib import Facility, to_date  # noqa: E402


def reason(rec, side):
    r = rec.get(side)
    return r.get("category") if isinstance(r, dict) and r.get("statement") else None


def analyse(f: Facility, since=None, until=None):
    min_sample = int(((f.comp.get("winloss") or {}).get("min_sample")) or 3)
    until = until or f.as_of
    recs = [r for r in f.winloss.values() if (d := to_date(r.get("closed_at"))) and (since is None or d >= since) and d <= until]
    recs.sort(key=lambda r: (str(r.get("closed_at")), r["id"]))
    outcomes = Counter(r.get("outcome") for r in recs)
    with_buyer = [r for r in recs if reason(r, "buyer_evidenced_reason")]
    pairs = [r for r in with_buyer if reason(r, "seller_reported_reason")]
    diverged = [r for r in pairs if reason(r, "seller_reported_reason") != reason(r, "buyer_evidenced_reason")]
    # where the divergence concentrates: seller category → buyer category
    flows = Counter((reason(r, "seller_reported_reason"), reason(r, "buyer_evidenced_reason")) for r in diverged)

    seg = lambda r: r.get("segment") or "unsegmented"  # noqa: E731
    # The reason a pattern counts: the buyer's where there is buyer evidence, else the seller's, marked seller-only.
    def best(r):
        b = reason(r, "buyer_evidenced_reason")
        return (b, "buyer") if b else (reason(r, "seller_reported_reason"), "seller-only")

    cells = defaultdict(list)  # (segment, competitor, outcome) → records
    for r in recs:
        cells[(seg(r), r.get("competitor") or "unknown", r.get("outcome"))].append(r)
    patterns = []
    for (s, comp, outcome), rs in sorted(cells.items()):
        n = len(rs)
        by = Counter(best(r)[0] for r in rs)
        for cat, k in by.most_common():
            evidence = [r["id"] for r in rs if best(r)[0] == cat]
            seller_only = sum(1 for r in rs if best(r)[0] == cat and best(r)[1] == "seller-only")
            patterns.append({"segment": s, "competitor": comp, "competitor_name": f.name(comp) if comp != "unknown" else "an unnamed competitor", "outcome": outcome,
                             "reason": cat, "k": k, "n": n, "share": round(k / n, 2), "anecdote": n < min_sample, "seller_only": seller_only, "records": evidence,
                             "text": f"{'lost' if outcome == 'loss' else 'won' if outcome == 'win' else 'no decision'} on {cat} in {k} of {n} {s} deal(s) against {f.name(comp) if comp != 'unknown' else 'an unnamed competitor'}"
                                     + (" — anecdote (below the minimum sample)" if n < min_sample else "") + (f" — {seller_only} on the seller's word only" if seller_only else "")})
    # Segment before generalising: a reason whose share on an outcome differs sharply between segments (each n ≥ 2)
    reversals = []
    for outcome in ("loss", "win"):
        seg_n = Counter(seg(r) for r in recs if r.get("outcome") == outcome)
        for cat in {best(r)[0] for r in recs if r.get("outcome") == outcome}:
            shares = {s: sum(1 for r in recs if r.get("outcome") == outcome and seg(r) == s and best(r)[0] == cat) / n for s, n in seg_n.items() if n >= 2}
            if len(shares) >= 2 and max(shares.values()) >= 0.5 and min(shares.values()) <= 0.2:
                reversals.append({"outcome": outcome, "reason": cat, "shares": {s: round(v, 2) for s, v in shares.items()},
                                  "text": f"'{cat}' on {'losses' if outcome == 'loss' else 'wins'} differs by segment ({', '.join(f'{s} {round(100 * v)}%' for s, v in sorted(shares.items()))}) — report per segment, never as one pattern"})
    # objections and gaps heard: the claims these records wrote
    heard = defaultdict(lambda: {"deals": set(), "statement": None, "category": None})
    for r in recs:
        for cid in r.get("claims_generated") or []:
            c = f.claims.get(cid)
            if c and c.get("category") in ("objection", "product-gap", "sales-tactic", "win-loss"):
                h = heard[cid]
                h["deals"].add(r["id"]); h["statement"] = c.get("statement"); h["category"] = c.get("category")
    per_comp = defaultdict(Counter)
    for r in recs:
        per_comp[r.get("competitor") or "unknown"][r.get("outcome")] += 1
    return {
        "as_of": str(f.as_of), "window": {"from": str(since) if since else (str(recs[0]["closed_at"]) if recs else None), "to": str(until)}, "min_sample": min_sample,
        "sample": {"records": len(recs), "wins": outcomes.get("win", 0), "losses": outcomes.get("loss", 0), "no_decision": outcomes.get("no-decision", 0), "with_buyer_evidence": len(with_buyer)},
        "divergence": {"pairs": len(pairs), "diverged": len(diverged), "rate": round(len(diverged) / len(pairs), 2) if pairs else None,
                       "flows": [{"seller": s, "buyer": b, "n": n} for (s, b), n in flows.most_common()],
                       "seller_said_price_buyer_did_not": sum(1 for r in diverged if reason(r, "seller_reported_reason") == "price")},
        "patterns": patterns, "reversals": reversals,
        "by_competitor": [{"competitor": c, "name": f.name(c) if c != "unknown" else "unnamed", **dict(v)} for c, v in sorted(per_comp.items())],
        "heard": [{"claim": cid, "category": h["category"], "statement": h["statement"], "deals": sorted(h["deals"])} for cid, h in sorted(heard.items())],
        "no_buyer_evidence": [{"id": r["id"], "deal_ref": r.get("deal_ref"), "outcome": r.get("outcome"), "closed_at": str(r.get("closed_at")),
                               "days_since_close": (f.as_of - to_date(r.get("closed_at"))).days} for r in recs if not reason(r, "buyer_evidenced_reason")],
        "records": [r["id"] for r in recs],
        "claims": sorted({cid for r in recs for cid in (r.get("claims_generated") or [])}),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facility")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--as-of")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    f = Facility(a.facility, a.as_of)
    out = analyse(f, to_date(a.since) if a.since else None, to_date(a.until) if a.until else None)
    if a.json:
        print(json.dumps(out, indent=1, default=str))
        return 0
    s, d = out["sample"], out["divergence"]
    print(f"win-loss {out['window']['from']} → {out['window']['to']}: {s['records']} records ({s['wins']} won, {s['losses']} lost, {s['no_decision']} no decision), {s['with_buyer_evidence']} with buyer evidence")
    print(f"  divergence: {d['diverged']} of {d['pairs']} records where both reasons are known" + (f" ({round(100 * d['rate'])}%)" if d["rate"] is not None else "") + f"; seller said price and the buyer did not: {d['seller_said_price_buyer_did_not']}")
    for p in out["patterns"]:
        print(f"  · {p['text']}  [{', '.join(p['records'])}]")
    for r in out["reversals"]:
        print(f"  ! {r['text']}")
    for r in out["no_buyer_evidence"]:
        print(f"  ? {r['id']} {r['deal_ref']} ({r['outcome']}, closed {r['closed_at']}): no buyer evidence yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
