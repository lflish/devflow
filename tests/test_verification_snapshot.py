import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "dev-workflow/scripts/verification_snapshot.py"


class VerificationSnapshotTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Snapshot Test")
        self.git("config", "user.email", "snapshot@example.test")
        self.git("config", "core.filemode", "true")
        self.write("app.py", "def f(flag):\n    if flag:\n        return 1\n    return 0\n")
        self.write("asset.bin", b"\x00\x01")
        self.target = self.commit()
        self.git("branch", "target")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def call(self, command, head, target, snapshot=None, docs_dir="docs/changes"):
        args = [
            sys.executable, str(SCRIPT), command, "--repo", str(self.repo),
            "--head", head, "--target", target, "--docs-dir", docs_dir,
        ]
        if snapshot is not None:
            args += ["--snapshot", snapshot]
        return subprocess.run(args, text=True, capture_output=True)

    def snapshot(self, head, target=None):
        result = self.call("snapshot", head, target or self.target)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def assert_rejected(self, head, target, snapshot, docs_dir="docs/changes"):
        result = self.call("check", head, target, snapshot, docs_dir)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_distinguishes_semantically_different_indentation(self):
        prefix = "def f(flag):\n    if flag:\n        return 1\n"
        self.write("app.py", prefix + "    return 2\n")
        saved = self.snapshot(self.commit())
        self.write("app.py", prefix + "        return 2\n")
        self.assert_rejected(self.commit(), self.target, saved)

    def test_distinguishes_binary_content_mode_and_path(self):
        saved = self.snapshot(self.target)
        self.write("asset.bin", b"\x00\x02")
        self.assert_rejected(self.commit(), self.target, saved)
        self.git("reset", "--hard", self.target)
        os.chmod(self.repo / "asset.bin", 0o755)
        self.assert_rejected(self.commit(), self.target, saved)
        self.git("reset", "--hard", self.target)
        (self.repo / "asset.bin").rename(self.repo / "asset\tname.bin")
        self.assert_rejected(self.commit(), self.target, saved)

    def test_accepts_only_exact_documentation_paths_and_returns_current_shas(self):
        self.write("app.py", "pass\n")
        head = self.commit()
        saved = self.snapshot(head)
        self.write("docs/changes/spec.md", "result")
        self.write(".dview.json", "{}")
        head_with_docs = self.commit()
        self.git("checkout", "-q", "target")
        self.write("docs/changes/index.md", "index")
        target_with_docs = self.commit()
        result = self.call("check", head_with_docs, target_with_docs, saved, "docs/changes/")
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshot = json.loads(result.stdout)
        self.assertEqual(snapshot["head"], head_with_docs)
        self.assertEqual(snapshot["target"], target_with_docs)

        self.git("checkout", "-q", "--detach", head_with_docs)
        for path in ("docs/changeset/new.py", "nested/.dview.json", "nested/docs/changes/app.py"):
            with self.subTest(path=path):
                self.write(path, "changed")
                self.assert_rejected(self.commit(), target_with_docs, saved)
                self.git("reset", "--hard", head_with_docs)

    def test_rejects_target_code_change_even_when_pr_was_not_rebased(self):
        self.write("app.py", "pass\n")
        head = self.commit()
        saved = self.snapshot(head)
        self.git("checkout", "-q", "target")
        self.write("config.yml", "new: true\n")
        new_target = self.commit()
        self.assertEqual(self.git("merge-base", head, new_target), self.target)
        self.assert_rejected(head, new_target, saved)
        result = self.call("snapshot", head, new_target)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

        self.git("checkout", "-q", "--detach", head)
        self.git("merge", "--no-edit", new_target)
        self.snapshot(self.git("rev-parse", "HEAD"), new_target)

    def test_fails_closed_on_legacy_bad_refs_and_invalid_paths(self):
        saved = self.snapshot(self.target)
        missing_head = json.loads(saved)
        del missing_head["head"]
        original = json.loads(saved)
        invalid_fields = {
            "schema": True,
            "head": 10 ** (len(original["head"]) - 1),
            "target": 10 ** (len(original["target"]) - 1),
            "head_tree": 10 ** 63,
            "target_tree": 10 ** 63,
        }
        bad_snapshots = ["", "legacy-patch-id", "null", json.dumps(missing_head)]
        bad_snapshots.extend(
            json.dumps(dict(original, **{key: value})) for key, value in invalid_fields.items()
        )
        for bad_snapshot in bad_snapshots:
            with self.subTest(snapshot=bad_snapshot):
                self.assert_rejected(self.target, self.target, bad_snapshot)
        self.assert_rejected("missing-ref", self.target, saved)
        self.assert_rejected(self.target, self.target, saved, ".")
        self.assert_rejected(self.target, self.target, saved, "docs/other")


if __name__ == "__main__":
    unittest.main()
