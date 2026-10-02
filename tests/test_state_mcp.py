"""Synthetic integration tests for the bundled Project State stdio server."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "plugin/scripts/start-state-mcp.mjs"
sys.path.insert(0, str(ROOT / "scripts"))
from validate_codex_adaptation import validate_caches  # noqa: E402


class MCP:
    def __init__(self, facility: Path, read_only: bool = False):
        env = dict(os.environ)
        env.update(
            PROJECT_STATE_ACTOR="synthetic@example.test",
            PROJECT_STATE_REGISTRY="off",
            PROJECT_STATE_NO_OS_ACTOR="1",
            PROJECT_STATE_READ_ONLY="1" if read_only else "0",
        )
        self.process = subprocess.Popen(
            ["node", str(SERVER), "--root", str(facility)],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self.sequence = 0
        self.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "synthetic-test", "version": "1"},
        })
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict | None = None):
        self.sequence += 1
        self.process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params or {}
        }) + "\n")
        self.process.stdin.flush()
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise AssertionError(f"MCP exited {self.process.poll()}: {self.process.stderr.read()}")
            response = json.loads(line)
            if response.get("id") == self.sequence:
                if "error" in response:
                    raise AssertionError(response["error"])
                return response["result"]

    def call(self, name: str, arguments: dict | None = None):
        value = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        payload = "\n".join(block.get("text", "") for block in value.get("content", []) if block["type"] == "text")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = payload
        return value.get("isError", False), data

    def close(self):
        self.process.terminate()
        try:
            self.process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate(timeout=5)


class StateMCPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ps-mcp-test-")
        self.facility = Path(self.temporary.name) / "project-state"
        self.facility.mkdir()
        self.manifest = self.facility / "manifest.yaml"
        self.manifest.write_text(
            "schema_version: 2\nmanifest_kind: project\nproject:\n  name: synthetic\n  kind: legacy-kind\n  packs_loaded: []\n"
            "capabilities:\n  tender-intelligence:\n    enabled: true\ncustom_future_field:\n  preserve: this\n",
            encoding="utf-8",
        )
        (self.facility / "state.json").write_text('{"current_phase":"planning"}\n', encoding="utf-8")
        (self.facility / "automation").mkdir()
        (self.facility / "automation/tasks.yaml").write_text("tasks:\n  - id: legacy-cadence\n    enabled: true\n", encoding="utf-8")
        self.server = MCP(self.facility)

    def tearDown(self):
        self.server.close()
        self.temporary.cleanup()

    def test_discovery_read_hash_guard_and_attribution(self):
        names = {t["name"] for t in self.server.request("tools/list")["tools"]}
        self.assertTrue({"project_list", "get_entity", "entity_patch", "log_append"} <= names)
        error, listing = self.server.call("project_list")
        self.assertFalse(error, listing)
        self.assertIn("local/synthetic", str(listing))
        error, entity = self.server.call("get_entity", {"project": "local/synthetic", "path": "manifest.yaml"})
        self.assertFalse(error, entity)
        self.assertIn("sha256", str(entity))
        original = self.manifest.read_bytes()
        original_sha = hashlib.sha256(original).hexdigest()
        error, updated = self.server.call("entity_patch", {
            "project": "local/synthetic", "path": "manifest.yaml",
            "set": {"new_flag": "checked"}, "base_sha256": original_sha
        })
        self.assertFalse(error, updated)
        result = yaml.safe_load(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(result["custom_future_field"], {"preserve": "this"})
        self.assertNotIn("caches", result)
        self.assertEqual(result["capabilities"]["tender-intelligence"]["enabled"], True)
        self.assertEqual(result["last_modified_by"], "synthetic@example.test")
        self.assertEqual((self.facility / "automation/tasks.yaml").read_text(encoding="utf-8"), "tasks:\n  - id: legacy-cadence\n    enabled: true\n")
        before_stale = self.manifest.read_bytes()
        error, refusal = self.server.call("entity_patch", {
            "project": "local/synthetic", "path": "manifest.yaml",
            "set": {"new_flag": "stale"}, "base_sha256": original_sha
        })
        self.assertTrue(error, refusal)
        self.assertEqual(self.manifest.read_bytes(), before_stale)
        error, logged = self.server.call("log_append", {
            "project": "local/synthetic", "event": "project.checked", "summary": "Synthetic validation"
        })
        self.assertFalse(error, logged)
        line = json.loads((self.facility / "logs/activity.ndjson").read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(line["actor"], "synthetic@example.test")
        self.assertEqual(line["event"], "project.checked")

    def test_read_only_server_exposes_no_write_tools(self):
        self.server.close()
        before = {p.relative_to(self.facility).as_posix(): p.read_bytes() for p in self.facility.rglob("*") if p.is_file()}
        self.server = MCP(self.facility, read_only=True)
        names = {t["name"] for t in self.server.request("tools/list")["tools"]}
        self.assertIn("project_list", names)
        self.assertTrue({"entity_patch", "entity_put", "log_append"}.isdisjoint(names))
        error, result = self.server.call("project_list")
        self.assertFalse(error, result)
        after = {p.relative_to(self.facility).as_posix(): p.read_bytes() for p in self.facility.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_upstream_research_migration_and_disable_preserve_existing_state(self):
        source = Path(self.temporary.name) / ".research-state"
        (source / "mandates").mkdir(parents=True)
        history = self.facility / "logs/activity.ndjson"
        history.parent.mkdir(exist_ok=True)
        history.write_text('{"event":"legacy.existing","actor":"historical@example.test"}\n', encoding="utf-8")
        original_source = sorted(p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file())
        schedule = (self.facility / "automation/tasks.yaml").read_bytes()
        script = ROOT / "plugin/capabilities/research/scripts/migrate_research_state.py"
        args = [sys.executable, str(script), str(source), str(self.facility), "--today", "2026-09-30"]
        migration_env = dict(os.environ, PYTHONIOENCODING="utf-8")
        planned = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=migration_env)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertIn("plan only", planned.stdout)
        self.assertFalse((self.facility / "research").exists())
        written = subprocess.run(args + ["--write", "--actor", "synthetic@example.test"], capture_output=True, text=True, encoding="utf-8", env=migration_env, check=True)
        self.assertIn("written", written.stdout)
        migrated = yaml.safe_load(self.manifest.read_text(encoding="utf-8"))
        self.assertTrue(migrated["capabilities"]["research"]["enabled"])
        self.assertTrue(migrated["capabilities"]["tender-intelligence"]["enabled"])
        self.assertEqual(migrated["custom_future_field"], {"preserve": "this"})
        self.assertNotIn("caches", migrated)
        self.assertEqual((self.facility / "automation/tasks.yaml").read_bytes(), schedule)
        self.assertEqual(sorted(p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()), original_source)
        lines = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(lines[0]["event"], "legacy.existing")
        self.assertTrue(any(line["event"] == "capability.enabled" and line["actor"] == "synthetic@example.test" for line in lines))
        self.assertTrue(any(line["event"] == "research.migrated" for line in lines))
        original_sha = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        migrated["capabilities"]["research"]["enabled"] = False
        error, result = self.server.call("entity_patch", {
            "project": "local/synthetic", "path": "manifest.yaml",
            "set": {"capabilities": migrated["capabilities"]}, "base_sha256": original_sha,
        })
        self.assertFalse(error, result)
        disabled = yaml.safe_load(self.manifest.read_text(encoding="utf-8"))
        self.assertFalse(disabled["capabilities"]["research"]["enabled"])
        self.assertTrue(disabled["capabilities"]["tender-intelligence"]["enabled"])
        self.assertEqual((self.facility / "automation/tasks.yaml").read_bytes(), schedule)
        self.assertEqual(len(history.read_text(encoding="utf-8").splitlines()), len(lines))

    def test_optional_cache_register_validation(self):
        repo = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        (repo / ".gitignore").write_text(".cache/\n", encoding="utf-8")
        self.assertEqual(validate_caches({}, repo), ([], [], []))
        self.assertEqual(validate_caches({"caches": None}, repo), ([], [], []))
        self.assertEqual(validate_caches({"caches": []}, repo), ([], [], []))
        good = {"artifact": "Synthetic binary", "tool": "example", "path": ".cache/example", "setting": "CACHE_DIR=.cache/example"}
        self.assertEqual(validate_caches({"caches": [good]}, repo), ([], [], []))
        invalid = [{**good, "path": "../outside"}, {**good, "path": "node_modules/tool"}, {**good, "path": "not-ignored/tool"}, {**good, "setting": ""}]
        for entry in invalid:
            errors, _, _ = validate_caches({"caches": [entry]}, repo)
            self.assertTrue(errors, entry)

    def test_scheduler_registry_update_and_event_identity_protocol(self):
        schedule = self.facility / "automation/tasks.yaml"
        prior_sha = hashlib.sha256(schedule.read_bytes()).hexdigest()
        tasks = [{"id": "legacy-cadence", "enabled": True, "cadence": {"kind": "weekly", "day": "Friday"}, "operator_note": "keep"}]
        error, result = self.server.call("entity_patch", {
            "project": "local/synthetic", "path": "automation/tasks.yaml",
            "set": {"tasks": tasks}, "base_sha256": prior_sha,
        })
        self.assertFalse(error, result)
        self.assertEqual(yaml.safe_load(schedule.read_text(encoding="utf-8"))["tasks"], tasks)
        self.assertFalse((self.facility / "automation/schedule.yaml").exists())
        helper = ROOT / "plugin/skills/project-state/scripts/event_identity.py"
        facts = [
            {"event": "scheduler.reschedule", "target": "automation/tasks.yaml#legacy-cadence", "fact": {"day": "Friday", "kind": "weekly"}},
            {"fact": {"kind": "weekly", "day": "Friday"}, "target": "automation/tasks.yaml#legacy-cadence", "event": "scheduler.reschedule"},
        ]
        ids = []
        for fact in facts:
            result = subprocess.run([sys.executable, str(helper)], input=json.dumps(fact), text=True, encoding="utf-8", capture_output=True, check=True)
            ids.append(result.stdout.strip())
        self.assertEqual(ids[0], ids[1])
        self.assertTrue(ids[0].startswith("evt-"))
        error, logged = self.server.call("log_append", {
            "project": "local/synthetic", "event": "scheduler.reschedule",
            "summary": "Moved synthetic cadence", "id": ids[0],
        })
        self.assertFalse(error, logged)
        history = self.facility / "logs/activity.ndjson"
        lines = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(line.get("id") == ids[1] for line in lines), 1)
        # The skill protocol reads this identity before deciding to append. The
        # server's raw log_append intentionally remains an append-only primitive.
        existing = any(line.get("id") == ids[1] for line in lines)
        self.assertTrue(existing)
        self.assertEqual(len(history.read_text(encoding="utf-8").splitlines()), len(lines))

    def test_milestone_domain_update_repeat_and_stale_revision(self):
        folder = self.facility / "milestones"
        folder.mkdir()
        milestone = folder / "M01-test.yaml"
        milestone.write_text(
            "id: M01\nkind: milestone\ntitle: Synthetic milestone\nstatus: in_progress\n"
            "percent_complete: 75\nlast_modified: '2026-09-29T12:00:00Z'\n",
            encoding="utf-8",
        )
        stale = "2026-09-29T12:00:00Z"
        error, changed = self.server.call("milestone_update", {
            "project": "local/synthetic", "id": "M01", "status": "in_progress",
            "percent_complete": 80, "base_last_modified": stale,
        })
        self.assertFalse(error, changed)
        self.assertEqual(yaml.safe_load(milestone.read_text(encoding="utf-8"))["percent_complete"], 80)
        history = self.facility / "logs/activity.ndjson"
        changed_bytes = milestone.read_bytes(), history.read_bytes()
        fresh = yaml.safe_load(milestone.read_text(encoding="utf-8"))["last_modified"]
        error, repeated = self.server.call("milestone_update", {
            "project": "local/synthetic", "id": "M01", "status": "in_progress",
            "percent_complete": 80, "base_last_modified": fresh,
        })
        self.assertFalse(error, repeated)
        self.assertIn("unchanged", str(repeated))
        self.assertEqual((milestone.read_bytes(), history.read_bytes()), changed_bytes)
        error, refused = self.server.call("milestone_update", {
            "project": "local/synthetic", "id": "M01", "percent_complete": 85,
            "base_last_modified": stale,
        })
        self.assertTrue(error, refused)
        self.assertEqual((milestone.read_bytes(), history.read_bytes()), changed_bytes)

    def test_read_views_do_not_mutate_or_finalize_running_job(self):
        jobs = self.facility / "outbox/jobs"
        jobs.mkdir(parents=True)
        job = jobs / "synthetic-running.json"
        job.write_text(json.dumps({
            "id": "synthetic-running", "label": "Still running", "status": "running",
            "started_at": "2026-09-30T12:00:00Z", "cost_usd": None,
        }) + "\n", encoding="utf-8")
        before = {p.relative_to(self.facility).as_posix(): p.read_bytes() for p in self.facility.rglob("*") if p.is_file()}
        names = {tool["name"] for tool in self.server.request("tools/list")["tools"]}
        for name in ("view_documents", "view_outputs", "view_goals", "view_jobs"):
            self.assertIn(name, names)
            error, result = self.server.call(name, {"project": "local/synthetic"})
            self.assertFalse(error, (name, result))
            if name == "view_jobs":
                self.assertIn("running", str(result))
                self.assertIn("synthetic-running", str(result))
        after = {p.relative_to(self.facility).as_posix(): p.read_bytes() for p in self.facility.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
