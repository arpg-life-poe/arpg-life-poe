#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Generates Cyrillic font glyphs (.tgf + .tga) for SimpleGraphic Windows runtime.
# ==============================================================================

import os
import sys
import subprocess
import platform

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
FONTGEN_DIR = os.path.join(SCRIPT_DIR, "fontgen")
FONTGEN_BIN = os.path.join(FONTGEN_DIR, "fontgen")
FONTGEN_SRC = os.path.join(FONTGEN_DIR, "fontgen.mm")
DEFAULT_FONTS_DIR = os.path.join(ROOT_DIR, "assets", "fonts")

def build_fontgen_macos():
    if not os.path.exists(FONTGEN_BIN) or os.path.getmtime(FONTGEN_SRC) > os.path.getmtime(FONTGEN_BIN):
        print(f"Compiling fontgen from {FONTGEN_SRC}...")
        cmd = [
            "clang++", "-std=c++17", "-O2",
            FONTGEN_SRC,
            "-framework", "CoreGraphics",
            "-framework", "CoreText",
            "-framework", "Foundation",
            "-o", FONTGEN_BIN
        ]
        subprocess.check_call(cmd)
        print("fontgen compiled successfully!")

def run_fontgen(target_dir):
    if platform.system() == "Darwin":
        build_fontgen_macos()
        cmd = [FONTGEN_BIN, target_dir]
        subprocess.check_call(cmd)
    else:
        print(f"Running fallback Python generator on {platform.system()}...")
        # Fallback to python generator if on Linux/Windows CI
        import generate_cyrillic_fonts_pil
        generate_cyrillic_fonts_pil.process_directory(target_dir)

if __name__ == "__main__":
    fonts_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FONTS_DIR
    print(f"=== Generating Cyrillic Fonts for {fonts_dir} ===")
    run_fontgen(fonts_dir)
    print("=== Finished Generating Cyrillic Fonts ===")
