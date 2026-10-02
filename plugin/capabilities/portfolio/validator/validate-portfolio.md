# validate-portfolio — the portfolio capability's validator (lean V1)

Composed with the core validator by `project-state validate`; may fail only records in the
`portfolio` namespace (the bundled capability contract). Checks, in order:

1. **Enablement coherence.** `capabilities.portfolio` present and `enabled` well-formed;
   `workspace_root` and `subject` non-empty and not the literal `REQUIRED`; `workspace_root`
   resolves to a directory (warn); `version:` compared to the installed plugin — warn on drift.
2. **Directory shape.** `portfolio/{members,snapshots,index,understanding,dependencies,findings,answers,reports}`
   exist; `state/portfolio.json` parses; `portfolio/registry.yaml` parses when present.
3. **Members.** Filename equals `id:`; ids unique; enums; a member in `{active, paused, closing}`
   has `location.type != none` and a `path` or `remote`; a `retired` member carries `retired:`.
   Whether the location exists is the collector's `member-unreachable`, not a validation failure.
4. **Snapshots.** Every `portfolio/snapshots/<member>/` names a member row (fail on orphans);
   one file per date; `member_id` equals the directory; `reachable: false` carries
   `unreachable.reason`; where the host tracks content hashes, a snapshot changed after
   `captured_at` is a failure.
5. **Index.** Every `portfolio/index/*.yaml` parses; every row's `member` resolves to a member
   row; a row whose `path` no longer exists in the member → warn ("re-collect").
   `index` older than the newest snapshot → warn.
6. **Ids and counters.** `PF-D-NNN` / `PF-F-NNN` filenames match `id:`; counters in
   `state/portfolio.json` ≥ the highest id seen — fail on a counter behind the files.
7. **Dependencies.** `from.member` and `to.member` resolve; enums.
8. **Findings.** Required fields and enums; `members[]` resolve; every `evidence[]` row carries
   `member` and `path`; `became[]` entries shaped `{member, entity, at}`; a `dismissed` finding
   carries `dismissed_reason`; an `emerging-project` finding with status `acknowledged` has a
   `became` row pointing at a `proposed` member.
9. **Answers.** Every `portfolio/answers/*.md` front matter carries `question`, `read`,
   `drilled`, `basis`.
10. **Read-only discipline.** No path under `workspace_root` other than this project's own
    `project-state/` appears as a write target in `logs/activity.ndjson` entries authored by
    `portfolio-*` skills, except `documents/inbox/portfolio-proposal-*.md` drops recorded by
    `portfolio.finding.promoted`. Any other is a failure — the portfolio never writes into a member.

Report findings plainly; fix nothing silently.
