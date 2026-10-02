<!-- Optional build-playbook section for a project with heavy downloads. -->

## Heavy downloads

When a project uses a large downloaded tool or model, declare it in `project-state/manifest.yaml:caches` and configure the tool to store it in a Git-ignored repository `.cache/` directory. The `project-state` validator checks that the declared path stays inside the repository and is ignored. A CI workflow may cache that same directory using its native cache action and the relevant lockfile key.

## Long commands

Run a long build or download through the current host's process/session tools so output can be read while it runs. Check the original process and exit status after a timeout before starting another attempt. Record a measured setup time only when it matters to the project.
