# Pattern library — functional and dysfunction patterns

Read by `project-educator` before every `briefing` and `pathway` run. Each pattern gives: the
detectable **signal** in state, the **plain name** used with the user (no jargon), **why it
matters** written for a newcomer and framed on accountability, **the move** (one action, one
sitting, with the skill that does it), and **teaches** — the underlying practice this moment is an
opening to teach. Evidence must always be concrete: real entity ids, real dates, real counts.

Conventions for this library and `project-educator`:
functional patterns are evaluated and reported first (E2); at most one move per dysfunction (E3);
patterns describe systems, never individuals (E7); no scores, no maturity language, ever.

**Register note (E11):** the entries below are written at the `practicing` register — they are
source material, not copy. At `newcomer` level the educator down-shifts every line through the
plain-language rules: the five questions as separate short lines, spoken register,
humanized numbers, names before codes, one why per finding. Never quote an entry verbatim to a
newcomer.

Age thresholds below are defaults; tighten or relax them proportionally to the project's cadence
(a weekly-cadence project goes stale faster than a quarterly one — read the reporting matrix).

---

## Functional patterns (find these first)

### F1 — The written why
- **Signal:** decisions exist and ≥80% of those from the last two quarters have an owner, a date, and a stated rationale.
- **Plain name:** "Your decisions have a written why."
- **Why it matters:** anyone new — a council member, an auditor, a funder — can reconstruct why a choice was made without asking anyone. That is institutional memory, and most organizations don't have it.
- **Teaches:** decision records as governance minutes.

### F2 — The living log
- **Signal:** activity log entries within the last 7 days across more than one entity kind.
- **Plain name:** "The project's record is alive."
- **Why it matters:** the record reflects what is actually happening, which means every report generated from it is true without anyone reconstructing the month from memory.
- **Teaches:** state as the source of truth; reporting as a byproduct.

### F3 — The honest change record
- **Signal:** milestone date changes in the last quarter have matching change-log entries.
- **Plain name:** "When the plan changed, you said so."
- **Why it matters:** plans always change; accountable projects write down that they changed and why. This is exactly what funders and members mean when they ask for transparency.
- **Teaches:** change control as honesty, not bureaucracy.

### F4 — The reviewed risk list
- **Signal:** all open risks have `last_reviewed` within the review age (default 60 days).
- **Plain name:** "You look at your worry list on purpose."
- **Why it matters:** problems get handled while they're small and cheap, instead of remembered at 2am when they're neither.
- **Teaches:** risk review cadence.

### F5 — Many hands on the record
- **Signal:** writes in the last quarter come from ≥2 distinct authors.
- **Plain name:** "This isn't a one-person project."
- **Why it matters:** the project survives any one person's vacation, illness, or departure. Shared custody of the record is shared accountability.
- **Teaches:** bus factor; delegation of record-keeping.

---

## Dysfunction patterns

### D1 — Invisible drift
- **Signal:** milestone(s) past due date with status still open and no change-log entry touching them.
- **Plain name:** "The plan and reality have quietly drifted apart."
- **Why it matters:** an overdue item with no note means nobody has decided which is true — the date or the delay. Everything downstream of it (reports, promises to funders and members) inherits the fiction.
- **The move:** for the most overdue milestone, either move the date *with a reason* or mark what's blocking it → `/project-milestone-manager`.
- **Teaches:** keeping the record honest; change notes.

### D2 — The silent risk list
- **Signal:** open risks with `last_reviewed` older than the review age (default 60 days), or zero risks recorded on a project past its first quarter.
- **Plain name:** "The worry list has stopped being looked at" / "the worries live in people's heads."
- **Why it matters:** an unread risk list is the usual way it quietly stops being true. Unwritten worries can't be handed to anyone, budgeted for, or caught early.
- **The move:** review the single oldest unreviewed risk — still real? bigger? handled? — and update it (two minutes) → `/project-state` update risk.
- **Teaches:** risk review cadence; writing worries down.

### D3 — Decisions without a why
- **Signal:** decisions missing owner, date, or rationale; or an active quarter with zero recorded decisions.
- **Plain name:** "Choices are being made, but the why isn't being kept."
- **Why it matters:** in six months someone will ask why this was done — an auditor, a new member, the council. "We don't remember" costs trust that took years to build.
- **The move:** record the most recent significant choice as a decision with owner, date, and two sentences of why → `/project-state` record decision.
- **Teaches:** decision records as minutes.

### D4 — The quiet log
- **Signal:** no activity log entries for 14+ days on a project whose phase is active.
- **Plain name:** "The project's record has gone quiet."
- **Why it matters:** work is almost certainly happening — but it's happening off the record, which means reports will be reconstructed from memory, and memory is where accountability leaks.
- **The move:** log this week's three most significant events, one line each → `/project-state` log activity.
- **Teaches:** little-and-often record keeping.

### D5 — One-person project
- **Signal:** ≥90% of writes in the last quarter from a single author on a multi-person project.
- **Plain name:** "One person is carrying the whole record."
- **Why it matters:** if that person is away for a month, the project's memory goes with them. It's also a heavy, unfair load — shared record-keeping is shared accountability, not surveillance.
- **The move:** pick one entity kind (milestones is easiest) and hand its upkeep to a second person, with a 15-minute walk-through.
- **Teaches:** bus factor; delegation.

### D6 — Promises without a calendar
- **Signal:** reporting-matrix rows whose cadence implies a report that has never been generated, or is ≥1 full cycle overdue.
- **Plain name:** "There are reporting promises no one is keeping."
- **Why it matters:** each matrix row is a commitment to a real audience — a funder, the membership, the council. Missed quietly, each one spends down the trust the project runs on.
- **The move:** generate the single most overdue report now (it's a byproduct of the record, not extra work) → `/project-status-reporter`.
- **Teaches:** the reporting matrix as a promise ledger.

### D7 — Goals with no legs
- **Signal:** objectives with zero linked milestones, or milestones linking to no objective.
- **Plain name:** "The goals and the work aren't holding hands."
- **Why it matters:** goals without work under them are wishes; work without a goal over it is motion. Either way, nobody can say whether this month moved the organization toward what it promised.
- **The move:** link the most important unlinked objective to the milestones that actually serve it → `/project-goal-tracker`.
- **Teaches:** objectives → milestones traceability.

### D8 — The stale gate
- **Signal:** current phase unchanged for far longer than its plan, with no phase-gate review recorded.
- **Plain name:** "The project hasn't stopped to ask 'are we still on the right road?'"
- **Why it matters:** phases exist so there's a scheduled moment to decide *on purpose* whether to continue, adjust, or stop. Skip it long enough and the project runs on momentum instead of decisions.
- **The move:** hold a short gate review — what did this phase promise, what happened, go/adjust → `/project-phase-gate`.
- **Teaches:** phase gates as deliberate checkpoints.
