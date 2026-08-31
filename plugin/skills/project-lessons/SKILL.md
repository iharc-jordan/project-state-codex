---
name: project-lessons
description: "Capture Lessons Learned continuously from project kickoff through close, then summarize them at closeout. Use whenever the user says 'capture a lesson', 'lesson learned', 'what we learned about', 'retro note', 'that was tricky, let's remember', 'pitfall we hit', 'something that worked well', 'tip for future projects', 'lessons so far', 'summarize lessons', 'retrospective', 'what would we do differently', 'lessons for the final report', or any request to record or review project retrospective content. Per PIC PM Guide best practice: 'Begin to collect Lessons Learned at the start of the project to make it easier to reflect and remember how the project went.' Lessons show up in SC meetings under Open Discussion and in final reports at closeout."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Lessons

## Purpose

PIC PM Guide best practice: begin collecting Lessons Learned at the start. Waiting until closeout means most of them are forgotten.

This skill is a low-friction register for lessons — anything from "that went better than expected and here's why" to "this nearly bit us — never again." It surfaces them at the right moments (SC meetings, quarterly retros, closeout).

## Trigger phrases

- "capture a lesson" / "lesson learned"
- "retro note" / "retrospective"
- "remember this for next time"
- "something that worked well / didn't work"
- "pitfall" / "gotcha"
- "tip for future projects"
- "lessons so far"
- "summarize lessons"
- "lessons for the final report"
- "what would we do differently"

## Operations

### `capture(fields)`

Low-friction capture. Minimum required: `title` + `body`. Everything else is optional.

Input:
- `date` (defaults to today)
- `title` (one line)
- `body` (prose — the observation + the "why it matters")
- `tags` (optional — `technical`, `process`, `communication`, `PIC`, `consortium`, `vendor`, `pilot`, `ai`, etc.)
- `related_milestone` (optional)
- `related_decision` (optional)
- `related_risk` (optional)
- `severity` (`positive` | `neutral` | `negative` | `near-miss`)
- `recommended_action` (optional — "for future projects: do X")

Flow:
1. Write `lessons-learned/YYYY-MM-DD-<slug>.md` with YAML frontmatter + prose body.
2. Log `lesson.captured` via `project-state`.

Format:

```markdown
---
id: 2026-05-14-sow-schedule-c
date: 2026-05-14
title: "Schedule C SOP review saved us a quarter of confusion"
tags: [process, funder]
severity: positive
related_milestone: null
related_decision: 2026-05-05-sop-adoption
recommended_action: "For future projects: adopt the funder's SOP template unmodified at first review meeting; customize later if needed."
created: 2026-05-14T10:00:00Z
created_by: project-lead@example.org
---

At the first review meeting we spent 30 minutes going through the
funder-provided SOP template. We were tempted to skip it — it looked
boilerplate. But it turned out to address exactly the questions that
caused friction in a previous consortium engagement. Adopting unmodified
and customizing later worked.

The specific win: the role language in the SOP preempted a drift
in our first month where we started treating the funder PM as a voting member.
```

### `list(filters)`

Retrieve lessons filtered by tag, severity, date range, or related entity.

### `summarize(period="all"|"quarter"|"phase")`

Group lessons by theme. Return a structured summary suitable for:
- SC meeting §Open Discussion / Lessons Learned
- Quarterly retro
- Final report appendix

Clustering is keyword + tag based.

### `contribute_to_final_report()`

At closeout, produce a section for the final report. Include:
- What went well (positive lessons)
- What went differently than planned (neutral + negative)
- Near-misses (we almost tripped on X — here's what saved us)
- Recommendations for future projects with this funder or program
- Recommendations for the Consortium in future engagements

Save as `reports/lessons-learned-final.md`.

## Discipline

- **Low friction capture.** Never reject a lesson for being too short. "Calibration took longer than expected. Plan 2x next time." is valuable.
- **No blame.** Lessons describe systems, not individuals. If a lesson reads as a finger-point, reframe.
- **Cross-reference generously.** Linking a lesson to a decision, milestone, or risk lets future readers understand context.
- **Review at SC meetings.** Quarterly, surface 2–3 lessons under the §Open Discussion / Lessons Learned agenda item (PIC PM Guide Appendix A).
- **Closeout summary is mandatory.** Even if lessons were sparse, produce a closeout summary — it is one of the most useful artifacts for PIC and for the next consortium.

## Integration

- **project-state** — writes `lessons-learned/*.md`.
- **project-review-meeting** — Section 10 "Open Discussion / Lessons Learned" pulls recent captures.
- **project-status-reporter** — weekly and SC packs may surface 1–2 recent lessons.
- **project-archive** — invokes `contribute_to_final_report()` at project close.

## Reference files

- `references/lesson-prompts.md` — prompts for surfacing lessons at end of milestone / quarter / phase
- `references/closeout-summary-structure.md` — structure for the closeout Lessons Learned summary
