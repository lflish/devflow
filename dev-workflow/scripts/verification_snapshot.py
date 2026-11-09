"""Fingerprint the committed code at the candidate and destination branch tips."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys


SCHEMA = 1
COMMIT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
DIGEST = re.compile(r"[0-9a-f]{64}")


def git(repo, *args):
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", repo, *args], stderr=subprocess.PIPE,
    )


def code_digest(repo, commit, docs_dir):
    entries = git(repo, "ls-tree", "-r", "-z", "--full-tree", commit)
    docs_prefix = os.fsencode(docs_dir) + b"/"
    digest = hashlib.sha256()
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        _, path = entry.split(b"\t", 1)
        if path == b".dview.json" or path.startswith(docs_prefix):
            continue
        digest.update(entry + b"\0")
    return digest.hexdigest()


def snapshot(repo, docs_dir, head, target, require_ancestor):
    if "\\" in docs_dir or any(part in ("", ".", "..") for part in docs_dir.split("/")):
        raise ValueError("--docs-dir must be a repository-relative Git directory")
    head = git(repo, "rev-parse", "--verify", "--end-of-options", f"{head}^{{commit}}").decode().strip()
    target = git(repo, "rev-parse", "--verify", "--end-of-options", f"{target}^{{commit}}").decode().strip()
    if require_ancestor:
        try:
            git(repo, "merge-base", "--is-ancestor", target, head)
        except subprocess.CalledProcessError as error:
            if error.returncode == 1:
                raise ValueError("target must be an ancestor of the candidate before verification") from error
            raise
    return {
        "schema": SCHEMA,
        "docs_dir": docs_dir,
        "head": head,
        "head_tree": code_digest(repo, head, docs_dir),
        "target": target,
        "target_tree": code_digest(repo, target, docs_dir),
    }


def matches_hex(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def check_saved(raw, current):
    saved = json.loads(raw)
    if (
        not isinstance(saved, dict)
        or type(saved.get("schema")) is not int
        or saved["schema"] != SCHEMA
        or any(not matches_hex(saved.get(key), COMMIT_ID) for key in ("head", "target"))
        or any(not matches_hex(saved.get(key), DIGEST) for key in ("head_tree", "target_tree"))
    ):
        raise ValueError("missing or invalid verification snapshot")
    for key in ("docs_dir", "head_tree", "target_tree"):
        if saved.get(key) != current[key]:
            raise ValueError(f"{key} changed since verification")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("snapshot", "check"):
        command = commands.add_parser(name)
        command.add_argument("--repo", required=True)
        command.add_argument("--docs-dir", required=True)
        command.add_argument("--head", required=True)
        command.add_argument("--target", required=True)
    commands.choices["check"].add_argument("--snapshot", required=True)
    args = parser.parse_args()

    try:
        current = snapshot(
            args.repo, args.docs_dir.rstrip("/"), args.head, args.target,
            require_ancestor=args.command == "snapshot",
        )
        if args.command == "check":
            check_saved(args.snapshot, current)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"verification snapshot: {error}", file=sys.stderr)
        return 1

    print(json.dumps(current, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
