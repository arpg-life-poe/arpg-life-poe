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
sync_repo "PathOfBuilding-PoE2" "https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2.git"
sync_repo "PathOfBuilding-PoE2-MacOS" "https://github.com/stevep51/PathOfBuilding-PoE2-MacOS.git"
sync_repo "SimpleGraphic" "https://github.com/PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic.git"

echo "=== All upstreams synchronized successfully ==="
