#!/usr/bin/env python3
"""Read-only validation for the Project State Codex lean adaptation."""

from __future__ import annotations

import ast
import fnmatch
import json
import os
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

try:
    import yaml
except ImportError as exc:  # pragma: no cover - an actionable environment failure
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc


BASELINE_REF = "upstream-v4.9.0"
BASELINE_COMMIT = "c0b55ba52dfdca9312a1f6150039ed14d569e2db"
EXPECTED_SKILL_COUNT = 43
EXPECTED_PACKS = {
    "agile-default",
    "board-investor",
    "client-services",
    "grant-canada",
    "open-source-community",
    "pic-pcais",
    "sred-canada",
    "tender-pursuit",
}
EXPECTED_CAPABILITIES = {"sred", "tender-intelligence"}
EXPECTED_EVENTS = {
    "inbox.triage.document",
    "project.intake.completed",
    "report.generated",
    "tender.deadline.changed",
    "tender.harvest.completed",
}
EXPECTED_REPORT_PATHS = {
    "reports/weekly/YYYY-Www.md",
    "reports/adhoc/YYYY-MM-brief.md",
    "reports/sc-meetings/<id>-pack.docx",
    "reports/sc-meetings/<id>-agenda.docx",
    "reports/pic-submissions/YYYY-QN-ms-financial.xlsx",
    "reports/claims/YYYY-QN.yaml",
    "reports/custom-defs/<slug>.yaml",
    "reports/onepagers/<YYYY-MM-DD>-<slug>.html",
    "project-state/reports/unified-suite/YYYY-MM-DD/",
    "project-state/reports/tech/<report-id>/<stamp>.md",
}
ALLOWED_PROTECTED_CHANGES = {
    "plugin/capabilities/sred/README.md",
    "plugin/capabilities/sred/packs/sred-canada/README.md",
    "plugin/capabilities/sred/plugin.yaml",
    "plugin/capabilities/sred/routine.yaml",
    "plugin/capabilities/sred/schema/entities.yaml",
    "plugin/capabilities/sred/validator/validate-sred.md",
    "plugin/packs/agile-default/manifest.yaml",
    "plugin/packs/board-investor/manifest.yaml",
    "plugin/packs/board-investor/profiles/funder-reporting.yaml",
    "plugin/packs/client-services/manifest.yaml",
    "plugin/packs/grant-canada/manifest.yaml",
    "plugin/packs/open-source-community/manifest.yaml",
    "plugin/packs/pic-pcais/manifest.yaml",
    "plugin/packs/sred-canada/README.md",
    "plugin/packs/tender-pursuit/manifest.yaml",
    "plugin/templates/lesson-learned.md",
    "plugin/templates/manifest-v2.yaml",
    "plugin/templates/manifest.yaml",
    "plugin/templates/phase-presets/agile-default.yaml",
    "plugin/templates/phase-presets/client-engagement-default.yaml",
    "plugin/templates/phase-presets/grant-default.yaml",
    "plugin/templates/phase-presets/open-source-default.yaml",
    "plugin/templates/phase-presets/waterfall-default.yaml",
    "plugin/templates/reporting-matrix.yaml",
}
ALLOWED_PROTECTED_SEMANTIC_PATHS = {
    "plugin/capabilities/sred/plugin.yaml": {"plugin.spec"},
    "plugin/templates/phase-presets/agile-default.yaml": {"description"},
    "plugin/templates/phase-presets/client-engagement-default.yaml": {"description"},
    "plugin/templates/phase-presets/grant-default.yaml": {"description"},
    "plugin/templates/phase-presets/open-source-default.yaml": {"description"},
    "plugin/templates/phase-presets/waterfall-default.yaml": {"description"},
}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(loader: UniqueKeyLoader, node: yaml.Node, deep: bool = False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key {key!r} at {key_node.start_mark}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def run(*args: str, cwd: Path, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args), cwd=cwd, check=True, capture_output=True, text=text
    )


def git_text(root: Path, *args: str) -> str:
    return run("git", *args, cwd=root).stdout


def git_bytes(root: Path, spec: str) -> bytes:
    return run("git", "show", spec, cwd=root, text=False).stdout


def tracked_paths(root: Path, ref: str = "HEAD", prefix: str | None = None) -> set[str]:
    args = ["ls-tree", "-r", "--name-only", ref]
    if prefix:
        args.extend(["--", prefix])
    return {line for line in git_text(root, *args).splitlines() if line}


def current_text(root: Path) -> str:
    chunks: list[str] = []
    for rel in sorted(tracked_paths(root)):
        path = root / rel
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            chunks.append(path.read_text(encoding="utf-8", errors="strict"))
    return "\n".join(chunks)


