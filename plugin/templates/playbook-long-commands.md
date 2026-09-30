<!--
  Drop-in playbook section: heavy downloads and long commands.

  Paste the two sections below into the project's own build playbook (for example
  project-state/documents/working/agentic-build-playbook.md) and adjust the numbers.
  From FB-001 / project-state issue #47 (CanRentPro, 2026-09-28). The register these
  sections refer to is described in skills/project-state/references/heavy-artifacts.md.
-->

## Heavy downloads

Anything a tool downloads that is large (a test-database binary, a browser, model weights) is cached
in **one git-ignored `.cache/` at the repository root**, shared by every app, and is listed in
`project-state/manifest.yaml → caches` with the setting that points the tool there.

- Never leave such a cache inside `node_modules`: every clean install deletes it, and every re-run
  downloads it again. Clean installs stay part of the evidence; they just stop paying for downloads.
- A new tool that downloads something heavy gets its register entry in the same change that adds it.
  `project-state validate` checks that each listed path is git-ignored.
- CI restores and saves the same folder:

  ```yaml
  - uses: actions/cache@v4
    with:
      path: .cache
      key: heavy-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
      restore-keys: heavy-${{ runner.os }}-
  ```

## Long commands

The Cowork device bridge stops responding for the whole of any command that runs longer than about
60 seconds. So:

1. **Anything expected to take more than about 45 seconds runs in a visible window that writes to a
   log file.** Clean installs, full test suites, builds, anything with a first-run download. The
   window stays open afterwards, so nothing runs where the operator cannot see it.
2. **Cowork starts it in one short call, then polls the log in short calls**: read the last 20 lines,
   wait at most 20 seconds, read again. It is finished when the last line starts with `EXIT`.
3. **Never** pipe a long command's output back to the end in one call, and never sleep past the
   bridge timeout in one call.
4. The log's `START` and `EXIT` lines give the setup time. Record it separately from the checks, so
   the retro sees setup cost as its own number.

Logs go to `.cache/logs/<name>.log`, which the `.cache/` rule already ignores.

### Windows (PowerShell): `tools/run-visible.ps1`

```powershell
# Run a long command in its own PowerShell window, copying every line to a log.
# Usage:   powershell -File tools/run-visible.ps1 -Name npm-ci -Command "npm ci"
# Poll:    Get-Content .cache/logs/npm-ci.log -Tail 20
param(
  [Parameter(Mandatory)][string]$Name,
  [Parameter(Mandatory)][string]$Command
)
$root = (Get-Location).Path
$logDir = Join-Path $root '.cache\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "$Name.log"
Set-Content -Path $log -Value "START $(Get-Date -Format o) $Command" -Encoding utf8
$inner = @"
Set-Location -LiteralPath '$root'
& { $Command } 2>&1 | ForEach-Object { `$line = "`$_"; `$line; Add-Content -LiteralPath '$log' -Value `$line -Encoding utf8 }
Add-Content -LiteralPath '$log' -Value "EXIT `$LASTEXITCODE `$(Get-Date -Format o)" -Encoding utf8
"@
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($inner))
Start-Process powershell -ArgumentList '-NoExit', '-EncodedCommand', $encoded
Write-Output $log
```

### macOS: `tools/run-visible.sh`

```bash
#!/usr/bin/env bash
# Run a long command in its own Terminal window, copying every line to a log.
# Usage:   tools/run-visible.sh npm-ci "npm ci"
# Poll:    tail -n 20 .cache/logs/npm-ci.log
set -eu
name=$1; command=$2
root=$(pwd)
mkdir -p "$root/.cache/logs"
log="$root/.cache/logs/$name.log"
runner="$root/.cache/logs/$name.run.sh"
printf 'START %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$command" > "$log"
{
  printf '#!/usr/bin/env bash\n'
  printf 'cd %q\n' "$root"
  printf 'set -o pipefail\n'
  printf '(\n%s\n) 2>&1 | tee -a %q\n' "$command" "$log"
  printf 'echo "EXIT $? $(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)" >> %q\n' "$log"
} > "$runner"
chmod +x "$runner"
open -a Terminal "$runner"
echo "$log"
```
