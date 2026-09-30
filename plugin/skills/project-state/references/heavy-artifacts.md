# Heavy-artifacts register (`manifest.yaml → caches`)

Some tools download something large the first time they run: a test-database binary, a browser, model
weights. By default most of them cache it inside `node_modules` (or a per-user folder a CI runner
throws away), so every clean install deletes it and the next run downloads it again. In an agentic
loop every run *starts* with a clean install, so the cost repeats on every workload and every
re-run, and nobody sees it until a person notices the waiting.

Measured on CanRentPro (FB-001, issue #47): mongodb-memory-server's MongoDB binary, about 780 MB on
Windows, sat in each app's `node_modules`. Two apps meant two copies, and the W-04 re-run spent 718 s
on its first check, mostly the download. Pointing both apps at one git-ignored `.cache/` at the repo
root took a clean `npm ci` to about 2 minutes, with the tests unchanged. The fix was two config lines
and one `.gitignore` line. The expensive part was not knowing to make it.

The register makes that knowledge part of the project: which artifacts are heavy, where each one is
cached, and the setting that puts it there.

## Shape

```yaml
caches:
  - artifact: "MongoDB server binary"            # what gets downloaded, in plain words
    tool: "mongodb-memory-server"                # the package or CLI that downloads it
    size: "780 MB (Windows), 70 MB (Linux)"      # rough is fine; it tells people what they are waiting for
    path: ".cache/mongodb-memory-server"         # where it is cached, relative to the repository root
    setting: "config.mongodbMemoryServer.downloadDir = ../../.cache/mongodb-memory-server (apps/web, apps/app package.json)"
    used_by: ["apps/web", "apps/app"]            # optional: which apps share it
    repo: "."                                    # optional: the code repository, relative to the folder
                                                 # holding project-state/. Default "." (the same repository)
    note: ~                                      # optional: why the path is not under .cache/, if it is not
```

| Value | Meaning |
|---|---|
| key absent or `caches: ~` | Never asked. Valid, and never reported. |
| `caches: []` | Asked; the project downloads nothing heavy. Not asked again. |
| a list | The register. Each entry is one artifact. |

Required on each entry: `artifact`, `tool`, `path`, `setting`. `size` is asked for and recommended;
a missing size is not an error.

## The convention: one git-ignored `.cache/` at the repository root

Every heavy artifact caches under `.cache/<tool>/` at the root of the code repository, shared by every
app in it, and `.cache/` is in the repository's `.gitignore`. That keeps it:

- **outside anything a clean install deletes**, so clean installs stay clean (the evidence is
  unchanged) and simply stop paying for the download;
- **shared**, so a monorepo with two apps downloads once, not twice;
- **one folder**, so a CI cache step (below) and a person clearing space both have one place to look.

A path outside `.cache/` is allowed when a tool cannot be moved; say why in `note`.

### Where the common tools look

The setting is always the tool's own: the register records it, and the change is made in the
project's code by whoever owns the code (a CC4PS workload, a developer), never by a project-state
skill.

| Tool | Artifact | Setting that moves the cache |
|---|---|---|
| `mongodb-memory-server` | MongoDB binary | `package.json` → `config.mongodbMemoryServer.downloadDir`, or env `MONGOMS_DOWNLOAD_DIR`. From an app two levels down: `../../.cache/mongodb-memory-server` |
| `@playwright/test`, `playwright` | Chromium, Firefox, WebKit | env `PLAYWRIGHT_BROWSERS_PATH=<repo>/.cache/ms-playwright` |
| `puppeteer` | Chrome for Testing | env `PUPPETEER_CACHE_DIR`, or `.puppeteerrc.cjs` → `cacheDirectory` |
| `cypress` | Cypress binary | env `CYPRESS_CACHE_FOLDER` |
| `electron` | Electron binary | env `ELECTRON_CACHE` |
| Hugging Face (`transformers`, `huggingface_hub`) | Model weights | env `HF_HOME` |
| `sentence-transformers` | Model weights | env `SENTENCE_TRANSFORMERS_HOME` (or `HF_HOME` on recent versions) |
| `torch.hub` | Model weights | env `TORCH_HOME` |
| `ollama` | Model weights | env `OLLAMA_MODELS` |

An environment variable only helps if every place the command runs sets it: the developer's shell,
the test script (`cross-env`, `dotenv`) and CI. A config-file setting inside the repository is
preferred where the tool has one, because it travels with the code.

## When it is asked

`project-onboarding` Q1.10 and `project-scaffolder` Step 5 ask it **once**, and only for a project
whose code lives next to the facility (a software work type, or package manifests beside
`project-state/`). Before asking, look: scan `package.json`, `pyproject.toml` and `requirements*.txt`
files in the repository (skipping `node_modules`) for the tools in the table above, and present what
you find as suggestions to confirm, each with where it caches today. Never write an entry the
operator has not seen. "Nothing heavy" writes `[]`; "not sure" leaves the key unset.

## What `project-state validate` checks

For each entry, with `<repo>` resolved from `repo` (default: the folder holding `project-state/`):

| Check | Severity |
|---|---|
| `artifact`, `tool`, `path` or `setting` missing | error |
| `path` absolute, starting with `~`, or containing a `..` segment | error: it must name a place inside the repository |
| `path` contains a `node_modules` segment | error: a clean install deletes it, which is the defect this register exists to prevent |
| `git -C <repo> check-ignore -q -- "<path>/"` exits 1 (not ignored) | error: a cached binary must never be committable |
| the same command exits 128, or `<repo>` is not on this machine | info: "not checked here", never an error. The code may live in a repository this machine does not have |
| `path` not under `.cache/` and no `note` | warning: outside the convention |

Check the path **with a trailing slash**. `git check-ignore` matches a directory pattern such as
`.cache/` against a path that does not exist yet only when the path ends in `/`, and before the
first install the cache folder does not exist.

Report; never fix. A missing ignore rule may be *offered* as a one-line `.gitignore` addition, shown
to the operator before it is written. The tool setting is never changed by this skill.

## Two things that go with it

**CI caches the same folder.** A workflow that runs the clean install should restore and save
`.cache/`, keyed on the OS and the lockfile:

```yaml
- uses: actions/cache@v4
  with:
    path: .cache
    key: heavy-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
    restore-keys: heavy-${{ runner.os }}-
```

**Long commands run visibly.** A command that downloads for minutes also trips the Cowork device
bridge, which stops responding for the whole of any command over about 60 s. The pattern for that,
written as a section to paste into a project's build playbook, is in
`templates/playbook-long-commands.md`.
