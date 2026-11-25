#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Checks remote upstream repositories for new commits, tags, and manifest versions.
# Synchronously updates upstream-versions.json and i18n/version.lua.
# ==============================================================================

import os
import sys
import re
import json
import urllib.request
import subprocess
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIONS_FILE = os.path.join(ROOT_DIR, "upstream-versions.json")
VERSION_LUA_FILE = os.path.join(ROOT_DIR, "i18n", "version.lua")
UPSTREAM_DIR = os.path.join(ROOT_DIR, "upstream")

REPOS = {
    "poe1": {
        "gh_repo": "PathOfBuildingCommunity/PathOfBuilding",
        "url": "https://github.com/PathOfBuildingCommunity/PathOfBuilding.git",
        "branch": "dev",
        "local_dir": os.path.join(UPSTREAM_DIR, "PathOfBuilding-PoE1")
    },
    "poe2": {
        "gh_repo": "PathOfBuildingCommunity/PathOfBuilding-PoE2",
        "url": "https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2.git",
        "branch": "dev",
        "local_dir": os.path.join(UPSTREAM_DIR, "PathOfBuilding-PoE2")
    },
    "simple_graphic": {
        "gh_repo": "PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic",
        "url": "https://github.com/PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic.git",
        "branch": "master",
        "local_dir": os.path.join(UPSTREAM_DIR, "SimpleGraphic")
    }
}

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "arpg-life-pob-checker"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def fetch_text(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "arpg-life-pob-checker"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None

def get_remote_head(url, branch):
    try:
        out = subprocess.check_output(["git", "ls-remote", url, f"refs/heads/{branch}"], text=True, timeout=15)
        lines = out.strip().splitlines()
        if lines:
            return lines[0].split()[0]
    except Exception:
        pass
    return None

def get_remote_latest_tag(url):
    try:
        out = subprocess.check_output(["git", "ls-remote", "--tags", url], text=True, timeout=15)
        tags = []
        for line in out.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                ref = parts[1]
                if ref.startswith("refs/tags/") and not ref.endswith("^{}"):
                    tag = ref[len("refs/tags/"):]
                    tags.append(tag)
        def parse_ver(t):
            m = re.match(r"^v?(\d+)\.(\d+)(?:\.(\d+))?", t)
            if m:
                return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
            return (0, 0, 0)
        valid = [t for t in tags if re.match(r"^v?\d+\.\d+", t)]
        if valid:
            valid.sort(key=parse_ver)
            return valid[-1]
    except Exception:
        pass
    return None

def extract_manifest_version(text):
    if not text:
        return None
    m = re.search(r'<Version\s+number="([^"]+)"', text)
    if m:
        return m.group(1)
    return None

def get_local_repo_info(local_dir):
    if not os.path.isdir(local_dir):
        return {}
    info = {}
    manifest_path = os.path.join(local_dir, "manifest.xml")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                ver = extract_manifest_version(f.read())
                if ver:
                    info["version"] = ver
        except Exception:
            pass
    if os.path.isdir(os.path.join(local_dir, ".git")):
        try:
            out = subprocess.check_output(
                ["git", "-C", local_dir, "log", "-1", "--format=%H%n%h%n%cI%n%s"],
                text=True, timeout=5
            ).strip().splitlines()
            if len(out) >= 4:
                info["commit"] = out[0]
                info["commit_short"] = out[1]
                info["commit_date"] = out[2]
                info["commit_subject"] = out[3]
        except Exception:
            pass
        try:
            tag = subprocess.check_output(
                ["git", "-C", local_dir, "describe", "--tags", "--abbrev=0"],
                text=True, timeout=5
            ).strip()
            if tag:
                info["latest_release_tag"] = tag
        except Exception:
            pass
    return info

def generate_version_lua(data):
    poe1 = data.get("poe1", {})
    poe2 = data.get("poe2", {})
    ver_p1 = poe1.get("version") or (poe1.get("latest_release_tag", "").lstrip("v")) or "2.68.1"
    ver_p2 = poe2.get("version") or (poe2.get("latest_release_tag", "").lstrip("v")) or "0.23.1"
    commit_p1 = str(poe1.get("commit_short", "5606cc6"))[:7]
    commit_p2 = str(poe2.get("commit_short", "601768b"))[:7]
    tag_p1 = poe1.get("latest_release_tag", f"v{ver_p1}")
    tag_p2 = poe2.get("latest_release_tag", f"v{ver_p2}")
    date_str = (data.get("updated_at") or datetime.now(timezone.utc).isoformat())[:10]

    lua_content = f"""-- ==============================================================================
-- Path of Building — ARPG-Life Edition
-- Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
-- Project: https://arpg-life.ru
--
-- Version and build metadata for auto-updater
-- Auto-generated by scripts/check_upstream.py
-- ==============================================================================

local version = {{
	edition = "ARPG-Life Edition",
	version = "{ver_p1}-arpg1",
	buildDate = "{date_str}",
	upstreamCommitPoE1 = "{commit_p1}",
	upstreamCommitPoE2 = "{commit_p2}",
	upstreamTagPoE1 = "{tag_p1}",
	upstreamTagPoE2 = "{tag_p2}",
	versionPoE1 = "{ver_p1}",
	versionPoE2 = "{ver_p2}",
	checkURL = "https://raw.githubusercontent.com/arpg-life-poe/arpg-life-poe/main/upstream-versions.json",
	releasesURL = "https://github.com/arpg-life-poe/arpg-life-poe/releases",
	siteURL = "https://arpg-life.ru",
	rawDictBaseURL = "https://raw.githubusercontent.com/arpg-life-poe/arpg-life-poe/main/i18n/dictionaries/",
}}

return version
"""
    with open(VERSION_LUA_FILE, "w", encoding="utf-8") as f:
        f.write(lua_content)
    print(f"Generated {VERSION_LUA_FILE} (PoE1: {ver_p1} [{commit_p1}], PoE2: {ver_p2} [{commit_p2}])")

def check_and_update(local_sync_only=False):
    if not os.path.exists(VERSIONS_FILE):
        print(f"Error: {VERSIONS_FILE} not found")
        sys.exit(1)

    with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if local_sync_only:
        print("=== Local sync mode: inspecting local upstream folders ===")
        for key, cfg in REPOS.items():
            local_info = get_local_repo_info(cfg["local_dir"])
            if local_info:
                data.setdefault(key, {}).update(local_info)
                print(f"[{key.upper()}] Local info: {local_info}")
        now_iso = datetime.now(timezone.utc).isoformat()
        data["updated_at"] = now_iso
        with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        generate_version_lua(data)
        return False

    updated = False
    for key, cfg in REPOS.items():
        entry = data.setdefault(key, {})
        entry["repository"] = cfg["url"]
        entry["branch"] = cfg["branch"]

        # 1. Check remote git commit
        remote_commit = get_remote_head(cfg["url"], cfg["branch"])
        curr_commit = entry.get("commit", "")

        # 2. Check GitHub API for commit metadata
        gh_commit = fetch_json(f"https://api.github.com/repos/{cfg['gh_repo']}/commits/{cfg['branch']}")
        if gh_commit and "sha" in gh_commit:
            remote_commit = gh_commit["sha"]
            entry["commit_subject"] = gh_commit.get("commit", {}).get("message", "").splitlines()[0]
            entry["commit_date"] = gh_commit.get("commit", {}).get("committer", {}).get("date", "")

        # 3. Check latest release tag
        remote_tag = get_remote_latest_tag(cfg["url"])
        if remote_tag:
            if entry.get("latest_release_tag") != remote_tag:
                print(f"[!] New tag for {key.upper()}: {entry.get('latest_release_tag')} -> {remote_tag}")
                entry["latest_release_tag"] = remote_tag
                updated = True

        # 4. Check manifest version
        manifest_text = fetch_text(f"https://raw.githubusercontent.com/{cfg['gh_repo']}/{cfg['branch']}/manifest.xml")
        man_ver = extract_manifest_version(manifest_text)
        if not man_ver:
            # Try reading local manifest if available
            local_info = get_local_repo_info(cfg["local_dir"])
            man_ver = local_info.get("version")
        if man_ver:
            if entry.get("version") != man_ver:
                print(f"[!] New manifest version for {key.upper()}: {entry.get('version')} -> {man_ver}")
                entry["version"] = man_ver
                updated = True

        if remote_commit and remote_commit != curr_commit:
            print(f"[!] New upstream commit for {key.upper()}: {curr_commit[:7]} -> {remote_commit[:7]}")
            entry["commit"] = remote_commit
            entry["commit_short"] = remote_commit[:7]
            updated = True
        else:
            print(f"[-] {key.upper()} commit up-to-date ({curr_commit[:7]})")

    # Also inspect local repos to ensure version fields are always present
    for key, cfg in REPOS.items():
        local_info = get_local_repo_info(cfg["local_dir"])
        for k, v in local_info.items():
            if not data[key].get(k):
                data[key][k] = v

    now_iso = datetime.now(timezone.utc).isoformat()
    data["updated_at"] = now_iso
    with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    generate_version_lua(data)

    if updated:
        print("=== upstream-versions.json and i18n/version.lua updated successfully ===")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as gh:
                gh.write("updated=true\n")
        return True
    else:
        print("=== All upstreams are up-to-date ===")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as gh:
                gh.write("updated=false\n")
        return False

if __name__ == "__main__":
    local_sync = "--local-sync" in sys.argv
    check_and_update(local_sync_only=local_sync)
