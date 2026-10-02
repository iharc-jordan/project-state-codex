# validate-intel — the intel capability's validator

Composed with the core validator by `project-state validate`; may fail only records in
the `intel` namespace (the bundled capability contract). Checks, in order:

1. **Enablement coherence.** `capabilities.intel` block present and `enabled: true|false`
   well-formed; `focus` non-empty and not the literal `REQUIRED`; `version:` compared to
   the installed plugin version — warn on drift, never fail.
2. **Directory shape.** `intel/{entities,signals,mandates,network,reports}` exist;
   `intel/agenda.yaml` parses; `state/intel.json` parses.
3. **Ids and counters.** Every file matches its kind's id format (`INT-E-NNN` etc.);
   filename equals `id:`; `state/intel.json` counters ≥ the highest id seen — fail on a
   counter behind the files (id collision risk), warn on a counter far ahead.
4. **Required fields and enums** per `schema/entities.yaml`, with `type` validated against
   the manifest block's declared `entity_types` / `mandate_types`.
5. **References.** Every `entities_referenced[]` id and every mandate `entity_id` resolves
   to an existing entity — fail on orphans. `became:` targets resolve to existing risks,
   decisions, or registered documents — warn on orphans (the target may live in a
   not-yet-pulled branch).
6. **Append-only signals.** A signal whose content hash changed after creation (where the
   host tracks it) or whose `created:` postdates a referencing record is flagged. The
   convention is supersede-with-reference, never edit.
7. **Agenda hygiene.** Every question marked answered cites at least one signal id that
   exists.


## Competitive layer (intel 1.1 — capabilities/intel/README.md)

8. **Competitive block.** `competitive.self_entity`, when set (scalar or one-element list),
   resolves to an entity of type `self`; every `competitors[]` id resolves; `half_lives_days`
   has an entry for every category in use across `intel/claims/`.
9. **Claims.** Required fields and enums per `schema/entities.yaml` (`intel-claim`);
   `subject.entity` resolves; `material: true` requires `source.ref` and either `excerpt` or
   `epistemic_status: unknown`; `verified` requires a source class other than `inference`;
   `derived_from`, when set, resolves to a signal; `retrieved_at` ≥ `source_date`.
10. **Supersession integrity.** Every `supersedes` target exists, is older, and the chain has
    no cycle; a superseded claim is not cited as current by a projection whose
    `generated_at` postdates the supersession — fail.
11. **Conflicts symmetric.** `conflicts_with` appears on both claims — fail on a one-sided
    conflict; list contested categories, do not resolve them.
12. **Append-only claims and changes.** Content hash unchanged since creation where the host
    tracks it (as check 6 for signals).
13. **Projection citations.** For every file under `intel/profiles`, `intel/battlecards`,
    `intel/deals/*/brief.md`, `intel/reports/brief-*.md`: every `[INT-C-…]` in the body
    resolves; frontmatter `claims:` equals the set cited; a battlecard's
    `health.unsourced_lines` is 0; a file whose sha256 differs from
    `state/intel.json → projections[path].sha256` is a **fork** — warn, name the file, say
    "put the correction in the claim set and regenerate".
14. **Change events.** `before[]` are claims that are superseded; `after[]` are the claims
    that supersede them; `significance` is an enum value.
15. **Lineage.** `became:` on claims resolves like check 5 — warn on orphans.

Report findings plainly; fix nothing silently.


## Monitor and win-loss (intel 1.2 — capabilities/intel/README.md)

16. **Watch list.** `intel/watch.yaml` parses; every source has a unique `id`, an `entity` that
    resolves, a `via` from the connector capabilities (`web.read`, `documents.search`,
    `deals.read`, `messages.search`, `mail.search`), and `categories` from the claim taxonomy;
    `status` is `active`, `paused` or `retired` (a retired source stays listed). Warn on a
    cursor in `state/intel.json → monitor.sources` with no source of that id.
17. **Monitor provenance.** A claim `logged_by: intel-monitor` cites a `source.ref` equal to a
    watched source's `ref` (or, for `deals.read` / `documents.search`, a file the source covers);
    a change event `detected_by: intel-monitor` has non-empty `affected` and
    `recommended_action` unless its significance is `noise` — an event nobody owns is noise.
18. **Win-loss records.** Required fields and enums per `schema/entities.yaml` (`intel-winloss`);
    `outcome` ∈ win · loss · no-decision; `seller_reported_reason.category` and
    `buyer_evidenced_reason.category` from the reason taxonomy plus the manifest's
    `reason_categories_extra`; `competitor`, when set, resolves to an entity; `buyer_evidenced_reason`,
    when set, carries a `source.ref` and a source class other than `internal-observation`
    (a buyer's reason comes from the buyer — fail otherwise); every `claims_generated` id resolves.
19. **Append-only records.** Only `buyer_evidenced_reason`, `interviews`, `claims_generated` and
    `last_modified` change after creation (the server enforces this on write; the validator
    reports any history that did otherwise). The seller's reason is never rewritten.
20. **Win-loss analyses.** Every `[INT-W-…]` in `intel/reports/winloss-*.md` resolves; the
    frontmatter `sample` and `divergence` equal what `scripts/winloss.py` computes for the stated
    window (fail on a mismatch — the numbers are derived, never authored); `records:` lists every
    record in the window.
21. **Evaluation (L3 claimed).** When `competitive.conformance_target` is `L3`,
    `scripts/eval_metrics.py` over the project passes every OCI §13.2 threshold it can measure —
    report each failing line; the claim of L3 is withdrawn until they pass.
