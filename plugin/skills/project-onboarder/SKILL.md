---
name: project-onboarder
description: "Produce a personalized onboarding brief for a new teammate joining the project, grounded in project-state/. Use whenever the user says 'onboard [name]', 'new teammate joining', 'brief for [name]', 'get [name] up to speed', 'someone new from [org]', 'onboarding doc for [person]', 'welcome pack', 'what does [role] need to know', 'bring [name] into the project', or any request to introduce someone to the project. Produces a one-pager with their role, what they own, who their key contacts are, the MPA/PIC basics they need, and a 'first week' action list. Tailors content by role (Project Lead / Finance Rep / Communications / Signing Authority / Technical Contributor / PIC liaison)."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Onboarder

## Purpose

When a new teammate joins — either as a Consortium Member addition, a newly-designated SC role-holder, or a technical contributor — they need to become useful quickly. This skill pulls everything relevant from `project-state/` and produces a tailored onboarding brief.

The brief is short (target: 2 pages). It trades comprehensiveness for getting the person unstuck in week one.

## Trigger phrases

- "onboard [name]"
- "new teammate joining"
- "brief for [name]"
- "get [name] up to speed"
- "welcome pack" / "welcome brief"
- "onboarding doc for [person]"
- "what does [role] need to know"
- "bring [name] into the project"

## Inputs

1. **Person** — name, org, email (and ideally the `people/` entry if created).
2. **Role** — Project Lead / Finance Rep / Comms / Signing Authority / Technical Contributor / Observer / PIC liaison / Other.
3. **Organization** — a Consortium Member, PIC, or subcontractor.
4. **Access level** — full / SC-only / task-scoped.

If the `people/` entry doesn't exist, offer to create it first via `project-state`.

## Brief structure

```markdown
# Welcome to Project <[Short Name] / [Long Name]>

Hi <name>,

## The one-minute summary
<manifest.project.one_liner>
<total budget + PIC co-invest>
<project timeline>

## Your role
You are joining as the <role> representing <organization>.

<role-specific "what this means">

## What you own
<if milestone owner>  The following milestones are assigned to your organization:
  - M02 [Org] Data Infrastructure (…)
  - M05 [Org] AI Model (…)
<if SC designate>   You will vote at Steering Committee meetings on behalf of <org>.
<if Finance Rep>    You own quarterly claim submissions from <org> by the 20th of Apr/Jul/Oct/Jan.
<if Comms Rep>      You coordinate announcements + publications for <org>, in partnership with PIC.
<if Signing Auth>   You can bind <org> to Change Orders + MPA amendments.

## Key people to know
<People card for Project Lead, your counterpart at the other Consortium Member, PIC Project Manager, and anyone in your direct workflow>

## Where the source of truth lives
Everything authoritative is under `project-state/` in the shared drive folder. Read:
- `BLUEPRINT.md` for the overall facility
- `project-state/manifest.yaml` for project identity
- `project-state/phases/03-planning/manifest.yaml` for where we are in the lifecycle
- `project-state/SKILLS.md` for what automation is available

## The cadence
- Weekly report every Monday (via Slack)
- Quarterly Steering Committee meetings (chair: Project Lead)
- Quarterly claims due 20th of Apr/Jul/Oct/Jan (to PIC)
- Monthly technical brief to consortium
- Annual Questionnaire

## Your first week
<role-specific bullets; examples below>
- Read the MPA (once signed) or the approved proposal (`<doc-proposal-full>`)
- Set up your access to Slack channel(s): <channels>
- Review milestones you own: <list>
- Confirm your sc_designations in `people/<your-slug>.yaml`
- Check into next SC meeting: <date if known>

## Useful reference
- PIC PM Guide (May 2025): `<path>` — section that's most relevant to your role
- The schema reference: `project-state/SCHEMA.md`
- Install the skills per `project-state/skills/INSTALL.md` so "what's going on?" actually tells you

Any questions, ping <Project Lead name> in Slack or email.

Welcome aboard.
— David (keystone: david@atomic47.co)
```

## Role-specific playbook excerpts

- **Project Lead**: responsible for SC chairing, minutes, change order routing, PIC liaison, monthly/weekly reports coordination. Read the full PIC PM Guide.
- **Finance Representative**: own quarterly claims; read PIC PM Guide §Reporting. Your cadence is T-21/T-14/T-10/T-5/T-1 around each 20th. Understand eligibility: "PIC upon review of submitted costs."
- **Communications Representative**: announcements cannot pre-empt PIC's press; publications go through 30/14-day SC review. Your first move is introducing yourself to PIC's communications team.
- **Signing Authority**: you'll be asked to countersign Change Orders and MPA amendments. You don't need to be in the weeds day-to-day but you need to be reachable within 48 hours when an approval comes around.
- **Technical Contributor**: you likely own tasks under one or more milestones. Read the proposal's Milestone description and Schedule A workbook for your milestone(s). Update technical_progress monthly; ping Project Lead before quarter-close.
- **PIC liaison (incoming PIC PM)**: skip this — send them the PIC-facing summary instead.

## Operations

### `onboard(person_slug, role, org)`

1. Read `people/<slug>.yaml` (or create it via `project-state` if missing).
2. Gather role-specific content.
3. Render the brief as `communications/onboarding/<person_slug>.md`.
4. Hand off to `project-notifier` to Gmail-draft the welcome email to the person.
5. Log `onboarding.drafted`.

### `update_onboarding(person_slug)`

Refresh the brief for someone who's been around but wants an updated snapshot.

## Discipline

- **Keep it short.** 2 pages maximum. Better: 1.
- **Role-specific, not comprehensive.** A Finance Rep does not need a 20-page technical overview. A Technical Contributor does not need quarterly claim procedure.
- **Point at source of truth.** Don't re-explain what lives in the manifest; link to it.
- **Confirm access before promising it.** Slack channels and doc folders should already be shared by the time the brief goes out.

## Integration

- **project-state** — reads people, manifest, milestones, phase.
- **project-notifier** — Gmail draft to the new teammate.
- **project-milestone-manager** — pulls the milestones owned by the person's org.
- **project-review-meeting** — brief references the next SC meeting date/time.
