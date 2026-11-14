#!/usr/bin/env bash
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Synchronization script for upstream PoB repositories
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
UPSTREAM_DIR="${ROOT_DIR}/upstream"

mkdir -p "${UPSTREAM_DIR}"

sync_repo() {
    local name="$1"
    local url="$2"
    local target="${UPSTREAM_DIR}/${name}"

    if [ -d "${target}/.git" ]; then
        echo "==> Updating ${name}..."
        git -C "${target}" fetch --depth 1 origin
        git -C "${target}" reset --hard origin/HEAD
    else
        echo "==> Cloning ${name}..."
        git clone --depth 1 "${url}" "${target}"
    fi
}

echo "=== Syncing Upstream Repositories ==="
sync_repo "PathOfBuilding-PoE1" "https://github.com/PathOfBuildingCommunity/PathOfBuilding.git"
# Ensure 3.30 tree and GameVersions are present if not yet merged into dev
if [ ! -d "${UPSTREAM_DIR}/PathOfBuilding-PoE1/src/TreeData/3_30" ] || ! grep -q "3_30" "${UPSTREAM_DIR}/PathOfBuilding-PoE1/src/GameVersions.lua"; then
    echo "==> Fetching 3.30 tree from PR #10437..."
    git -C "${UPSTREAM_DIR}/PathOfBuilding-PoE1" fetch origin pull/10437/head:pr-10437 || true
    git -C "${UPSTREAM_DIR}/PathOfBuilding-PoE1" checkout pr-10437 -- src/TreeData/3_30 src/TreeData/3_30_ruthless src/GameVersions.lua src/Classes/PassiveTree.lua src/Data/ModCache.lua src/Modules/ModParser.lua src/Modules/Utils.lua || true
fi
sync_repo "PathOfBuilding-PoE2" "https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2.git"
sync_repo "PathOfBuilding-PoE2-MacOS" "https://github.com/stevep51/PathOfBuilding-PoE2-MacOS.git"
sync_repo "SimpleGraphic" "https://github.com/PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic.git"

echo "=== All upstreams synchronized successfully ==="
