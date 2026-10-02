#!/usr/bin/env python3
"""Validate the Codex package against its pinned upstream Project State release."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate keys."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key {key!r} at {key_node.start_mark}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def strict_json(text):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError(f"duplicate JSON key {key!r}")
            value[key] = item
        return value
    return json.loads(text, object_pairs_hook=pairs)


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8").stdout


def tree(root, ref):
    return set(git(root, "ls-tree", "-r", "--name-only", ref).splitlines())


def frontmatter(text, source):
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.DOTALL)
    assert match, f"missing frontmatter: {source}"
    value = yaml.load(match.group(1), Loader=UniqueKeyLoader)
    assert isinstance(value, dict), f"invalid frontmatter: {source}"
    return value


def validate_inventory(root, info):
    upstream_paths = tree(root, info["commit"])
    current_paths = {p.relative_to(root).as_posix() for p in (root / "plugin").rglob("*") if p.is_file()}
    missing = {p for p in upstream_paths - current_paths if p.startswith("plugin/") and not p.startswith("plugin/.claude-plugin/") and p not in {"plugin/CODEX.md", "plugin/.mcp.json"}}
    assert not missing, "upstream payload missing:\n" + "\n".join(sorted(missing))
    upstream_names = set()
    for rel in sorted(p for p in upstream_paths if p.startswith("plugin/skills/") and p.endswith("/SKILL.md")):
        name = frontmatter(git(root, "show", f"{info['commit']}:{rel}"), rel).get("name")
        assert isinstance(name, str) and name and name not in upstream_names, f"duplicate upstream skill {name}"
        upstream_names.add(name)
    local_names = set()
    for path in (root / "plugin/skills").rglob("SKILL.md"):
        rel = path.relative_to(root).as_posix()
        fm = frontmatter(path.read_text(encoding="utf-8"), rel)
        name = fm.get("name")
        assert isinstance(name, str) and name and name not in local_names, f"duplicate skill {rel}"
        assert isinstance(fm.get("description"), str) and fm["description"].strip(), f"missing description {rel}"
        local_names.add(name)
    assert local_names == upstream_names, f"skill discovery mismatch: missing={upstream_names-local_names}, extra={local_names-upstream_names}"
    result = [len(local_names)]
    for section in ("packs", "capabilities"):
        expected = {Path(p).parts[2] for p in upstream_paths if p.startswith(f"plugin/{section}/")}
        actual = {p.name for p in (root / "plugin" / section).iterdir() if p.is_dir()}
        assert actual == expected, f"{section} mismatch: missing={expected-actual}, extra={actual-expected}"
        result.append(len(actual))
    return result


def validate_manifest(root, info):
    manifest = strict_json((root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "project-state"
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]), "use a plain semantic package version"
    assert tuple(map(int, manifest["version"].split("."))) >= tuple(map(int, info["version"].split("."))), "package version precedes its upstream baseline"
    assert manifest["skills"] == "./plugin/skills/"
    assert manifest["license"] == "MIT" and manifest["author"]["name"] == "Atomic 47 Labs"
    assert manifest.get("mcpServers") == "./.mcp.json", "Codex MCP registration missing"
    mcp = strict_json((root / ".mcp.json").read_text(encoding="utf-8"))
    server = mcp["mcpServers"]["project-state"]
    assert server["command"] == "node"
    assert server["cwd"] == ".", "relative MCP cwd must resolve from the installed plugin root"
    assert server["args"] == ["./plugin/scripts/start-state-mcp.mjs"], "use a plugin-root-relative launcher path"
    assert (root / "plugin/scripts/start-state-mcp.mjs").is_file()
    assert (root / "plugin/server/state-mcp-local.mjs").is_file()
    assert not (root / "skills").exists(), "root skills duplicate payload"


def validate_files(root):
    counts = dict(json=0, yaml=0, python=0, javascript=0, archives=0)
    paths = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.relative_to(root).parts[0] in {"plugin", "scripts", ".codex-plugin"}}
    paths |= {".mcp.json", "upstream.json"}
    for rel in sorted(paths):
        path = root / rel
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext == ".json":
            strict_json(path.read_text(encoding="utf-8")); counts["json"] += 1
        elif ext in {".yaml", ".yml"}:
            yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader); counts["yaml"] += 1
        elif ext == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel); counts["python"] += 1
        elif ext in {".js", ".mjs", ".cjs"}:
            subprocess.run(["node", "--check", str(path)], cwd=root, check=True, capture_output=True); counts["javascript"] += 1
        elif rel.endswith((".tar", ".tar.gz", ".tgz", ".zip")):
            with (zipfile.ZipFile(path) if ext == ".zip" else tarfile.open(path, "r:*")) as archive:
                members = archive.infolist() if ext == ".zip" else archive.getmembers()
                for member in members:
                    name = member.filename if ext == ".zip" else member.name
                    normalized = name.replace("\\", "/")
                    assert not normalized.startswith("/") and not re.match(r"^[A-Za-z]:", normalized)
                    assert ".." not in PurePosixPath(normalized).parts, f"unsafe archive member {name}"
                    if ext != ".zip":
                        assert not member.isdev(), f"device archive member {name}"
                        if member.issym() or member.islnk():
                            target = member.linkname.replace("\\", "/")
                            assert not target.startswith("/") and ".." not in PurePosixPath(target).parts, f"unsafe archive link {name}"
            counts["archives"] += 1
    return counts


def validate_links(root):
    checked, missing = 0, []
    for path in (root / "plugin/skills").rglob("*.md"):
        prose = re.sub(r"```.*?```|`[^`\n]+`", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        for raw in re.findall(r"!?\[[^]]*\]\(([^)]+)\)", prose):
            target = unquote(raw.strip().split()[0].strip("<>").split("#", 1)[0])
            if not target or re.match(r"(?:[a-z]+:|/|#)", target) or any(mark in target for mark in "{}*<>"):
                continue
            checked += 1
            if not (path.parent / target).exists():
                missing.append(f"{path.relative_to(root)}: {target}")
    assert not missing, "broken skill links:\n" + "\n".join(missing)
    return checked


def validate_resources(root):
    """Check pack references that are used to install and seed projects."""
    pack_root = root / "plugin/packs"
    names = {p.name for p in pack_root.iterdir() if p.is_dir()}
    checked = 0
    for folder in pack_root.iterdir():
        if not folder.is_dir():
            continue
        manifest_path = folder / "manifest.yaml"
        assert manifest_path.is_file(), f"missing pack manifest: {folder.name}"
        value = yaml.load(manifest_path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        assert value["pack"]["id"] == folder.name, f"pack id mismatch: {folder.name}"
        for dependency in value.get("depends_on", {}).get("packs", []) or []:
            assert dependency in names, f"missing pack dependency: {folder.name} -> {dependency}"
        for conflict in value.get("conflicts_with", {}).get("packs", []) or []:
            assert conflict in names, f"missing pack conflict: {folder.name} -> {conflict}"
        provides = value.get("provides", {})
        defaults = provides.get("reporting_matrix_defaults")
        if defaults:
            target = folder / (defaults if isinstance(defaults, str) else "reporting-matrix-defaults.yaml")
            assert target.is_file(), f"missing reporting defaults: {folder.name}"
            checked += 1
        for seed in provides.get("seeds", []) or []:
            assert (folder / "seeds" / f"{seed}.yaml").is_file(), f"missing {seed} seed: {folder.name}"
            checked += 1
    for folder in (root / "plugin/capabilities").iterdir():
        if not folder.is_dir():
            continue
        assert (folder / "plugin.yaml").is_file(), f"missing capability manifest: {folder.name}"
        assert (folder / "schema").is_dir(), f"missing capability schema: {folder.name}"
        value = yaml.load((folder / "plugin.yaml").read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        assert value["plugin"]["id"] == folder.name, f"capability id mismatch: {folder.name}"
        checked += 1
    return checked


def validate_host_instructions(root):
    failures = []
    for path in (root / "plugin/skills").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"claude\.ai|Cowork device|agent-loader|CLAUDE_PLUGIN_ROOT", text, re.IGNORECASE):
            failures.append(path.relative_to(root).as_posix())
    assert not failures, "unsupported active host instructions:\n" + "\n".join(failures)


def validate_caches(manifest, repo):
    """Validate the optional cache register without creating a cache directory."""
    entries = manifest.get("caches")
    if entries is None:
        return [], [], []
    if not isinstance(entries, list):
        return ["caches must be a list or null"], [], []
    errors, warnings, unchecked = [], [], []
    for index, entry in enumerate(entries):
        label = f"caches[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be a mapping")
            continue
        for field in ("artifact", "tool", "path", "setting"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                errors.append(f"{label}.{field} is required")
        raw = entry.get("path")
        if not isinstance(raw, str) or not raw.strip():
            continue
        normalized = raw.replace("\\", "/")
        pieces = PurePosixPath(normalized).parts
        if normalized.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", normalized) or ".." in pieces:
            errors.append(f"{label}.path must stay within the repository")
            continue
        if "node_modules" in pieces:
            errors.append(f"{label}.path must not be in node_modules")
        if not normalized.startswith(".cache/") and normalized != ".cache" and not entry.get("note"):
            warnings.append(f"{label}.path is outside .cache without a note")
        subrepo = entry.get("repo")
        candidate = repo / subrepo if isinstance(subrepo, str) else repo
        if isinstance(subrepo, str) and (Path(subrepo).is_absolute() or ".." in Path(subrepo).parts):
            errors.append(f"{label}.repo must stay within the project")
            continue
        if not candidate.is_dir():
            unchecked.append(f"{label}.path repository not on this machine")
            continue
        result = subprocess.run(["git", "-C", str(candidate), "check-ignore", "-q", "--", normalized.rstrip("/") + "/"], capture_output=True)
        if result.returncode == 1:
            errors.append(f"{label}.path is not git-ignored")
        elif result.returncode != 0:
            unchecked.append(f"{label}.path ignore status not checked here")
    return errors, warnings, unchecked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facility", type=Path, help="optional project-state folder to check its cache register")
    args = parser.parse_args()
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip()).resolve()
    info = strict_json((root / "upstream.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"[0-9a-f]{40}", info["commit"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", info["version"])
    git(root, "cat-file", "-e", f"{info['commit']}^{{commit}}")
    skills, packs, capabilities = validate_inventory(root, info)
    validate_manifest(root, info)
    counts = validate_files(root)
    links = validate_links(root)
    resources = validate_resources(root)
    validate_host_instructions(root)
    if args.facility:
        facility = args.facility.resolve()
        manifest = yaml.load((facility / "manifest.yaml").read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        errors, warnings, unchecked = validate_caches(manifest, facility.parent)
        assert not errors, "invalid caches:\n" + "\n".join(errors)
        print(f"FACILITY caches valid; warnings={warnings}, unchecked={unchecked}")
    print(f"PASS: upstream={info['version']}@{info['commit'][:12]}, skills={skills}, packs={packs}, capabilities={capabilities}, skill_links={links}, resources={resources}, " + ", ".join(f"{k}={v}" for k,v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
