#!/usr/bin/env bash
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Native macOS build & packaging script (Apple Silicon arm64)
# Supports both Path of Exile 1 and Path of Exile 2
# ==============================================================================

set -euo pipefail

TARGET="${1:-poe2}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
UPSTREAM_DIR="${ROOT_DIR}/upstream"
BUILD_ROOT="${ROOT_DIR}/build"
DIST_ROOT="${ROOT_DIR}/dist"
HOST_SRC="${ROOT_DIR}/macos-host"

export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

# Check required build tools
for tool in cmake ninja pkg-config python3; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "Error: Required tool '${tool}' not found in PATH." >&2
    exit 1
  fi
done

# Check required libraries via pkg-config
for pkg in sdl3 luajit libzstd; do
  if ! pkg-config --exists "${pkg}"; then
    echo "Error: Required pkg-config package '${pkg}' not found." >&2
    exit 1
  fi
done

# Ensure dictionaries are generated and up to date
echo "==> Updating translation dictionaries..."
python3 "${ROOT_DIR}/scripts/build_dictionaries.py"

build_target() {
  local GAME="$1"
  local APP_NAME=""
  local BUNDLE_ID=""
  local SRC_REPO=""

  if [ "${GAME}" = "poe1" ]; then
    APP_NAME="Path of Building (PoE 1)"
    BUNDLE_ID="ru.arpg-life.poe1.pob"
    SRC_REPO="${UPSTREAM_DIR}/PathOfBuilding-PoE1"
  elif [ "${GAME}" = "poe2" ]; then
    APP_NAME="Path of Building (PoE 2)"
    BUNDLE_ID="ru.arpg-life.poe2.pob"
    SRC_REPO="${UPSTREAM_DIR}/PathOfBuilding-PoE2"
  else
    echo "Unknown target: ${GAME}. Choose 'poe1' or 'poe2'." >&2
    exit 1
  fi

  echo "=========================================================="
  echo "Building: ${APP_NAME} (${GAME})"
  echo "=========================================================="

  local BUILD_DIR="${BUILD_ROOT}/${GAME}-macos-arm64"
  local DIST_DIR="${DIST_ROOT}/${GAME}-macos-arm64"

  mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

  # Configure & compile native host with UTF-8/CoreText support
  echo "==> Compiling native host..."
  cmake -S "${HOST_SRC}" -B "${BUILD_DIR}" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_OSX_ARCHITECTURES="arm64"

  cmake --build "${BUILD_DIR}"

  local COMPILED_APP="${BUILD_DIR}/PathOfBuilding-PoE2.app"
  local FINAL_APP="${DIST_DIR}/${APP_NAME}.app"

  rm -rf "${FINAL_APP}"
  cp -R "${COMPILED_APP}" "${FINAL_APP}"

  local BIN_DIR="${FINAL_APP}/Contents/MacOS"
  local FRAMEWORKS="${FINAL_APP}/Contents/Frameworks"
  local RESOURCES="${FINAL_APP}/Contents/Resources"
  mkdir -p "${FRAMEWORKS}" "${RESOURCES}"

  # Bundle dynamic libraries (SDL3, LuaJIT, libzstd)
  echo "==> Bundling dynamic libraries into Frameworks..."
  local BINARY="${BIN_DIR}/PathOfBuilding-PoE2"

  local HOMEBREW_PREFIX
  HOMEBREW_PREFIX="$(brew --prefix)"

  bundle_dep() {
    local dylib_path="$1"
    local name
    name="$(basename "${dylib_path}")"
    if [ ! -f "${FRAMEWORKS}/${name}" ]; then
      cp "${dylib_path}" "${FRAMEWORKS}/${name}"
      chmod u+w "${FRAMEWORKS}/${name}"
      install_name_tool -id "@rpath/${name}" "${FRAMEWORKS}/${name}"
    fi
    install_name_tool -change "${dylib_path}" "@rpath/${name}" "${BINARY}"
  }

  bundle_dep "${HOMEBREW_PREFIX}/opt/sdl3/lib/libSDL3.0.dylib"
  bundle_dep "${HOMEBREW_PREFIX}/opt/luajit/lib/libluajit-5.1.2.dylib"
  bundle_dep "${HOMEBREW_PREFIX}/opt/zstd/lib/libzstd.1.dylib"

  for fw in "${FRAMEWORKS}"/*.dylib; do
    install_name_tool -change "${HOMEBREW_PREFIX}/opt/sdl3/lib/libSDL3.0.dylib" "@rpath/libSDL3.0.dylib" "${fw}" 2>/dev/null || true
    install_name_tool -change "${HOMEBREW_PREFIX}/opt/luajit/lib/libluajit-5.1.2.dylib" "@rpath/libluajit-5.1.2.dylib" "${fw}" 2>/dev/null || true
    install_name_tool -change "${HOMEBREW_PREFIX}/opt/zstd/lib/libzstd.1.dylib" "@rpath/libzstd.1.dylib" "${fw}" 2>/dev/null || true
  done

  # Add rpath to binary
  install_name_tool -add_rpath "@executable_path/../Frameworks" "${BINARY}" 2>/dev/null || true

  # Copy Lua source code and runtime assets
  echo "==> Populating app Resources..."
  rsync -a --delete \
    --exclude 'Export' \
    --exclude 'Builds' \
    --exclude 'Settings.xml' \
    --exclude 'HeadlessWrapper.lua' \
    --exclude 'LaunchInstall.lua' \
    "${SRC_REPO}/src" "${RESOURCES}/"

  # Copy font atlases
  mkdir -p "${RESOURCES}/runtime/SimpleGraphic/Fonts"
  rsync -a "${UPSTREAM_DIR}/PathOfBuilding-PoE2-MacOS/runtime/SimpleGraphic/Fonts/" "${RESOURCES}/runtime/SimpleGraphic/Fonts/"

  # Copy runtime/lua libraries
  if [ -d "${SRC_REPO}/runtime/lua" ]; then
    mkdir -p "${RESOURCES}/runtime/lua"
    rsync -a "${SRC_REPO}/runtime/lua/" "${RESOURCES}/runtime/lua/"
  fi

  # Copy i18n modules and dictionaries
  echo "==> Copying i18n modules and dictionaries..."
  mkdir -p "${RESOURCES}/i18n"
  rsync -a "${ROOT_DIR}/i18n/" "${RESOURCES}/i18n/"

  # Apply source patches: branding, i18n hooks, language switcher
  echo "==> Patching sources for ARPG-Life branding and i18n..."
  python3 "${ROOT_DIR}/scripts/patch_sources.py" "${RESOURCES}/src" "${GAME}"

  # Copy manifest and docs
  if [ -f "${SRC_REPO}/manifest.xml" ]; then
    # Modify manifest so it has platform="macos-arm64"
    python3 - "${SRC_REPO}/manifest.xml" "${RESOURCES}/manifest.xml" <<'PY'
import re, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, "r", encoding="utf-8").read()
def add_platform(match):
    tag = match.group(0)
    if "platform=" in tag:
        return tag
    return tag[:-2] + ' platform="macos-arm64" />'
text = re.sub(r'<Version\b[^>]*/>', add_platform, text, count=1)
open(dst, "w", encoding="utf-8").write(text)
PY
  fi

  if [ -f "${SRC_REPO}/changelog.txt" ]; then
    cp "${SRC_REPO}/changelog.txt" "${RESOURCES}/changelog.txt"
  fi
  if [ -f "${SRC_REPO}/help.txt" ]; then
    cp "${SRC_REPO}/help.txt" "${RESOURCES}/help.txt"
  fi

  # Customize Info.plist
  local PLIST="${FINAL_APP}/Contents/Info.plist"
  if [ -f "${PLIST}" ]; then
    plutil -replace CFBundleName -string "${APP_NAME}" "${PLIST}" 2>/dev/null || true
    plutil -replace CFBundleDisplayName -string "${APP_NAME}" "${PLIST}" 2>/dev/null || true
    plutil -replace CFBundleIdentifier -string "${BUNDLE_ID}" "${PLIST}" 2>/dev/null || true
  fi

  # Ad-hoc codesign
  echo "==> Codesigning bundle..."
  codesign --force --deep -s - "${FINAL_APP}"
  codesign --verify --deep --strict "${FINAL_APP}"

  # Copy macOS First-Launch Helper scripts into package directory
  echo "==> Adding first-launch helper and instruction..."
  cp "${ROOT_DIR}/scripts/macos-helper/Запустить первый раз (снять блокировку macOS).command" "${DIST_DIR}/"
  cp "${ROOT_DIR}/scripts/macos-helper/ИНСТРУКЦИЯ.txt" "${DIST_DIR}/"
  chmod +x "${DIST_DIR}/Запустить первый раз (снять блокировку macOS).command"

  # Package into ZIP and create SHA-256
  local GAME_NAME="PoE1"
  if [ "${GAME}" = "poe2" ]; then
    GAME_NAME="PoE2"
  fi
  local ZIP_NAME="PathOfBuilding-${GAME_NAME}-macOS-arm64.zip"
  echo "==> Creating clean distribution archive: ${ZIP_NAME}..."
  rm -f "${DIST_DIR}"/*.zip*
  rm -f "${DIST_ROOT}/${ZIP_NAME}" "${DIST_ROOT}/${ZIP_NAME}.sha256"
  (cd "${DIST_DIR}" && COPYFILE_DISABLE=1 ditto --noextattr --norsrc -c -k . "${DIST_ROOT}/${ZIP_NAME}")
  (cd "${DIST_ROOT}" && shasum -a 256 "${ZIP_NAME}" > "${ZIP_NAME}.sha256")

  echo "==> Successfully built and packaged ${APP_NAME}!"
  echo "    Path: ${FINAL_APP}"
  echo "    Archive: ${DIST_DIR}/${ZIP_NAME}"
}

if [ "${TARGET}" = "all" ]; then
  build_target "poe1"
  build_target "poe2"
else
  build_target "${TARGET}"
fi
