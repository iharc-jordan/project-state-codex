---
name: project-change-register
description: "Register, classify, and route project changes per PIC PM Guide — distinguish material (Change Order, Schedule A amendment) from non-material (Change Log entry). Use whenever the user says 'log a change', 'we need to change X', 'swap vendor', 'add a subcontractor', 'shift funds', 'timeline slip', 'change order', 'CO-01', 'material change', 'non-material change', 'change the IP rationale', 'change of control', 'bring on ACME as subcontractor', 'update the change log', 'what's the difference between a CO and a change log', or any request about changes to the project scope, schedule, budget, vendors, subcontractors, or IP rationale. Drafts Change Orders but never submits — always stops at a draft for PIC + Steering Committee approval."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Change Register

## Purpose

PIC's PM Guide defines a crisp two-tier change system. Getting the classification right matters because it determines the approval path and whether an MPA amendment (Schedule A) is required. This skill is the register and the router.

**Material changes → Change Order → PIC acceptance → SC approval → amends MPA Schedule A.**
**Non-material changes → Change Log entry → SC approval → lives in the Workbook.**

*PIC is the arbiter* of whether any specific change is material. When in doubt, query the PIC Project Manager before filing.

## Trigger phrases

- "log a change" / "record a change"
- "material change" / "non-material change"
- "change order" / "CO" / "CO-01"
- "swap vendor" / "add vendor" / "change vendor"
- "add subcontractor" / "engage [subcontractor name]"
- "shift funds" / "move budget between [A] and [B]"
- "timeline slip" / "delay milestone by N months"
- "change IP rationale"
- "change of control"
- "delay funds to next year"
- "what counts as material?"

## Material vs. non-material — the PIC rules

### Material (requires Change Order)

Per PIC PM Guide §Change Management:
- Funds shifting between categories, milestones, or Consortium Members
- Naming of subcontractors (any new subcontractor except those already on Schedule A)
- Milestone additions, subtractions, or major timeline deviations (≥3 months) from original plan
- Engagement of a related entity
- Changes in IP rationale
- Change of control of a Consortium Member

Change Orders default to **forward-looking**. Retroactive changes possible but only after querying the PIC PM.

Delay of funds to subsequent years: Change Orders will **not** be accepted; such shifts may be considered following the Annual Questionnaire at PIC's discretion.

Change of control also triggers a 30-day notification obligation to PIC.

### Non-material (Change Log entry)

- Vendor changes or additions (vendor = standard service provider with no access to IP/confidential info)
- Milestone timeline changes < 3 months that do not affect project end date

"Non-material" in this PIC classification is still a governed shared-project
fact and may justify the established Change Log. It is not permission to log
ordinary task-local code changes, commits, formatting, or test reruns. Those
remain in Git/the active task unless the operator explicitly requests a Project
State record and supplies a reason.

### Subcontractor vs. vendor — the key distinction

- **Subcontractor:** any access to project IP or confidential information. Lists on "Subcontractor" tab. Changes require Change Order.
- **Vendor:** standard service provider with no IP/confidential access. Lists on "Other Direct" or "Materials & Supplies". Changes go on Change Log.

Universities and Food Centres are **always** subcontractors unless already a Consortium member.

## Operations

### `classify(description)`

Given a description of a proposed change, return the most likely classification (`material` | `non-material` | `ambiguous`) with reasoning. For ambiguous, include the specific question to bring to the PIC Project Manager.

### `log_non_material(fields)`

Input:
- `date` (ISO)
- `description`
- `reason`
- `impact` (budget/timeline/IP — usually "zero")
- `responsible_party`

Flow:
1. Apply the adapter materiality gate, then classify under the PIC rules. Refuse
   task-local work with no reason and refuse this operation if PIC
   classification is `material`.
2. Write `changes/change-log/YYYY-MM-DD-<slug>.yaml` per schema.
3. Log `change.logged` via `project-state`; bump `counters.change_log_entries`.
4. Mark for SC approval — belongs in the next SC pack Section 4.

### `draft_change_order(fields)`

Input:
- `title`
- `material_reason` (which PIC criterion applies)
- `affected_milestones`
- `budget_impact` (if any)
- `budget_shift` (from category → to category, if reallocating)
- `ip_rationale_change` (bool)
- `decision_ref` (link to the originating decision)

Flow:
1. Classify; refuse if not `material`.
2. Assign CO number (next in sequence; `CO-01`, `CO-02`, …).
3. Write `changes/change-orders/CO-NN-<slug>.yaml` with `status: drafted`.
4. Log `change-order.drafted` via `project-state`; bump `counters.change_orders`.
5. Via `project-notifier`:
   - Gmail draft to PIC Project Manager — PIC arbiters first per Guide.
   - Note in next SC pack pending resolution.

### `submit_change_order(co_id)`

After user confirms the CO is ready and has cleared PIC PM feedback, mark `status: submitted`, fill `pic_submitted: <date>`, log `change-order.submitted`.

### `record_pic_approval(co_id, date)` / `record_sc_approval(co_id, date)`

Update CO record with approval dates. When both are present, mark `status: approved` and `mpa_amendment_incorporated: <date>`. Log `change-order.approved`.

If PIC rejects, mark `status: rejected` with reason; the CO is closed and a new one may be drafted.

### `list_open()`

Return all COs with `status in {drafted, submitted, under_review}`. Used by SC pack and weekly report.

## Discipline

- **Project State materiality comes first.** A code change is not a Change Log
  entry merely because this skill can classify changes. Shared governed scope,
  schedule, budget, vendor, IP, or compliance facts qualify; explicit operator
  overrides include their reason in the existing summary.
- **PIC is the arbiter.** This skill's classification is advisory. When non-trivial, draft a Change Order and get PIC PM to confirm rather than guess.
- **Change Orders are forward-looking by default.** Retroactive CO attempts flag a warning; user must explicitly acknowledge.
- **Change of control notification clock.** If a CO involves change of control of a Consortium Member, also schedule a 30-day PIC notification reminder via `project-orchestrator`.
- **No CO without a decision.** Material changes should trace to a `decisions/` entry. If none exists, the skill prompts to create one first.
- **Cost eligibility separate from CO approval.** Per PIC PM Guide: "A change order can be approved and accepted but costs will still be evaluated for eligibility for reimbursement." The skill notes this on each CO with `budget_impact`.

## Integration

- **project-state** — all writes go through it.
- **project-notifier** — PIC PM Gmail draft for CO submission; SC reminders.
- **project-status-reporter** — pulls change-log + open COs for weekly and SC pack.
- **project-review-meeting** — incorporates pending COs into Section 4 of the agenda.
- **project-milestone-manager** — CO affecting milestones cross-references those milestones.
- **project-ip-tracker** — IP-rationale-change COs coordinate with the IP abstract.
- **project-phase-gate** — CO approvals that amend Schedule A may unblock gate criteria.

## Reference files

- `references/material-vs-non-material.md` — the full PIC criteria with examples
- `references/co-template.md` — the skeleton of a Change Order YAML
- `references/change-of-control-checklist.md` — 30-day notification flow
