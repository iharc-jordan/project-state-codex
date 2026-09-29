---
kind: winloss-analysis
generated_at: YYYY-MM-DD
generator: intel-winloss
window: {from: YYYY-MM-DD, to: YYYY-MM-DD}
sample: {records: 0, wins: 0, losses: 0, no_decision: 0, with_buyer_evidence: 0}
divergence: {pairs: 0, diverged: 0, rate: ~}          # records with both reasons whose categories differ
records: []                                           # every INT-W id counted
claims: []                                            # every INT-C id cited
---

# Win-loss — <window>

<!-- The numbers in this file come from `python3 capabilities/intel/scripts/winloss.py <facility> --json`.
     Every pattern states its sample ("lost on price in 3 of 4 enterprise deals where X was present");
     a pattern that differs between segments is reported per segment, never as one line. -->

## Sample
Records, outcomes, how many carry buyer evidence. Below three records in a cell, a pattern is anecdote and says so.

## What sellers say vs what buyers say
The divergence rate, and the reason categories where it concentrates. This is a finding about the sales
organisation, not only about competitors. [INT-W-…]

## Patterns, by segment
One subsection per segment with n ≥ 2. Each pattern: the count, the base, the competitor, the reason
category, the evidence [INT-W-…, INT-C-…].

## Against each competitor
Wins and losses per competitor, and the reasons the buyers gave. [INT-W-…]

## Objections and product gaps heard
The objection and product-gap claims these records wrote, with how many deals each came from. [INT-C-…]

## What we do not know
Losses with no buyer evidence yet, segments too small to read, competitors unnamed.

## Recommended actions
Owned, specific: which battlecard to regenerate, which gap goes to product, which interviews to book.
