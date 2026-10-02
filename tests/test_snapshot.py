"""Exercise local snapshot recording without changing a project facility."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "plugin/server/state-snapshot.mjs"


class SnapshotTests(unittest.TestCase):
    def test_make_refresh_list_and_preservation(self):
        with tempfile.TemporaryDirectory(prefix="ps-snapshot-test-") as temporary:
            base = Path(temporary)
            facility = base / "project-state"
            facility.mkdir()
            (facility / "manifest.yaml").write_text(
                "schema_version: 2\nmanifest_kind: project\nproject:\n  name: snapshot-test\n  packs_loaded: []\n",
                encoding="utf-8",
            )
            (facility / "state.json").write_text('{"current_phase":"planning"}\n', encoding="utf-8")
            output = base / "preview/snapshot.html"
            index = base / "personal/index.json"
            def tree():
                return {p.relative_to(facility).as_posix(): p.read_bytes() if p.is_file() else None
                        for p in facility.rglob("*")}

            before = tree()

            def run(*arguments):
                return subprocess.run(["node", str(RECORDER), *arguments], cwd=ROOT,
                                      text=True, encoding="utf-8", capture_output=True, timeout=40)

            made = run("make", "--root", str(facility), "--out", str(output), "--index", str(index))
            self.assertEqual(made.returncode, 0, made.stderr)
            self.assertIn("window.PS_SNAPSHOT =", output.read_text(encoding="utf-8"))
            records = json.loads(index.read_text(encoding="utf-8"))
            key = next(iter(records))
            records[key]["custom_future_field"] = "preserve"
            index.write_text(json.dumps(records), encoding="utf-8")
            first_taken = records[key]["taken"]
            refreshed = run("refresh", "--root", str(facility), "--index", str(index))
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            records = json.loads(index.read_text(encoding="utf-8"))
            self.assertEqual(Path(records[key]["file"]), output)
            self.assertNotEqual(records[key]["taken"], first_taken)
            self.assertEqual(records[key]["custom_future_field"], "preserve")
            listing = run("list", "--index", str(index))
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertIn(str(output), listing.stdout)
            self.assertEqual(before, tree())
            rejected = run("make", "--root", str(facility), "--out", str(facility / "snapshot.html"), "--index", str(index))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse((facility / "snapshot.html").exists())
            index.write_text("invalid", encoding="utf-8")
            rejected = run("list", "--index", str(index))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(index.read_text(encoding="utf-8"), "invalid")


if __name__ == "__main__":
    unittest.main()
