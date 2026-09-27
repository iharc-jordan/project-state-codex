---
name: project-educator
description: "Explain project management through this project's own state — 'explain what a risk register is here', 'what's working and what's broken', 'teach me', 'why does this matter'. Plain language, for newcomers."
plugin: "project-state-suite"
tier: P2
depends_on:
  skills:
    - project-state
surfaces: []
slash_command:
  trigger: "/project-educator"
  subcommands:
    - name: "briefing"
      description: "The literacy briefing: how this project is functional and dysfunctional, with one move per finding"
    - name: "explain <topic|entity>"
      description: "Ground an entity, term, or practice in this project's own state"
    - name: "pathway"
      description: "The next single practice to adopt, and why"
    - name: "profile [show|set <field> <value>]"
      description: "Show or update the education profile (audience, level, annotations, vocabulary)"
    - name: "--help"
      description: "Show usage summary"
  examples:
    - "/project-educator briefing"
    - "/project-educator explain risk-register"
    - "/project-educator pathway"
    - "/project-educator profile set level practicing"
map:
  tier: P2
  stage: keep
  reads: [manifest, milestones, risks, decisions, objectives, changes, log, education]
  writes: [education]
  produces: [teaching-briefing]
---

# Project Educator

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Inline project education — the teaching concierge for audiences new to project management. Teaches through this project's own state: names what is working and what is quietly broken in plain language, explains any entity or practice in the audience's own vocabulary, and recommends the next single practice to adopt. Use when the user says 'how healthy is this project', 'explain this project to me', 'what is a risk register and why do we care', 'why does this matter', 'teach me as we go', 'what should we learn to do next', 'give me the literacy briefing', 'turn education mode on/off', 'stop explaining that', or '/project-educator'. Reads manifest, milestones, risks, decisions, objectives, changes, logs, reporting-matrix and education/profile.yaml; writes education/profile.yaml and education/log.ndjson. Do not use to generate status reports (project-status-reporter) or to capture retrospectives (project-lessons) — this skill teaches the practice, it does not do the reporting.

## Purpose

Many organizations this substrate serves — band-management organizations, community-based organizations, first-time grantees — carry real governance and accountability obligations without formal project-management literacy, and should never need a course to use their own project. Without this skill the suite works but doesn't teach, so the organization stays dependent on whoever set it up. The educator closes that gap in line: it uses the project's own state as the entire curriculum, pairs every dysfunction it names with what is working and one practical move, and fades as fluency grows. Design: `docs/INLINE-EDUCATION-SPEC.md`.

## Trigger phrases

- "how healthy is this project" / "how is this project doing, really"
- "give me the literacy briefing" / "how is this project functional and dysfunctional"
- "explain this project to me" / "explain <milestones|risks|decisions|the reporting matrix> to me"
- "what is a <risk register / phase gate / change order> and why do we care"
- "why does this matter"
- "what should we learn to do next"
- "teach me as we go" / "turn education mode on" / "turn education mode off"
- "stop explaining that" (mutes a topic)
- `/project-educator briefing`

## Inputs

