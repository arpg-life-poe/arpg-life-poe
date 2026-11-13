#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Checks remote upstream repositories for new commits and updates upstream-versions.json
# ==============================================================================

import os
import sys
import json
import subprocess
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIONS_FILE = os.path.join(ROOT_DIR, "upstream-versions.json")

REPOS = {
    "poe1": {
        "url": "https://github.com/PathOfBuildingCommunity/PathOfBuilding.git",
        "branch": "dev"
    },
    "poe2": {
        "url": "https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2.git",
        "branch": "dev"
    },
    "simple_graphic": {
        "url": "https://github.com/PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic.git",
        "branch": "master"
    }
}

def get_remote_head(url, branch):
    try:
        out = subprocess.check_output(["git", "ls-remote", url, f"refs/heads/{branch}"], text=True, timeout=30)
        lines = out.strip().splitlines()
        if lines:
            commit = lines[0].split()[0]
            return commit
    except Exception as e:
        print(f"Error fetching remote head for {url}: {e}")
    return None

def check_and_update():
    if not os.path.exists(VERSIONS_FILE):
        print(f"Error: {VERSIONS_FILE} not found")
        sys.exit(1)

    with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = False
    for key, cfg in REPOS.items():
        remote_commit = get_remote_head(cfg["url"], cfg["branch"])
        if not remote_commit:
            continue

        curr_commit = data.get(key, {}).get("commit", "")
        if remote_commit != curr_commit:
            print(f"[!] New upstream commit for {key.upper()}: {curr_commit[:7]} -> {remote_commit[:7]}")
            data[key]["commit"] = remote_commit
            data[key]["commit_short"] = remote_commit[:7]
            updated = True
        else:
            print(f"[-] {key.upper()} is up-to-date ({curr_commit[:7]})")

    if updated:
        now_iso = datetime.now(timezone.utc).isoformat()
        data["updated_at"] = now_iso
        with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print("=== upstream-versions.json updated successfully ===")
        # Output for GitHub Actions
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as gh:
                gh.write("updated=true\n")
        sys.exit(0)
    else:
        print("=== All upstreams are up-to-date ===")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as gh:
                gh.write("updated=false\n")
        sys.exit(0)

if __name__ == "__main__":
    check_and_update()
