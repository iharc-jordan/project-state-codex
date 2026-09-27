---
name: intel-ingest
description: "Pull intel from documents dropped in project-state/documents/inbox/ — 'ingest this competitor PDF', 'process the intel docs', 'drain the inbox for intel'. Extracts findings into the intel evidence base."
map:
  tier: capability
  stage: ingest
  reads: [documents, manifest]
  writes: [intel, log]
---

# intel-ingest — the inbox drainer

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Drain intel-relevant documents from the project's shared inbox (project-state/documents/inbox/) — PDFs, markdown, images, CSVs, URL lists, and docs deposited by project-harvester. Read each file, extract findings relevant to capabilities.intel.focus, create append-only INT-S signals via project-state, update entity key_facts, propose new entities (never auto-create), mark answered agenda questions, and hand the document on to the normal documents pipeline so signals can cite the registered doc. Use when the user says 'ingest the inbox', 'process the dropped docs for intel', 'drain the intel inbox', 'I dropped files for intelligence', or when the digest reports intel.inbox-waiting. There is no intel/inbox/ — the house inbox is the only inbox. Requires the intel capability enabled with a declared focus.

Every intel-relevant file in `documents/inbox/` is a potential source of signals. One
inbox for the whole project: operator drops and `project-harvester` deposits land in the
same place, and this skill drains the intel-classified ones.

## Step 1 — Context

Via `project-state`: read `capabilities.intel` (refuse if disabled or `focus` missing),
the entity list (id, name, type) for matching, `intel/agenda.yaml` for
answerable questions, and `state/intel.json` counters.

## Step 2 — Enumerate

List `documents/inbox/` (skip `processed/`, dotfiles). Take files that are
intel-classified by `project-inbox` triage, deposited by `project-harvester` as intel,
or named by the user. Oldest first. Empty → "Inbox holds nothing for intel." and stop.

## Step 3 — Per file

1. **Read** — PDF/markdown/text/CSV via Read; images via vision; `.url`/`.urls` files
   fetch each listed URL.
2. **Extract findings** against the focus. Per distinct finding: summary (what was
   learned, why it matters; inferences marked as inferences), `signal_type`,
   `intelligence_value` (high = changes strategy, medium = context, low = background),
   entity matches, new-entity candidacy, agenda questions answered. Skip promotional
   fluff; a file with zero findings still moves on, noted "no actionable intel."
3. **Write signals** via `project-state` — one per finding, `source: document_inbox`,
   `logged_by: intel-ingest`, `source_url:` the inbox filename; event
   `intel.signal.logged`.
4. **Update entities** — new key_facts and research questions via `project-state`
   (`intel.entity.updated`).
5. **Propose new entities** — collected and presented at the end; created only on
   confirmation.
6. **Hand the document on** — it proceeds through the normal pipeline
   (`project-document-curator` registration or `processed/` archival per house inbox
   rules); once registered, add the doc id to each signal's `became:`/citation edge.

## Step 4 — Report

Files processed · signals by value · entities updated · candidates pending approval ·
agenda questions answered (event `intel.inbox.drained`). Then re-render the declared report so
the app's Intel page reflects what was just ingested:

```bash
python3 capabilities/intel/views/build-intel-glance.py <facility>/project-state
```

## Subcommands

`drain` (default) · `peek` (list without processing) · `file <name>` (one file).

## Discipline

One signal per finding · never fabricate · propose entities, never auto-create · signals
are append-only · everything through `project-state`.
