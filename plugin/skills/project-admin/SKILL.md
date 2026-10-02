---
name: project-admin
description: "Create, pull, or list Project State projects — 'create a project', 'pull project X', 'list projects'. Uses the configured local or GitHub location."
map:
  tier: P3
  stage: keep
  requires: [memory, local-fs]
  reads: [manifest]
  calls: [project-scaffolder, project-git]
  delivers: [chat]
---

# Project Admin

Manage the projects the operator can actually access. Read `plugin/CODEX.md` once per task and use the selected Project State binding.

## List

Call `project_list` when available. For local projects not served there, use the configured workspace registry or explicit directories supplied by the operator. Return each project's identity, location, and access state. Do not claim that an unconfigured dashboard or private registry exists.

## Create

Use `project-scaffolder` at the selected local directory. A request to create a GitHub state repository also supplies authorization for that action; confirm the GitHub owner from the requested destination or existing configuration, create one private repo with `gh`, and push the initialized state. Register it in a viewer only when that viewer and registry are actually configured and the request calls for registration. Report the real repository and local path.

## Pull

Resolve the repo from an explicit GitHub reference or configured registry. Use `gh repo clone` for a new copy, or `project-git sync` for an existing copy. Verify `project-state/manifest.yaml` in the result. Preserve dirty local changes and avoid cloning over an existing directory.

GitHub membership remains governed by the repository's permissions. Do not invent a local role record or launch an absent private application.