- **Current working directory** — locate `project-state/` by walking up.
- Via `project-state`: `manifest.yaml`, `state.json`, `milestones/*.yaml`, `risks/*.yaml`, `decisions/*.yaml`, `objectives/*.yaml` (if present), `changes/change-log/*.yaml`, `reporting-matrix.yaml`, `logs/activity.ndjson` (recent tail), and `education/profile.yaml` + `education/log.ndjson` (if present).
- **User arguments** — subcommand and topic/entity/field arguments as in the frontmatter.
- **Reference file** — `references/dysfunction-patterns.md` (this skill's pattern library: signal → plain name → why it matters → the move → what it teaches). Read it before every `briefing` and `pathway` run.
- No pack profile required.

## Outputs

- `project-state/education/profile.yaml` — created on first use from `templates/education-profile.yaml`, updated by `profile set` and by "stop explaining that" (via `project-state`).
- `project-state/education/log.ndjson` — one appended entry per teaching moment `{ts, concept, surface, entity, level_at_time}` (via `project-state`, which also logs the write to the activity log).
- Conversational teaching output per Output format. No surfaces touched; nothing outward-facing. The educator is inward-facing only — outward audience framing belongs to `project-onepager`.

## Behavior

1. Locate `project-state/` by walking up from cwd. If not found, go to Error handling.
2. Via `project-state`, read `education/profile.yaml`. If absent, seed it from `templates/education-profile.yaml`, asking the user one question — "who is this project's team, in your own words?" — to set `audience` and `framing.governance_anchor`. Do not interrogate further; every other field keeps its default.
3. Dispatch on subcommand (default, when the user's request is a question about a term or entity, is `explain`; when it is about overall health, `briefing`).

### `briefing`

4. Via `project-state`, read the entities listed in Inputs. Evaluate every pattern in `references/dysfunction-patterns.md` — functional patterns first, then dysfunctions — collecting concrete evidence (entity ids, dates, counts) for each hit.
5. Write a 2–3 line **What happened lately** recap from the recent activity log, in plain words with humanized dates — this answers *what was done* before anything is judged.
6. Select at most 4 functional and at most 4 dysfunction findings, ranked by impact on the organization's accountability. Every dysfunction carries exactly one move (from the pattern's `the move`), rewritten to name this project's actual entity and sized for one sitting.
7. Choose the single **next practice** — the practice that addresses the highest-impact dysfunction, phrased per the profile's `framing.governance_anchor` (the practice extends governance the org already does).
8. Render per Output format, translating terms through `vocabulary` and honoring `muted_topics`. At `newcomer` level apply the plain-language contract (`docs/INLINE-EDUCATION-SPEC.md` §3.1) to every line: the five questions as separate short lines (what was done → why it matters → what's next → why that → how), spoken register, humanized numbers ("almost four months", not "118 days"), names before codes ("the desktop app milestone (M12)", never the bare code), one why per finding. The pattern library's text is source material to down-shift, never to quote. Never emit a score, a percentage, or maturity language.
9. Via `project-state`, append one education log entry per concept surfaced.

### `explain <topic|entity>`

4. Resolve the argument: an entity id (e.g. `M04`, `R-02`) → that entity; a term (e.g. `risk-register`) → the concept plus this project's matching entities.
5. Answer in ≤2 short paragraphs: what it is in plain language (through `vocabulary`), then why it matters *here*, citing this project's own data (counts, dates, the actual item). If the project has no matching entities, say so plainly and use one generic example, marked as such.
6. End with one optional practical hook (a two-minute walk-through offer or a slash command) — never a lecture continuation. If the topic is in `muted_topics`, give only the direct factual answer with no teaching frame.
7. Append an education log entry.

### `pathway`

4. Run the pattern evaluation as in `briefing` steps 4–6 but return only the next practice: what to adopt, why (grounded in the current highest-impact dysfunction), what doing it looks like this week, and which command does it.
5. Append an education log entry.

### `profile [show|set <field> <value>]`

4. `show` → render the profile in plain language. `set` → validate (`level` ∈ newcomer|practicing|fluent; `annotations` ∈ on|off) and write via `project-state`. "Stop explaining that" → append the concept to `muted_topics`.
5. If the education log shows a concept cluster repeatedly acted on at the current level, the educator may *propose* a level promotion here — never promote automatically.

### Annotation policy (for host skills — not a subcommand)

When `annotations: on` and `level` is `newcomer` or `practicing`, skills producing inward-facing prose (`project-status-reporter`, `project-orchestrator`, `project-review-meeting`, milestone confirmations) apply this policy to their own drafts: at most one why-line per section and three per artifact, each attached to a specific item, skipping concepts already `taught` in the education log, never in outward-facing artifacts. Why-line form: `↳ Why this matters: <one sentence>. (<one-line move>)`.

## Output format

`briefing` at `newcomer` level returns (≤1 page, always paired, no scores, §3.1 contract on every line):

    # Your project check-in — YYYY-MM-DD

    ## What happened lately
    <2–3 plain lines: what was done recently, from the record, humanized dates>

    ## What's going well
    - **<plain name>** — <one short sentence: what the record shows>. <one short sentence: the good it does>.

    ## What needs a look
    - **<plain name>** — <what the record shows, in everyday words>.
      *Why it matters:* <one short sentence>.
      *What to do:* <one small step>.
      *How:* <the exact thing to say, or the command to run>.

    ## What's next
    <one practice: what, why now, and the first small step this week>

At `practicing` and above, the compact practitioner form is allowed instead: headers "Working / Drifting / Next practice", evidence-first bullets, move inline. `explain` returns two short paragraphs plus one optional hook line (five-questions shape at newcomer). `pathway` returns the What's-next block alone. `profile show` returns a short plain-language listing.

## Error handling

**Missing state**: if no `project-state/manifest.yaml` is found walking up from cwd, stop and return:
> No `project-state/` found. Run `/project-scaffolder` to initialize one — and I can teach as we go from there.

**Missing template**: if `templates/education-profile.yaml` is unavailable when seeding, create `education/profile.yaml` with the defaults shown in `docs/INLINE-EDUCATION-SPEC.md` §6.1 and continue.

**Sparse state** (project too young for patterns to fire): return the functional list that exists, say plainly that it is early, and offer the two practices that create teachable state first (milestones with dates; decisions with owners). Never pad with hypothetical dysfunctions.

**Invalid input**: unknown subcommand or unresolvable entity/topic → say what wasn't found, list the four subcommands, and offer the nearest match. Execution stops.

## Integration

- **project-state** — all reads and writes route through it, including both education files.
- **project-orchestrator** — includes at most one educator nudge in the daily read when the briefing is stale (>30 days) or a dysfunction pattern first fires.
- **project-intake / project-onboarding** — may seed `education/profile.yaml` at init when the audience is known.
- **project-status-reporter / project-review-meeting** — hosts for inline why-lines under the annotation policy.
- **project-lessons** — a dysfunction the team fixed is a lesson candidate; suggest capturing it, don't capture it unasked.

## Reference files

- `references/dysfunction-patterns.md` — the pattern library: functional and dysfunction patterns, each with signal, plain name, why it matters, the move, and what it teaches.
