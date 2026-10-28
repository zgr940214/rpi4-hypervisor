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
        # Explicit, reviewed mirrors carry the same pinned Git objects. Keep
        # the canonical origin as provenance and never change a local origin.
        urls = list(dict.fromkeys(source.get("mirrors", []) + [source["url"]]))
        path = ROOT / ".cache/sources" / source["name"]
        if not path.exists():
            path.mkdir(parents=True)
            git(path, "init", "--quiet")
            git(path, "remote", "add", "origin", source["url"])
        if git(path, "remote", "get-url", "origin", capture=True).stdout.strip() not in urls:
            sys.exit(f"Refusing unexpected origin at {path}")
        if git(path, "status", "--porcelain", capture=True).stdout:
            sys.exit(f"Preserve local changes before refreshing {path}")
        current = subprocess.run(["git", "-C", str(path), "rev-parse", "--verify", "HEAD"],
                                 text=True, capture_output=True)
        if current.returncode == 0 and current.stdout.strip() == source["commit"]:
            print(f"Pinned source already present: {source['name']}", flush=True)
            continue
        print(f"Fetching {source['name']} at {source['commit']}", flush=True)
        for url in urls:
            print(f"Source endpoint: {url}", flush=True)
            try:
                git(path, "fetch", "--depth=1", url, source["commit"])
                break
            except subprocess.CalledProcessError:
                print(f"Pinned fetch failed at {url}", file=sys.stderr, flush=True)
        else:
            sys.exit(f"Cannot fetch pinned commit for {source['name']} from configured sources")
        git(path, "checkout", "--detach", source["commit"])
        assert git(path, "rev-parse", "HEAD", capture=True).stdout.strip() == source["commit"]
        git(path, "fsck", "--strict", "--no-reflogs", "--no-dangling")


if __name__ == "__main__":
    main()
