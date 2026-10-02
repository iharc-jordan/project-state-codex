# validate-tender — the tender capability's validator

**Executable implementation:** [`validate_tender_state.py`](validate_tender_state.py) — the
original build's working validator (report-only, exit 0/1/2), folded in from the retired
root `templates/tender/` set. This document is the contract; the script is the runner.
Where they disagree, fix the script to match this contract.

Composed with the core validator by `project-state validate`; may fail only records in the
`tender` namespace (the bundled capability contract). Checks, in order:

1. **Enablement coherence.** `capabilities.tender` block well-formed;
   `mailbox_label` non-empty and not the literal `REQUIRED`; `version:` vs the installed
   plugin — warn on drift, never fail.
2. **Directory shape.** `tenders/`, `tenders/profiles/`, `tenders/events.ndjson`,
   `documents/inbox/quarantine/`, `state/tender.json` exist and parse.
3. **Tender records.** Filename equals `id:`; id matches `t-<year>-<seq>`;
   `workflow.status` is in the lifecycle enum; required fields present; counters in the
   state file ≥ the highest sequence seen (fail behind — id collision risk).
4. **Profiles.** Every enabled profile's matching weights sum to 100; every id in
   `profiles_enabled` resolves to a profile file.
5. **Event log integrity.** `tenders/events.ndjson` lines parse; each carries ts, actor,
   event (from `schema/events.yaml`), id resolving to an existing tender; corrections use
   `superseded_ts`, never rewrites — flag any event whose target id does not exist.
6. **Lifecycle discipline.** Every tender in a post-decision status (`pursue` onward) has a
   corresponding bid/no-bid facility decision; every `dismissed` tender carries a reason
   code; every `awarded` tender with a handoff has `tender.handoff.completed` on the log.
7. **Human reservations.** Any `human_approved` field that is set traces to a human actor
   in the activity log — an agent-attributed write there is a failure, not a warning.
8. **Connector state.** Each `tender_connectors` entry carries cursor + last_success +
   health; unknown connector ids (not in the manifest block's `sources`) are warned.

Report findings plainly; fix nothing silently.
