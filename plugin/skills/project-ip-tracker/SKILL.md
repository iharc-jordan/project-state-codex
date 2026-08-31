---
name: project-ip-tracker
description: Track IP arising from a project — disclosures to a configured recipient, abstracts on a configured registry, foreground vs. background distinction, annual reporting inputs. Generic in v2.0 — disclosure recipient, registry format, and definitions come from a profile loaded by the active pack. PIC pack profile routes to PIC Director of Data and IP, uses PIC IP Registry abstract format, feeds Annual Questionnaire. Other packs route to general counsel, internal IP committee, customer IP officer. Optional — projects without IP-bearing work don't load any profile and the skill is inert. Use whenever the user says 'log an IP disclosure', 'new IP', 'patent idea', 'trade secret', 'disclose to [recipient]', 'IP rationale update', 'foreground IP', 'background IP', 'IP commercialization', 'license granted', 'license received', 'annual IP update'.
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project IP Tracker (v2.0 — generic recipient)

Tracks intellectual property arising from project work. Captures disclosures, maintains a foreground/background distinction, feeds annual or periodic IP reports.

The mechanism is generic. The disclosure recipient, registry format, and IP definitions come from the profile loaded by the active pack:

- **PIC pack** profile (`packs/pic-pcais/profiles/ip-tracker.yaml`) — disclosure recipient = PIC Director of Data and IP, IP Registry abstract format, Annual Questionnaire IP section template, foreground/background per PIC definitions, commercialization reporting cadence. Reproduces v1.x behavior.
- **Internal-IP pack** profile — disclosure to General Counsel + IP Committee, internal disclosure form, quarterly IP review.
- **Customer-IP pack** profile (for client work) — joint-development IP routing, customer IP officer notification, customer-vs-vendor IP allocation per contract.

## What it owns

- Disclosure capture (one YAML per disclosure in `ip/disclosures/`)
- Foreground/background classification per the active profile's definitions
- Routing notifications to the configured recipient via `project-notifier` (Gmail draft)
- Maintaining the IP rationale baseline document
- Annual/periodic IP report assembly from the profile's template
- Coordination with `project-external-comms` for patent-filing-delay holds

## What it does not own

- Filing patents — captures disclosures and routes them; the human IP authority files
- Authoring the IP rationale narrative — captures changes; humans write the rationale
- Defining what counts as foreground vs. background — that's in the profile

## Optional module

If no profile is loaded (no pack with an `ip-tracker.yaml` is active), the skill becomes inert. Projects without IP-bearing work simply don't load any IP profile.

## Migration from v1.x

The skill name is unchanged. The PIC-specific routing (Director of Data and IP) moves from hard-coded behavior into `packs/pic-pcais/profiles/ip-tracker.yaml`. Existing disclosures and IP rationale documents are unchanged.

Projects that swap PIC for a different funder change the loaded pack; projects that add a customer alongside PIC load both packs and IP gets routed per which work it arose from (foreground for the customer, foreground for PIC, background, etc., per contract).