def frontmatter(text: str, source: str) -> dict:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, flags=re.DOTALL)
    if not match:
        raise AssertionError(f"missing YAML frontmatter: {source}")
    data = yaml.load(match.group(1), Loader=UniqueKeyLoader)
    if not isinstance(data, dict):
        raise AssertionError(f"invalid YAML frontmatter: {source}")
    return data


def validate_baseline(root: Path) -> None:
    baseline = git_text(root, "rev-parse", f"{BASELINE_REF}^{{commit}}").strip()
    assert baseline == BASELINE_COMMIT, (baseline, BASELINE_COMMIT)
    main = git_text(root, "rev-parse", "main^{commit}").strip()
    assert main == BASELINE_COMMIT, "local main must remain byte-equivalent to upstream v4.9.0"


def validate_skills(root: Path) -> None:
    current_files = sorted((root / "plugin" / "skills").rglob("SKILL.md"))
    current_names: dict[str, str] = {}
    for path in current_files:
        rel = path.relative_to(root).as_posix()
        data = frontmatter(path.read_text(encoding="utf-8"), rel)
        name = data.get("name")
        description = data.get("description")
        assert isinstance(name, str) and name, f"missing skill name: {rel}"
        assert isinstance(description, str) and description, f"missing skill description: {rel}"
        assert name not in current_names, f"duplicate skill name: {name}"
        current_names[name] = rel
        adapter = os.path.relpath(root / "plugin" / "CODEX.md", path.parent).replace("\\", "/")
        expected = f"> Codex adapter: Read [CODEX.md]({adapter}) before using this skill."
        assert expected in path.read_text(encoding="utf-8"), f"missing adapter link: {rel}"

    baseline_names: set[str] = set()
    for rel in sorted(tracked_paths(root, BASELINE_REF, "plugin/skills")):
        if not rel.endswith("/SKILL.md"):
            continue
        text = git_bytes(root, f"{BASELINE_REF}:{rel}").decode("utf-8")
        baseline_names.add(frontmatter(text, f"{BASELINE_REF}:{rel}")["name"])

    assert len(current_names) == EXPECTED_SKILL_COUNT, len(current_names)
    assert set(current_names) == baseline_names, "public skill-name set changed"


def validate_manifest(root: Path) -> None:
    manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text("utf-8"))
    assert manifest["name"] == "project-state"
    assert manifest["skills"] == "./plugin/skills/"
    assert manifest["license"] == "MIT"
    assert manifest["repository"] == "https://github.com/Atomic-47-Labs/project-state-plugin-public"
    assert manifest["author"]["name"] == "Atomic 47 Labs"

    assert (root / "plugin" / "skills").is_dir(), "upstream skills payload is missing"
    root_skills = root / "skills"
    assert not root_skills.exists() and not root_skills.is_symlink(), (
        "root skills must not duplicate or link the upstream payload"
    )


def validate_structured_files(root: Path) -> tuple[int, int]:
    json_count = 0
    yaml_count = 0
    for rel in sorted(tracked_paths(root)):
        path = root / rel
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        elif suffix in {".yaml", ".yml"}:
            yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
            yaml_count += 1
    return json_count, yaml_count


def validate_code(root: Path) -> tuple[int, int]:
    py_count = 0
    js_count = 0
    for rel in sorted(tracked_paths(root)):
        path = root / rel
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            py_count += 1
        elif suffix in {".js", ".mjs", ".cjs"}:
            run("node", "--check", str(path), cwd=root)
            js_count += 1
    return py_count, js_count


