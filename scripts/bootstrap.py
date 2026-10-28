#!/usr/bin/env python3
"""Fetch exact source commits without replacing local edits or switching branches."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def git(path, *args, capture=False):
    return subprocess.run(["git", "-C", str(path), *args], check=True,
                          text=True, stdout=subprocess.PIPE if capture else None)


def main():
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    for source in lock["repositories"]:
        path = ROOT / ".cache/sources" / source["name"]
        if not path.exists():
            path.mkdir(parents=True)
            git(path, "init", "--quiet")
            git(path, "remote", "add", "origin", source["url"])
        if git(path, "remote", "get-url", "origin", capture=True).stdout.strip() != source["url"]:
            sys.exit(f"Refusing unexpected origin at {path}")
        if git(path, "status", "--porcelain", capture=True).stdout:
            sys.exit(f"Preserve local changes before refreshing {path}")
        current = subprocess.run(["git", "-C", str(path), "rev-parse", "--verify", "HEAD"],
                                 text=True, capture_output=True)
        if current.returncode == 0 and current.stdout.strip() == source["commit"]:
            print(f"Pinned source already present: {source['name']}", flush=True)
            continue
        print(f"Fetching {source['name']} at {source['commit']}", flush=True)
        git(path, "fetch", "--depth=1", "origin", source["commit"])
        git(path, "checkout", "--detach", source["commit"])
        assert git(path, "rev-parse", "HEAD", capture=True).stdout.strip() == source["commit"]


if __name__ == "__main__":
    main()
