# Project State Codex Lean Adaptation

## Baseline and repository contract

This branch adapts Atomic 47 Labs Project State public v4.9.0 at commit
[`c0b55ba52dfdca9312a1f6150039ed14d569e2db`](https://github.com/Atomic-47-Labs/project-state-plugin-public/commit/c0b55ba52dfdca9312a1f6150039ed14d569e2db)
for Codex while preserving the public Project State deliverable contract.

- `upstream` is `https://github.com/Atomic-47-Labs/project-state-plugin-public.git`.
- `origin` is the independent public adaptation repository
  `https://github.com/iharc-jordan/project-state-codex.git`.
- `main` is the public default and only long-lived branch. It contains the
  upstream baseline followed by the documented Codex adaptation commits.
- `upstream-v4.9.0` remains exactly at the upstream baseline.
- `codex-v4.9.0-lean.1` identifies the first validated adaptation revision.
- `codex-v4.9.0-lean.2` identifies the public-sharing documentation revision;
  it changes no Project State runtime contract. Tags are immutable.
- `codex-v4.9.0-lean.3` identifies the Codex-only, single-branch distribution.
- `codex-v4.9.0-lean.4` identifies the scale-proportional, idempotent,
  reconciliation-aware operating contract while preserving every public
  Project State interface.
- Atomic47 attribution, upstream links, and the MIT license are retained.

The repository began as an independent private mirror because GitHub does not
support making a private fork of a public repository. It was made public for
sharing with Atomic47 after the adaptation was validated. It is not presented
as an official Atomic47 fork or upstream release.

## Preserved public interface

The adaptation preserves the Project State runtime interface: all 43 skill
names and automatic discovery, the
`project-state/` and `grant-state/` layouts, schemas, IDs, event vocabulary,
logs, reports, templates, eight packs, two capabilities, and bundled assets.
Reporting-matrix triggers, pack-required triggers, Git sharing, provenance, and
external-review safeguards remain operative.

The compatibility changes are intentionally narrow:

- optional or unconfigured skills no longer fan out automatically;
- one report owner handles one source event and reporting period;
- unavailable private dashboards, services, helper skills, and connector names
  are treated as optional integrations rather than bundled dependencies;
- the deprecated document-suite entrypoint forwards once to the already-current
  unified suite instead of maintaining a second generator;
- `automation/tasks.yaml` is the sole current automation registry;
- Claude/Coworker presentation instructions are replaced by normal Codex
  Markdown interaction without removing any data field or approval rule;
- the Claude marketplace and plugin manifests are not shipped on `main`; the
  exact upstream distribution remains available at `upstream-v4.9.0` and in
  Atomic47's public repository;
- the ten dangling `docs/*.md` references found in the public baseline are
  removed, inlined from existing public invariants, or marked unsupported when
  their only implementation was private.

No Project State manifest field, alternate state format, connector, or hosted
gate was added.

## Scale-proportional operating contract

Project State records shared project meaning, not every code change or
individual task. Scale is determined at runtime from the operator request and
supplied repository evidence; it is deliberately not a required manifest field.

- A **task** remains in the active Codex task and configured issue tracker. It
  does not scaffold or write Project State unless it changes a shared API/data/
  architecture contract, milestone, durable decision/risk, compliance or
  reporting obligation, governed phase, or release boundary, or the operator
  explicitly requests a reasoned Project State record.
- An **epic** represents one shared outcome with only meaningful milestones,
  durable decisions/risks, stable external references, and revision-keyed
  evidence.
- A **program** may use the complete facility for multi-developer objectives,
  rollups, reporting, compliance, and provenance.

Explicit initialization still creates the existing standard tree and schema.
Source-first intake asks only unresolved required, pack-driven, or
routing-critical questions and does not populate speculative entities.

New canonical events retain `ts`, `actor`, `event`, `id`, and `summary`.
Idempotent evidence, reports, and deliveries derive deterministic identities
from their existing event/entity/revision/period/owner inputs and reuse the
existing `id` contract. Exact repeats return the existing record and do not
append, increment, advance pointers, regenerate, or notify. Legacy duplicates
and aliases remain readable. No `dedupe_key`, `source_revision`, `supersedes`,
second event index, or clone request ledger was added.

`state.json` remains at the same path and schema. Unique entity counters and
`last_activity` are mechanical projections. Phase is governed by the manifest
and successful explicit lifecycle/transition operations, with disagreement
reported instead of inferred from milestones. The automation registry timezone
mirrors the manifest; null/mismatch is reported rather than guessed. Default
health reflects material delivery, reporting, compliance, security, and
production-path risk; development-only advisories remain visible but do not
independently lower health. Terminal closeout and continuous increments are
reconciled explicitly. Validation/reconciliation is dry-run by default and any
repair remains an explicit canonical write.

Material implementation-linked state normally travels with its code through an
ordinary branch/PR and protected/default-branch merge. State-only commits remain
valid for meetings, decisions, reports, governance, and post-commit evidence.
The merge is the cross-clone serialization point: stale bases, duplicate
deterministic event IDs, and incompatible same-entity edits require explicit
resolution. Lockfiles and `merge=union` do not solve cross-clone semantics, and
no parallel change-request ledger exists.

External ticket/document systems retain full bodies, comments, and source
content. Project State stores stable references, provenance, required status
snapshots, and managed copies only when a pack/output contract requires them.
Routine list/activity/status reads use bounded summaries, filters, limits, and
cursors before explicit detail reads. Deep documentation and historical scans
remain available when explicitly requested or contractually triggered.

## Redundancies removed

The adaptation does not remove Project State's shared project ledger. It removes
places where the public Claude package would otherwise duplicate state or
process already owned by Codex, the repository, an issue tracker, or a canonical
document store.

| Redundant overlap | Canonical owner after adaptation | What Project State still owns |
|---|---|---|
| Personal preferences and recurring operator habits copied into project files | Codex Memories | Checked-in shared project facts; memory can never override them. |
| Repository commands, coding rules, release requirements, and execution constraints repeated in project state | The nearest `AGENTS.md` | Project objectives, milestones, decisions, risks, reporting obligations, and compliance evidence. |
| Temporary implementation objectives and conversational completion state persisted as durable project facts | The active Codex task or Goal | Durable objective and milestone rollups needed by the wider project or its reports. |
| Full engineering tickets copied into Project State | Jira, GitHub, or Linear when configured | Stable ticket references, cross-ticket milestone rollups, decisions, risks, and reporting context. |
| Full source documents copied into the ledger by default | Their canonical drive or repository | Document inventory, stable references, provenance, status, and a managed copy only when a pack explicitly requires one. |
| Reports treated as another source of truth | Canonical Project State entities | Reports remain derived views; a new fact found while reporting is first written to its canonical entity. |
| Several writers creating parallel forms of the same project fact | `project-state` as the only canonical entity and ledger mutation gateway | Report and automation generators may write their owned derived artifacts, then record the pointer and activity event through `project-state`. |
| Multiple report generators reacting to the same event | One report owner selected by output type, source event, and reporting period | Every configured report path and format remains available, but it is generated once. |
| Orchestrator-driven report fan-out on ordinary reads | Read-only orchestration by default | A generator runs only after operator acceptance, a due enabled reporting-matrix entry, or an active pack requirement. |
| Current and retired automation registries both presented as authoritative | `automation/tasks.yaml` | Existing automation behavior and logs remain; retired `automation/schedule.yaml` guidance is not regenerated. |
| A legacy document-suite generator alongside the unified suite | `project-doc-suite` | `project-doc-suite-generator` remains discoverable only as a forwarding alias, so callers retain compatibility without a second implementation. |
| Optional skills activating merely because they are discoverable | Applicable pack, capability, configured surface, due matrix entry, or explicit request | All skill entrypoints remain discoverable and available when their prerequisites exist. |
| Long onboarding questionnaires before examining available evidence | Supplied repository files and canonical source documents first | Only unresolved required, pack-driven, or routing-critical questions are asked, with source attribution preserved. |
| Advisory lockfiles described as cross-clone Git coordination | Lockfiles for shared-drive/server writers; Git synchronization for separate clones | Project State still supports team sharing, warns on known divergence, and requires explicit same-entity conflict resolution without automatic fetch, pull, commit, or push. |
| Claude/Coworker UI mechanics embedded in operational policy | Normal Codex Markdown interaction | Unique fields, approvals, error conditions, workflow dependencies, and output contracts remain. |
| Dangling links to private documents and assumed Atomic47-only services | Bundled public resources or an explicit unsupported boundary | Public behavior is not invented; configured, available integrations continue to work. |

The practical result is one durable shared ledger rather than a second personal
memory, task list, ticket database, document store, automation registry, and set
of competing reports. A team can still share the ledger through Git or a
properly coordinated shared filesystem; the adaptation only makes ownership and
conflict behavior explicit.

## Codex packaging note

The Codex manifest points directly to the preserved upstream payload at
`./plugin/skills/`; no root-level copy or symlink is used. This matters on
Windows because the Codex installation cache does not preserve a tracked
directory symlink. The exact nested-path package is accepted by `codex plugin
add` and exposes all 43 skills in fresh prompt input. The bundled
plugin-creator static helper currently hard-codes `./skills/`, so its remaining
structural checks are run against a temporary canonical-root projection while
the adaptation validator and installed-package probes validate the exact path.
Every skill links back to `plugin/CODEX.md`. The public branch contains no
`.claude-plugin` distribution metadata; the shared runtime payload is not
duplicated or changed by that packaging removal.

## Information ownership and routing

- Codex Memories own personal preferences and recurring operator habits; they
  never override a checked-in project fact.
- `AGENTS.md` owns repository commands, coding rules, release requirements, and
  execution constraints.
- the active Codex task or Goal owns temporary implementation objectives and
  completion state.
- configured Jira, GitHub, or Linear projects own individual engineering items.
- canonical drives and repositories own source-document content.
- Project State owns shared objectives, milestone rollups, decisions, risks,
  phases, stakeholders, reporting obligations, compliance evidence, and report
  provenance.

External records are normally represented by stable references. Reports are
derived views. A durable fact produces one canonical entity update, required
counters or pointers, and one activity event.

Routine reporting maps to one owner:

- routine status, weekly reporting, and SC packs: `project-status-reporter`;
- funder or customer claims: `project-funder-reporting`;
- audience-specific briefs: `project-onepager`;
- full documentation bundles: `project-doc-suite`;
- technical intelligence: `project-tech-reports`;
- public websites: `project-website-publisher`.

The orchestrator remains read-only except when explicit operator acceptance, a
due enabled matrix entry, or an active pack requirement authorizes one generator.
Generators write their owned derived artifacts and log canonical pointers and
events through `project-state`.

## Justification matrix

| ID | change group | affected files | reason | visible compatibility impact | validation | later internal-version disposition |
|---|---|---|---|---|---|---|
| PS-CX-001 | Codex packaging | `.codex-plugin/plugin.json`<br>`plugin/CODEX.md`<br>`plugin/skills/**/SKILL.md` | Add a valid Codex manifest that points directly to the upstream skills payload, adapter policy, and links from every skill. | All 43 public skill names remain discoverable; no payload is duplicated. | Plugin-creator structural projection, exact installed-package validation, 43-skill name-set comparison, fresh-process discovery probe. | Retain for Codex unless the internal package already supplies equivalent native metadata and adapter links. |
| PS-CX-002 | Discovery metadata normalization | `plugin/skills/project-feedback/SKILL.md`<br>`plugin/skills/project-goal-tracker/SKILL.md`<br>`plugin/skills/project-onepager/SKILL.md`<br>`plugin/skills/project-phase-gate/SKILL.md`<br>`plugin/skills/project-tech-reports/SKILL.md` | Make five oversized or stale descriptions valid and precise for automatic discovery. | Skill names, triggers, inputs, and outputs are unchanged; routing becomes less eager. | Quick validation and representative single-owner routing probes. | Compare with internal descriptions and retain only Codex-specific precision still needed. |
| PS-CX-003 | Cross-platform and provider-neutral execution | `plugin/skills/mindmap-vibe/**`<br>`plugin/skills/project-jira-publisher/**`<br>`plugin/skills/tender-harvester/**`<br>`plugin/skills/project-website-publisher/SKILL.md` | Preserve Windows support, safe archive extraction, runtime connector discovery, and truthful unavailable-surface refusal. | Configured outputs are unchanged; unsupported operations fail explicitly. | Python compile, JavaScript syntax, archive traversal inspection, token and path scans. | Retain unless internal adapters provide a portable implementation with the same refusal behavior. |
| PS-CX-004 | Public-package compatibility boundary | `plugin/skills/project-admin/SKILL.md`<br>`plugin/skills/project-feedback/SKILL.md`<br>`plugin/skills/project-harvester/SKILL.md`<br>`plugin/skills/project-onboarder/SKILL.md`<br>`plugin/skills/project-onepager/**` | Remove assumed private dashboards, services, identities, tokens, and hard-coded organization infrastructure while preserving optional integration contracts. | Local and configured workflows remain; unavailable private features are labelled unsupported. | Private URL, token, identity, absolute-path, and unsupported-operation scans. | Classify each boundary against actual internal services before porting. |
| PS-CX-005 | Public resource and error-path repairs | `plugin/skills/grant-ingestor/SKILL.md`<br>`plugin/skills/project-sred-reviewer/SKILL.md`<br>`plugin/skills/project-sred-tracker/SKILL.md`<br>`plugin/skills/sred-onboarding/SKILL.md`<br>`plugin/skills/tender-qualifier/SKILL.md`<br>`plugin/skills/project-review-meeting/SKILL.md` | Resolve resources from the upstream `plugin/` payload and retain missing-workbook, SR&ED, tender, and extraction safeguards. | Same templates, forms, and refusal conditions; paths now resolve in the public package. | Missing-reference audit, protected-path inventory, archive and syntax checks. | Prefer internal canonical resources where present; keep public refusal paths when absent. |
| PS-CX-006 | Canonical ownership | `plugin/CODEX.md`<br>`plugin/skills/project-state/SKILL.md` | Define one owner for preferences, repository rules, temporary goals, tickets, documents, shared project facts, derived reports, and ledger mutations. | No schema change; duplicate representations are prohibited. | Policy invariant scan and representative canonical-write review. | Retain unless the internal contract defines stricter ownership. |
| PS-CX-007 | Lean report routing | `plugin/skills/project-orchestrator/SKILL.md`<br>`plugin/skills/project-status-reporter/SKILL.md`<br>`plugin/skills/project-funder-reporting/SKILL.md`<br>`plugin/skills/project-doc-suite/SKILL.md`<br>`plugin/skills/project-onepager/SKILL.md`<br>`plugin/skills/project-tech-reports/SKILL.md`<br>`plugin/skills/project-website-publisher/SKILL.md` | Assign one report owner and deduplicate by source event, period, and owner. | All configured report paths and formats remain; duplicate fan-out is suppressed. | Required report-path checks and fresh-process routing probes. | Reconcile against internal reporting services and retain the one-owner invariant. |
| PS-CX-008 | Source-first onboarding | `plugin/skills/project-onboarding/SKILL.md`<br>`plugin/skills/project-scaffolder/SKILL.md`<br>`plugin/skills/project-inbox/project-intake/SKILL.md`<br>`plugin/skills/grant-scaffolder/SKILL.md` | Inspect supplied files first, attribute pre-filled values, group unresolved required questions, and avoid inferred objectives, contacts, capabilities, or surfaces. | Scaffold tree and schema are unchanged; questioning is shorter and better attributed. | Quick validation plus read-only onboarding and manifest-resolution probes. | Preserve unless internal intake adds authoritative fields or required questions. |
| PS-CX-009 | Team Git and concurrency truth | `plugin/skills/project-git/SKILL.md`<br>`plugin/skills/project-scaffolder/SKILL.md`<br>`plugin/skills/project-inbox/project-intake/SKILL.md`<br>`plugin/skills/grant-scaffolder/SKILL.md`<br>`plugin/skills/project-harvester/SKILL.md` | Distinguish lockfile coordination from separate clones, warn on known divergence, require same-entity conflict resolution, and keep checkpoints deliberate. | Git sharing remains supported; no automatic fetch, pull, commit, or push is introduced. | Static Git-policy scan and exact command review. | Retain unless the internal platform supplies a stronger transactional writer. |
| PS-CX-010 | Optional capability gates | `plugin/skills/**/SKILL.md` | Require an applicable pack, capability, configured surface, due matrix entry, or explicit request for optional skills. | Automatic discovery stays enabled; unconfigured work stays quiet. | All-skill quick validation and negative prerequisite routing probes. | Re-evaluate against internal pack defaults; retain conditional activation. |
| PS-CX-011 | Codex interaction and prompt-debt cleanup | `plugin/skills/grant-scaffolder/SKILL.md`<br>`plugin/skills/project-scaffolder/SKILL.md`<br>`plugin/skills/project-onboarding/SKILL.md`<br>`plugin/skills/project-inbox/project-intake/SKILL.md`<br>`plugin/skills/sred-onboarding/SKILL.md`<br>`plugin/skills/mindmap-vibe/SKILL.md` | Remove Claude, Coworker, and HTML-artifact mechanics while preserving questions, gates, data fields, approvals, and output summaries. | Presentation becomes Codex-native Markdown; deliverables do not change. | Unsupported Claude-only instruction scan and focused skill validation. | Retain for Codex; internal UI-specific presentation belongs in its own adapter. |
| PS-CX-012 | Missing private references and progressive disclosure | `plugin/capabilities/**`<br>`plugin/packs/**`<br>`plugin/templates/**`<br>`plugin/skills/project-document-curator/SKILL.md`<br>`plugin/skills/project-feedback/SKILL.md`<br>`plugin/skills/project-harvester/SKILL.md`<br>`plugin/skills/project-state/SKILL.md` | Remove ten dangling private-doc links, inline public invariants, and mark private-only protocols unsupported without inventing replacements. | Existing fields, pack rules, event terms, templates, and capability outputs remain. | Protected path-set equality, strict YAML and JSON parsing, missing-reference audit, contract-term checks. | For each internal document, classify as already solved, still required, incompatible, or superseded. |
| PS-CX-013 | Current registry, suite alias, and package metadata | `README.md`<br>`plugin/README.md`<br>`plugin/skills/project-automator/SKILL.md`<br>`plugin/skills/project-doc-suite-generator/SKILL.md`<br>`plugin/skills/project-doc-suite/SKILL.md`<br>`plugin/skills/project-orchestrator/SKILL.md`<br>`plugin/skills/project-status-reporter/SKILL.md`<br>`plugin/skills/project-funder-reporting/SKILL.md`<br>`plugin/templates/manifest-v2.yaml`<br>`plugin/templates/reporting-matrix.yaml` | Make `automation/tasks.yaml`, the unified suite, 43 skills, and eight packs authoritative; forward the deprecated generator once. | Retired baseline generation is not duplicated; its public entrypoint forwards to the established unified-suite owner. | Count, path, registry, alias, strict parse, and routing checks. | Use internal current registries and generators where authoritative; do not restore parallel legacy output. |
| PS-CX-014 | Adaptation evidence | `CODEX-ADAPTATION.md`<br>`scripts/validate_codex_adaptation.py` | Record the compatibility reasoning and provide one read-only repeatable validation entrypoint. | Documentation and checks only. | Self-coverage check requires every changed file and commit to carry a justification ID and required rationale headings. | Carry this matrix into the internal migration and reclassify every row. |
| PS-CX-015 | Codex-only single-branch distribution | `.claude-plugin/**`<br>`plugin/.claude-plugin/**`<br>`README.md`<br>`plugin/README.md`<br>`plugin/packs/pic-pcais/README.md`<br>`plugin/templates/reporting-matrix.yaml`<br>`plugin/capabilities/sred/views/README.md`<br>`plugin/capabilities/sred/views/build-sred-dashboard.mjs`<br>`plugin/skills/project-onepager/examples/**`<br>`scripts/validate_codex_adaptation.py` | Make `main` the single public Codex branch, remove Claude distribution manifests and active Claude-specific help, and retain the exact upstream baseline as a tag instead of a second branch. | Codex discovery and every Project State runtime contract remain; Claude installation routes to the upstream repository, while legacy data values and output flags stay readable. | Absence checks for both Claude manifests, active-instruction scan, strict YAML, JavaScript syntax, 43-skill validation, baseline ancestry, package validation, and remote branch audit. | Reintroduce a host-specific distribution layer only if the internal contract explicitly requires it; do not duplicate the runtime payload. |
| PS-CX-016 | Cross-skill contract drift repair | `plugin/skills/project-inbox/SKILL.md`<br>`plugin/skills/project-inbox/project-intake/SKILL.md`<br>`plugin/skills/project-scaffolder/SKILL.md`<br>`plugin/skills/project-onboarding/SKILL.md`<br>`plugin/skills/project-automator/SKILL.md`<br>`plugin/skills/project-milestone-manager/SKILL.md`<br>`plugin/skills/project-phase-gate/SKILL.md`<br>`plugin/templates/manifest-v2.yaml` | Use canonical event envelopes and entity frontmatter, remove undefined scaffolder fronts and facility-specific claims, and make manifest/tasks timezone projection consistent. | Existing legacy events, facility files, task registries, and the standard scaffold remain readable; no bulk migration occurs. | Canonical-example, cross-skill-command, generic-instruction, strict-parse, timezone-fixture, and protected-template semantic checks. | Retain the checks; reconcile internal commands and schemas before changing any wording. |
| PS-CX-017 | Scale and materiality routing | `plugin/CODEX.md`<br>`plugin/skills/project-state/SKILL.md`<br>`plugin/skills/project-scaffolder/SKILL.md`<br>`plugin/skills/project-onboarding/SKILL.md`<br>`plugin/skills/project-inbox/project-intake/SKILL.md`<br>`plugin/skills/project-change-register/SKILL.md`<br>`plugin/skills/project-feedback/SKILL.md`<br>`plugin/skills/project-goal-tracker/SKILL.md`<br>`plugin/skills/project-milestone-manager/SKILL.md` | Route task, epic, and program operations proportionally and require a shared-fact materiality gate before canonical writes. | Scale is runtime policy, not a manifest field; explicit initialization keeps the established tree/schema and explicit reasoned overrides use existing fields. | In-memory task/epic/program and materiality fixtures, policy scans, all-skill validation, and fresh-process routing probes. | Retain unless an internal router provides the same no-write task behavior without adding persisted scale state. |
| PS-CX-018 | Idempotency, projection, health, and closeout | `plugin/CODEX.md`<br>`plugin/skills/project-state/SKILL.md`<br>`plugin/skills/project-milestone-manager/SKILL.md`<br>`plugin/skills/project-phase-gate/SKILL.md`<br>`plugin/skills/project-archive/SKILL.md`<br>`plugin/skills/project-status-reporter/SKILL.md`<br>`plugin/skills/project-orchestrator/SKILL.md`<br>`plugin/skills/project-doc-suite/SKILL.md`<br>`plugin/skills/project-tech-reports/SKILL.md`<br>`plugin/skills/project-onepager/SKILL.md`<br>`plugin/skills/project-funder-reporting/SKILL.md`<br>`plugin/skills/project-notifier/SKILL.md`<br>`scripts/validate_codex_adaptation.py` | Reuse deterministic canonical event identities, suppress exact repeat fan-out, mechanically project counters/last activity, reconcile governed phase/lifecycle/timezone, and base health/closeout on material conditions. | Paths, schemas, event names, legacy aliases, report formats, governed overrides, and historical duplicates remain; no new event field or alternate state format is added. | Deterministic-ID, duplicate-suppression, projection, health, closeout, legacy-vocabulary, generic facility dry-run, and CanRentPro read-only acceptance checks. | Prefer any stronger internal transactional implementation while preserving identities, dry-run defaults, and legacy readability. |
| PS-CX-019 | Git serialization, external references, and progressive reads | `plugin/CODEX.md`<br>`plugin/skills/project-git/SKILL.md`<br>`plugin/skills/project-state/SKILL.md`<br>`plugin/skills/project-harvester/SKILL.md`<br>`plugin/skills/project-document-curator/SKILL.md`<br>`plugin/skills/project-feedback/SKILL.md`<br>`plugin/skills/project-jira-publisher/SKILL.md`<br>`plugin/skills/project-goal-tracker/SKILL.md`<br>`plugin/skills/project-milestone-manager/SKILL.md`<br>`plugin/skills/project-status-reporter/SKILL.md`<br>`plugin/skills/project-orchestrator/SKILL.md`<br>`plugin/skills/project-doc-suite/SKILL.md`<br>`plugin/skills/project-tech-reports/SKILL.md`<br>`plugin/skills/project-onepager/SKILL.md` | Use ordinary protected-branch merges for cross-clone serialization, allow explicit companion-code checkpoints, retain stable external references instead of full copies, and bound routine reads before detail. | Deliberate state-only commits, configured external adapters, copied legacy records, full detail/deep scans, Git sharing, and merge attributes remain supported. | Static Git/ref/read-contract scans, missing-reference audit, deterministic fixtures, fresh-process summary/detail probes, and legacy compatibility comparison. | Retain unless internal storage supplies stronger concurrency or query primitives with the same explicit authorization boundary. |
| PS-CX-020 | Lean.4 package, release, and evidence | `.codex-plugin/plugin.json`<br>`README.md`<br>`CODEX-ADAPTATION.md`<br>`scripts/validate_codex_adaptation.py` | Publish the consensus scalability contract, incorporate the pre-existing local cachebuster into a stable release version, and make package plus optional facility validation repeatable. | Installation remains one public repository and `project-state@personal`; attribution, upstream provenance, MIT licensing, 43 skills, packs, capabilities, and public main remain unchanged. | Full adaptation validator, 43 quick validations, package/discovery checks, fresh-process probes, Git diff check, exact tag/remote parity, and clean personal-installation proof. | Carry this release evidence forward; never restore a duplicate distribution branch or hosted gate. |

## Validation evidence

The validation entrypoint is:

```powershell
$env:PYTHONUTF8 = '1'
py -3 scripts/validate_codex_adaptation.py
```

The initial `codex-v4.9.0-lean.1` release passed the Codex-owned validators and
independent fresh-process probes on the exact release commit before its
immutable tag was created:

- adaptation contract validator: passed with 43 skills, eight packs, two
  capabilities, four JSON files, 83 YAML files, six Python files, two
  JavaScript files, one archive, and 45 local links checked;
- `quick_validate.py`: 43/43 skills passed with UTF-8 enabled;
- Codex plugin installation/activation: passed against the exact nested-path
  manifest. The plugin-creator structural validator also passed against a
  temporary canonical-root projection; its current hard-coded path check does
  not accept nested skill roots;
- `git diff --check`: passed;
- deterministic fresh-process prompt input contained all 43 unique
  `project-state:*` skill names. An earlier model-authored list omitted
  `project-onboarder`; the loader inventory proved that was a response omission,
  not a discovery failure;
- a fresh read-only resource probe loaded `project-scaffolder`, loaded
  `plugin/CODEX.md`, resolved `plugin/templates/manifest-v2.yaml`, confirmed
  schema version 2 and upstream commit
  `c0b55ba52dfdca9312a1f6150039ed14d569e2db`, and attempted no mutation;
- a fresh read-only routing probe selected exactly one established owner for
  each of routine status, funder/customer claims, audience briefs, full
  documentation bundles, technical intelligence, and public websites; and
- the same probe kept SR&ED, tender, grant, publishing, connector harvesting,
  and all report generators inactive when their packs, capabilities, surfaces,
  connectors, state directories, and due matrix entries were absent.

The `codex-v4.9.0-lean.3` Codex-only distribution additionally passed the
adaptation validator with 43 skills, eight packs, two capabilities, two JSON
files, 83 YAML files, six Python files, two JavaScript files, one archive, and
48 local links checked. Both Claude distribution manifests were absent; strict
YAML parsing, Python syntax compilation, `node --check`, active Claude-only
instruction scanning, baseline ancestry, matrix/commit coverage, and
`git diff --check` passed.

For `codex-v4.9.0-lean.4`, the 43 skill directories again passed the
skill-creator quick validator. Focused in-memory fixtures passed for
task/epic/program routing, materiality, deterministic identity, exact-repeat
suppression, projections, health, timezone, and continuous closeout. A generic,
read-only reconciliation of the CanRentPro fixture at
`548aefe10c92426ad2d805b32a34ae20f7aa4860` parsed its complete YAML/JSON state,
left HEAD and the clean worktree unchanged, and measured 46 tracked state files,
54 other tracked files, 90 activity events, 18 total commits, 14 state-touching
commits, and nine state-only commits. It surfaced rather than repaired:

- manifest/tasks timezone drift (`null` versus `America/Toronto`);
- a continuous lifecycle with no increment history and completed entities in
  later phases than the current phase;
- yellow health attributed solely to development-only advisories; and
- three repeated 40-character evidence revisions occurring six, two, and three
  times respectively.

Those findings are acceptance evidence for the generic dry-run reconciler, not
authorization to mutate the fixture. The release validator and fresh-process
installation probes are run again on the exact lean.4 release revision before
the immutable tag is pushed.

The contract validator checks the exact upstream baseline tag and ancestry,
exact skill name set, adapter links, the direct nested plugin manifest, absence
of Claude distribution manifests, strict JSON/YAML,
in-memory Python syntax, JavaScript syntax, website archive traversal safety,
relative references, protected templates/packs/capabilities path sets, package
counts, schema version 2, representative event terms, established report paths,
private identifiers, unsupported Claude-only operations, matrix coverage, and
commit-message rationale.

No validation step scaffolds or mutates a Project State project.

## Installation and release discipline

The public `main` branch is installed by cloning it to `$HOME/plugins/project-state`
(or `%USERPROFILE%\plugins\project-state` on Windows) and running
`codex plugin add project-state@personal`. The repository itself is not
duplicated into a second payload: its root Codex manifest points directly to
`plugin/skills/`.

Release invariants are:

1. keep `main` as the single public Codex branch and
   `upstream-v4.9.0` as the immutable exact upstream baseline;
2. keep the upstream baseline as an ancestor of every Codex release;
3. require every changed file to map to a justification ID and every adaptation
   commit to record `Why`, `Compatibility`, and `Validation`;
4. run the read-only contract validator and applicable Codex package probes on
   the exact revision before tagging it;
5. never scaffold or mutate a Project State project as part of package
   validation; and
6. retain the original attribution, upstream links, and MIT license.

The lean.4 release intentionally replaces the pre-existing local timestamp
cachebuster with the stable public manifest version `4.9.0+codex.lean.4` and
installs that exact version. Any later machine-local cachebuster must be
reconciled deliberately before the next release and must not leave the canonical
checkout dirty.

## Later internal-version migration

When Atomic47 grants internal access:

1. preserve the validated public `main` history and immutable release tags;
2. clone the internal source separately and inventory its schemas, private
   services, dashboards, hooks, packs, and workflow contracts before editing;
3. classify every justification row as already solved internally, still required
   for Codex, incompatible with the internal contract, or superseded by an
   internal capability;
4. port only still-required changes onto a new internal Codex branch without
   merging unrelated monorepo history;
5. treat the internal deliverable contract as authoritative;
6. repeat static and package validation, then perform project-level acceptance
   only in the separate real-project task.