def _safe_archive_name(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    assert not path.is_absolute(), f"absolute archive member: {name}"
    assert not re.match(r"^[A-Za-z]:", normalized), f"drive-qualified archive member: {name}"
    assert ".." not in path.parts, f"traversing archive member: {name}"
    return path


def validate_archives(root: Path) -> int:
    count = 0
    for rel in sorted(tracked_paths(root)):
        path = root / rel
        lower = rel.lower()
        if lower.endswith((".tgz", ".tar.gz", ".tar")):
            with tarfile.open(path, mode="r:*") as archive:
                for member in archive.getmembers():
                    member_path = _safe_archive_name(member.name)
                    assert not member.isdev(), f"device archive member: {member.name}"
                    if member.issym() or member.islnk():
                        target = _safe_archive_name(member.linkname)
                        combined = member_path.parent.joinpath(target)
                        assert ".." not in combined.parts, f"escaping archive link: {member.name}"
            count += 1
        elif lower.endswith(".zip"):
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    _safe_archive_name(info.filename)
            count += 1
    return count


def validate_local_links(root: Path) -> int:
    checked = 0
    link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    dangling_docs_re = re.compile(r"(?<![\w-])docs/[A-Za-z0-9._/-]+\.md")
    failures: list[str] = []
    for rel in sorted(tracked_paths(root)):
        if not rel.endswith(".md"):
            continue
        path = root / rel
        text = path.read_text(encoding="utf-8")
        for token in dangling_docs_re.findall(text):
            candidates = [path.parent / token, root / token, root / "plugin" / token]
            if not any(candidate.exists() for candidate in candidates):
                failures.append(f"{rel}: {token}")
        # Generated-output examples commonly contain Markdown-looking links in
        # code spans. They are contracts for future artifacts, not repository
        # references, so only inspect links in prose.
        prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        prose = re.sub(r"`[^`\n]+`", "", prose)
        for match in link_re.finditer(prose):
            target = match.group(1).strip().split()[0].strip("<>")
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target or target.startswith(("#", "/", "http://", "https://", "mailto:", "codex:")):
                continue
            if any(mark in target for mark in ("<", ">", "*", "{", "}")):
                continue
            checked += 1
            if not (path.parent / target).exists():
                failures.append(f"{rel}: {target}")
    assert not failures, "missing relative references:\n" + "\n".join(failures)
    return checked


def validate_protected_contract(root: Path) -> None:
    for prefix in ("plugin/templates", "plugin/packs", "plugin/capabilities"):
        before = tracked_paths(root, BASELINE_REF, prefix)
        after = tracked_paths(root, "HEAD", prefix)
        assert before == after, f"protected path inventory changed under {prefix}"

    changed = set(git_text(root, "diff", "--name-only", f"{BASELINE_REF}..HEAD").splitlines())
    protected = {
        path
        for path in changed
        if path.startswith(("plugin/templates/", "plugin/packs/", "plugin/capabilities/"))
    }
    unexpected = protected - ALLOWED_PROTECTED_CHANGES
    assert not unexpected, "unjustified protected changes: " + ", ".join(sorted(unexpected))

    def semantic_differences(before, after, prefix: str = "") -> set[str]:
        if type(before) is not type(after):
            return {prefix}
        if isinstance(before, dict):
            differences: set[str] = set()
            for key in set(before) | set(after):
                path = f"{prefix}.{key}" if prefix else str(key)
                if key not in before or key not in after:
                    differences.add(path)
                else:
                    differences |= semantic_differences(before[key], after[key], path)
            return differences
        if isinstance(before, list):
            differences = set()
            if len(before) != len(after):
                differences.add(f"{prefix}.length")
            for index, (old, new) in enumerate(zip(before, after)):
                differences |= semantic_differences(old, new, f"{prefix}[{index}]")
            return differences
        return set() if before == after else {prefix}

    for rel in sorted(protected):
        if not rel.endswith((".yaml", ".yml", ".json")):
            continue
        before_text = git_bytes(root, f"{BASELINE_REF}:{rel}").decode("utf-8")
        after_text = (root / rel).read_text(encoding="utf-8")
        if rel.endswith(".json"):
            before = json.loads(before_text)
            after = json.loads(after_text)
        else:
            before = yaml.load(before_text, Loader=UniqueKeyLoader)
            after = yaml.load(after_text, Loader=UniqueKeyLoader)
        differences = semantic_differences(before, after)
        allowed = ALLOWED_PROTECTED_SEMANTIC_PATHS.get(rel, set())
        assert differences <= allowed, (
            f"unjustified protected semantic changes in {rel}: "
            + ", ".join(sorted(differences - allowed))
        )

    pack_dirs = {p.name for p in (root / "plugin" / "packs").iterdir() if p.is_dir()}
    capability_dirs = {
        p.name for p in (root / "plugin" / "capabilities").iterdir() if p.is_dir()
    }
    assert pack_dirs == EXPECTED_PACKS, pack_dirs
    assert capability_dirs == EXPECTED_CAPABILITIES, capability_dirs


def validate_contract_terms(root: Path) -> None:
    text = current_text(root)
    missing_events = sorted(event for event in EXPECTED_EVENTS if event not in text)
    missing_paths = sorted(path for path in EXPECTED_REPORT_PATHS if path not in text)
    assert not missing_events, "missing event terms: " + ", ".join(missing_events)
    assert not missing_paths, "missing report paths: " + ", ".join(missing_paths)

    manifest_v2 = yaml.load(
        (root / "plugin" / "templates" / "manifest-v2.yaml").read_text("utf-8"),
        Loader=UniqueKeyLoader,
    )
    assert manifest_v2["schema_version"] == 2
    assert manifest_v2["manifest_kind"] == "project"


def validate_forbidden_content(root: Path) -> None:
    private_patterns = {
        "private dashboard hostname": re.compile(r"kanban-atomic47|stonemaps\.org", re.I),
        "private credential/token": re.compile(
            r"\bksm_[A-Za-z0-9_-]+|\bteam_[A-Za-z0-9_-]+|\bps_github\b|PROJECT_STATE_(?:API|ENDPOINT|TOKEN)",
            re.I,
        ),
        "absolute internal path": re.compile(r"(?:[A-Za-z]:\\Users\\|/Users/)", re.I),
    }
    claude_patterns = re.compile(
        r"Coworker|\bCowork\b|claude\.ai|Claude Code|HTML artifact|interactive HTML|artifact mode|markdown mode|\.cursor/|~/.claude",
        re.I,
    )
    email_re = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
    allowed_emails = {
        "david@atomic47.co",
        "notifications@merx.com",
        "noreply@sasktenders.ca",
        "notifications@bidsandtenders.ca",
        "solicitations-appelsdoffres@canadabuys-achatscanada.canada.ca",
    }
    allowed_domains = {"example.com", "example.org", "yourco.com", "co.com"}
    failures: list[str] = []
    for rel in sorted(tracked_paths(root)):
        if rel == "CODEX-ADAPTATION.md" or rel.startswith("scripts/"):
            continue
        path = root / rel
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        for label, pattern in private_patterns.items():
            if pattern.search(text):
                failures.append(f"{label}: {rel}")
        if rel.startswith("plugin/skills/") and rel.endswith((".md", ".py")):
            if claude_patterns.search(text):
                failures.append(f"unsupported Claude-only instruction: {rel}")
        for email in email_re.findall(text):
            normalized = email.lower().split("--", 1)[0]
            domain = normalized.rsplit("@", 1)[1]
            if normalized not in allowed_emails and domain not in allowed_domains:
                failures.append(f"unapproved personal identity {email}: {rel}")
    assert not failures, "forbidden/private content:\n" + "\n".join(sorted(set(failures)))


def validate_justification_coverage(root: Path) -> None:
    doc_path = root / "CODEX-ADAPTATION.md"
    doc = doc_path.read_text(encoding="utf-8")
    rows: dict[str, list[str]] = {}
    for line in doc.splitlines():
        if not line.startswith("| PS-CX-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        assert len(cells) == 7, f"malformed justification row: {line}"
        identifier = cells[0]
        patterns = re.findall(r"`([^`]+)`", cells[2])
        assert patterns, f"no affected-file patterns for {identifier}"
        rows[identifier] = patterns

    expected_ids = {f"PS-CX-{number:03d}" for number in range(1, 15)}
    assert set(rows) == expected_ids, (set(rows), expected_ids)

    changed = set(git_text(root, "diff", "--name-only", f"{BASELINE_REF}..HEAD").splitlines())
    uncovered = []
    for path in sorted(changed):
        if not any(
            fnmatch.fnmatchcase(path, pattern)
            for patterns in rows.values()
            for pattern in patterns
        ):
            uncovered.append(path)
    assert not uncovered, "changed files lack a justification ID:\n" + "\n".join(uncovered)

    commits = git_text(root, "log", "--format=%H%x1f%B%x1e", f"{BASELINE_REF}..HEAD")
    for record in commits.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        commit_hash, body = record.split("\x1f", 1)
        assert re.search(r"PS-CX-\d{3}", body), f"commit lacks justification ID: {commit_hash}"
        for heading in ("Why", "Compatibility", "Validation"):
            assert re.search(rf"(?im)^\s*{heading}:", body), (
                f"commit lacks {heading}: {commit_hash}"
            )


def main() -> int:
    root = Path(
        git_text(Path.cwd(), "rev-parse", "--show-toplevel").strip()
    ).resolve()
    validate_baseline(root)
    validate_skills(root)
    validate_manifest(root)
    json_count, yaml_count = validate_structured_files(root)
    py_count, js_count = validate_code(root)
    archive_count = validate_archives(root)
    link_count = validate_local_links(root)
    validate_protected_contract(root)
    validate_contract_terms(root)
    validate_forbidden_content(root)
    validate_justification_coverage(root)
    print(
        "PASS: "
        f"skills={EXPECTED_SKILL_COUNT}, packs={len(EXPECTED_PACKS)}, "
        f"capabilities={len(EXPECTED_CAPABILITIES)}, json={json_count}, "
        f"yaml={yaml_count}, python={py_count}, javascript={js_count}, "
        f"archives={archive_count}, local_links={link_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
