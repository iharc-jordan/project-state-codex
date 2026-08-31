---
id: YYYY-MM-DD-<slug>            # must match the filename minus .md
date: YYYY-MM-DD
title: "One line, in the past tense, naming what was learned"
tags: [technical, process]       # free-form; used for grouping in the Lessons view
severity: neutral                # positive | negative | neutral
related_milestone: null          # milestone id (M<NN>-slug), or null
related_decision: null           # decision id (YYYY-MM-DD-slug), or null
related_risk: null               # risk id (R-<NN>-slug), or null
recommended_action: "What someone should do differently next time. One sentence, imperative."
created: YYYY-MM-DDTHH:MM:SSZ
created_by: you@example.com
---

## What happened

The situation, briefly, with enough specifics that someone who was not there can recognise it. Name
files, ids and dates rather than describing them.

## Why it happened

The cause, separated from the symptom. If the cause is a guess, say it is a guess — a lesson built on
a plausible story is worse than one that admits the cause is unknown, because the next person will
act on it.

## What to do instead

Concrete and checkable. If it is already enforced somewhere — a validator, a guard, a schema rule —
name that thing, because a lesson with a mechanism behind it survives and a lesson that relies on
memory does not.

<!--
WHY THIS TEMPLATE EXISTS

Project State defines `lessons-learned/YYYY-MM-DD-<slug>.md`, and
skills/project-lessons has always written exactly that path. What was missing was a shape to copy and
a directory to copy it into. This repo's own facility has the directory and five lessons in it;
CRMA47, a newer facility, has no such directory, and the scaffolder's output listing never mentions
one.

The cost was not theoretical. Two hard-won lessons from a CRMA47 session on 2026-08-21 (a draft-07
host-validator trap, and "skill files are prompt material, keep secrets out of them") were written to
`wiki/` instead, because that directory existed and this one did not. They are real lessons sitting in
the wrong place, findable only by someone who already knows to look.

Also found while writing this: the five lessons in this repo were never counted -
state.json:counters.lessons read 0. Written but not registered, which is the same drift the feedback
register showed on 2026-08-21.

That is one pattern with several instances - a shipped, documented capability with nothing that makes
it reachable. See FB-003 (five phase presets, no writer) and FB-002 (a REQUIRED manifest key nothing
collected). Recorded in decision 2026-08-21-twelve-rulings-facility-contract.

Delete this comment when you copy the file.
-->
