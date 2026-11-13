#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Packages Windows distribution (.zip) with Cyrillic support and ARPG-Life branding.
# ==============================================================================

import os
import sys
import shutil
import hashlib
import zipfile
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = ROOT_DIR / "upstream"
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
ASSETS_FONTS_DIR = ROOT_DIR / "assets" / "fonts"
I18N_DIR = ROOT_DIR / "i18n"
SCRIPTS_DIR = ROOT_DIR / "scripts"

def calculate_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def ensure_cyrillic_fonts():
    """Ensure assets/fonts contains generated Cyrillic fonts"""
    if not ASSETS_FONTS_DIR.exists() or not any(ASSETS_FONTS_DIR.glob("*.tgf")):
        print("Cyrillic fonts not found in assets/fonts. Generating now...")
        cmd = [sys.executable, str(SCRIPTS_DIR / "generate_cyrillic_fonts.py"), str(ASSETS_FONTS_DIR)]
        subprocess.check_call(cmd)

def build_windows(game_type, custom_dll_path=None):
    assert game_type in ("poe1", "poe2"), f"Invalid game type: {game_type}"
    print(f"\n==========================================")
    print(f" Packaging Windows Release: {game_type.upper()}")
    print(f"==========================================")

    upstream_repo = UPSTREAM_DIR / ("PathOfBuilding-PoE1" if game_type == "poe1" else "PathOfBuilding-PoE2")
    if not upstream_repo.exists():
        print(f"Error: Upstream repository {upstream_repo} does not exist!")
        return False

    ensure_cyrillic_fonts()

    work_dir = BUILD_DIR / f"windows-{game_type}"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy src/
    print("Copying src/...")
    shutil.copytree(upstream_repo / "src", work_dir / "src")

    # 2. Copy runtime/
    print("Copying runtime/...")
    shutil.copytree(upstream_repo / "runtime", work_dir / "runtime")

    # Clean up any git or test clutter in runtime
    for junk in (work_dir / "runtime").glob("**/.git*"):
        if junk.is_file(): junk.unlink()
        elif junk.is_dir(): shutil.rmtree(junk)

    # 3. Locate & copy Path of Building.exe to root
    runtime_exe = None
    for candidate in (work_dir / "runtime").glob("*Path*exe"):
        runtime_exe = candidate
        break

    if runtime_exe and runtime_exe.exists():
        target_exe_name = "Path of Building.exe" if game_type == "poe1" else "Path of Building (PoE 2).exe"
        print(f"Copying main executable {runtime_exe.name} -> {target_exe_name}...")
        shutil.copy2(runtime_exe, work_dir / target_exe_name)
    else:
        print("Warning: Path of Building executable not found in runtime!")

    # 4. Replace SimpleGraphic.dll with patched build
    target_dll = work_dir / "runtime" / "SimpleGraphic.dll"
    if custom_dll_path and os.path.exists(custom_dll_path):
        print(f"Installing custom patched SimpleGraphic.dll from {custom_dll_path}...")
        shutil.copy2(custom_dll_path, target_dll)
    else:
        candidate_dll = UPSTREAM_DIR / "SimpleGraphic" / "build" / "Release" / "SimpleGraphic.dll"
        if candidate_dll.exists():
            print(f"Installing compiled SimpleGraphic.dll from {candidate_dll}...")
            shutil.copy2(candidate_dll, target_dll)
        else:
            print("Note: Custom SimpleGraphic.dll not supplied; using upstream runtime DLL with font patch.")

    # 5. Install Cyrillic Fonts into runtime/SimpleGraphic/Fonts/
    runtime_fonts_dir = work_dir / "runtime" / "SimpleGraphic" / "Fonts"
    runtime_fonts_dir.mkdir(parents=True, exist_ok=True)
    print("Installing Cyrillic font atlases (.tgf + .tga)...")
    for font_file in ASSETS_FONTS_DIR.glob("*.*"):
        if font_file.suffix.lower() in (".tgf", ".tga"):
            shutil.copy2(font_file, runtime_fonts_dir / font_file.name)

    # 6. Copy manifest if exists
    manifest_xml = upstream_repo / "manifest.xml"
    if manifest_xml.exists():
        shutil.copy2(manifest_xml, work_dir / "manifest.xml")

    # 7. Copy i18n modules & dictionaries
    print("Integrating i18n modules and dictionaries...")
    target_i18n = work_dir / "src" / "i18n"
    if target_i18n.exists():
        shutil.rmtree(target_i18n)
    target_i18n.mkdir(parents=True, exist_ok=True)

    # Copy modules and version.lua
    modules_dir = I18N_DIR / "modules"
    if modules_dir.exists():
        for mod in modules_dir.glob("*.lua"):
            shutil.copy2(mod, target_i18n / mod.name)
    version_lua = I18N_DIR / "version.lua"
    if version_lua.exists():
        shutil.copy2(version_lua, target_i18n / "version.lua")

    # Copy dictionaries
    dicts_dir = I18N_DIR / "dictionaries"
    if dicts_dir.exists():
        target_dicts = target_i18n / "dictionaries"
        target_dicts.mkdir(parents=True, exist_ok=True)
        for d in dicts_dir.glob("*.lua"):
            shutil.copy2(d, target_dicts / d.name)

    # 8. Apply patch_sources.py to src/
    print("Applying ARPG-Life patches to Lua sources...")
    patcher_script = SCRIPTS_DIR / "patch_sources.py"
    cmd = [sys.executable, str(patcher_script), str(work_dir / "src"), game_type]
    subprocess.check_call(cmd)

    # 9. Create Zip Archive in dist/
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    game_label = "PoE1" if game_type == "poe1" else "PoE2"
    zip_name = f"PathOfBuilding-{game_label}-Windows-x64.zip"
    zip_path = DIST_DIR / zip_name
    print(f"Creating zip archive {zip_path}...")
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                p = Path(root) / file
                arcname = p.relative_to(work_dir)
                zipf.write(p, arcname)

    sha = calculate_sha256(zip_path)
    sha_file = DIST_DIR / f"{zip_name}.sha256"
    with open(sha_file, "w") as f:
        f.write(f"{sha}  {zip_name}\n")

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Successfully packaged {zip_name} ({size_mb:.2f} MB)")
    print(f"SHA-256: {sha}")
    return True

if __name__ == "__main__":
    game_arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    dll_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if game_arg == "all":
        build_windows("poe1", dll_arg)
        build_windows("poe2", dll_arg)
    else:
        build_windows(game_arg, dll_arg)
