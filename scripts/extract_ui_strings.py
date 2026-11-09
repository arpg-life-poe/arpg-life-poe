#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# UI Strings Extractor and Coverage Verifier for PoB 1 & PoB 2 Lua source files
# ==============================================================================

import os
import re
import sys
import json
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POE1_SRC = os.path.join(BASE_DIR, "upstream", "PathOfBuilding-PoE1", "src")
POE2_SRC = os.path.join(BASE_DIR, "upstream", "PathOfBuilding-PoE2", "src")
UI_RU_LUA = os.path.join(BASE_DIR, "i18n", "dictionaries", "ui_ru.lua")

# Target UI & Calculation files in PoE1 and PoE2 upstream
TARGET_FILES = [
    # Modules
    ("Modules", "Main.lua"),
    ("Modules", "Build.lua"),
    ("Modules", "BuildDisplayStats.lua"),
    ("Modules", "CalcDisplay.lua"),
    ("Modules", "CalcSections.lua"),
    ("Modules", "ConfigOptions.lua"),
    ("Modules", "Common.lua"),
    # Classes (Tabs)
    ("Classes", "TreeTab.lua"),
    ("Classes", "SkillsTab.lua"),
    ("Classes", "ItemsTab.lua"),
    ("Classes", "CalcsTab.lua"),
    ("Classes", "ConfigTab.lua"),
    ("Classes", "ImportTab.lua"),
    ("Classes", "NotesTab.lua"),
    ("Classes", "PartyTab.lua"),
    ("Classes", "CompareTab.lua"),
    # Classes (Controls, Viewers, Popups)
    ("Classes", "PassiveTreeView.lua"),
    ("Classes", "ItemSlotControl.lua"),
    ("Classes", "GemSelectControl.lua"),
    ("Classes", "OptionsPopup.lua"),
    ("Classes", "PopupDialog.lua"),
    ("Classes", "ManageTreePopup.lua"),
    ("Classes", "CalcSectionControl.lua"),
    ("Classes", "CalcBreakdownControl.lua"),
    ("Classes", "ItemDBControl.lua"),
    ("Classes", "ItemListControl.lua"),
    ("Classes", "SkillListControl.lua"),
    ("Classes", "TradeQuery.lua"),
]

COLOR_CODE_RE = re.compile(r'\^[0-9]|\^x[0-9a-fA-F]{6}')

def clean_ui_string(s):
    if not s or not isinstance(s, str):
        return None
    # Strip PoB color codes
    cleaned = COLOR_CODE_RE.sub('', s).strip()
    # Strip trailing colons
    cleaned = re.sub(r':\s*$', '', cleaned).strip()
    # Basic sanity filters
    if not cleaned or len(cleaned) < 2:
        return None
    # Skip formatting tags or template placeholders
    if re.match(r'^[%\d\.\+\-\s\{\}:_A-Za-z0-9#\/\*\(\)]+$', cleaned):
        words = re.findall(r'[a-zA-Z]{2,}', cleaned)
        if not words:
            return None
        non_format = [w for w in words if w.lower() not in ('nil', 'true', 'false', 'and', 'or', 'not', 'fs', 'mod', 'output', 'var', 'stat')]
        if not non_format:
            return None
    # Ignore filenames, paths, URLs, code identifiers
    if cleaned.endswith('.lua') or cleaned.endswith('.png') or cleaned.startswith('http') or cleaned.startswith('/'):
        return None
    if re.match(r'^[A-Z0-9_]{3,}$', cleaned):
        return None
    if re.match(r'^[a-z]+[A-Z0-9][a-zA-Z0-9]*$', cleaned):
        return None
    return cleaned

def extract_from_file(file_path):
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    results = []

    # 1. label = "..." or label = '...'
    for m in re.finditer(r'\blabel\s*=\s*(["\'])(.*?)\1', content):
        val = clean_ui_string(m.group(2))
        if val:
            results.append((val, "label", m.start()))

    # 2. section = "..." or section = '...'
    for m in re.finditer(r'\bsection\s*=\s*(["\'])(.*?)\1', content):
        val = clean_ui_string(m.group(2))
        if val:
            results.append((val, "section", m.start()))

    # 3. format = "..." where format looks like text (e.g. "Physical:")
    for m in re.finditer(r'\bformat\s*=\s*(["\'])(.*?)\1', content):
        raw = m.group(2)
        if "{" not in raw:
            val = clean_ui_string(raw)
            if val:
                results.append((val, "format", m.start()))

    # 4. Control constructors: new("...Control"):...Control(..., "...", ...)
    for m in re.finditer(r'new\("(?:Button|CheckBox|Label)Control"\):[A-Za-z0-9]+\([^,]+,[^,]+,\s*(["\'])(.*?)\1', content):
        val = clean_ui_string(m.group(2))
        if val:
            results.append((val, "control_label", m.start()))

    # 5. DropDown items: { label = "...", ... }
    for m in re.finditer(r'\{\s*label\s*=\s*(["\'])(.*?)\1', content):
        val = clean_ui_string(m.group(2))
        if val:
            results.append((val, "dropdown_label", m.start()))

    # 6. Tooltip AddLine: tooltip:AddLine(..., "...")
    for m in re.finditer(r'(?:tooltip|miscTooltip):AddLine\(\s*\d+\s*,\s*(["\'])(.*?)\1', content):
        val = clean_ui_string(m.group(2))
        if val:
            results.append((val, "tooltip_line", m.start()))

    # 7. OpenPopup: main:OpenPopup(..., "Title", ...)
    for m in re.finditer(r'OpenPopup\([^,]+,[^,]+,\s*(["\'])(.*?)\1', content):
        val = clean_ui_string(m.group(2))
        if val:
            results.append((val, "popup_title", m.start()))

    # 8. DrawString: DrawString(..., "Text")
    for m in re.finditer(r'DrawString\([^,]+,[^,]+,[^,]+,[^,]+,[^,]+,\s*(["\'])(.*?)\1', content):
        val = clean_ui_string(m.group(2))
        if val:
            results.append((val, "draw_string", m.start()))

    # 9. AddStatComparesToTooltip header lines
    for m in re.finditer(r'AddStatComparesToTooltip\([^,]+,[^,]+,[^,]+,\s*(["\'])(.*?)\1', content):
        val = clean_ui_string(m.group(2))
        if val:
            results.append((val, "stat_compare_header", m.start()))

    # 10. Known UI keyword strings
    for m in re.finditer(r'(["\'])([\^xA-Za-z0-9\s:%\+\-\.\?!,\'\(\)\/]{3,80})\1', content):
        raw = m.group(2)
        if any(term in raw for term in [
            "will give you", "Socket", "Level", "Quality", "DPS", "Damage", "Crit", "Resistance",
            "Mana", "Life", "Energy Shield", "Armour", "Evasion", "Chance", "Requires", "Warning"
        ]):
            val = clean_ui_string(raw)
            if val:
                results.append((val, "ui_keyword", m.start()))

    return results

def load_ui_ru_dict():
    if not os.path.exists(UI_RU_LUA):
        return set()
    with open(UI_RU_LUA, "r", encoding="utf-8") as f:
        content = f.read()
    # Extract keys inside ui_ru = { ["key"] = "val" }
    keys = set()
    for m in re.finditer(r'\["(.*?)"\]\s*=', content):
        key = m.group(1).encode().decode('unicode_escape')
        keys.add(key)
    return keys

def main():
    extracted = defaultdict(set)
    file_count = 0

    for base_src, label in [(POE1_SRC, "PoE1"), (POE2_SRC, "PoE2")]:
        for folder, fname in TARGET_FILES:
            fpath = os.path.join(base_src, folder, fname)
            if os.path.exists(fpath):
                file_count += 1
                items = extract_from_file(fpath)
                for val, kind, pos in items:
                    extracted[val].add(f"{label}:{folder}/{fname}:{kind}")

    print(f"Scanned files in PoE1 and PoE2: scanned {file_count} files.")
    print(f"Total unique UI string candidates: {len(extracted)}")

    # Save to JSON
    out_dict = {k: sorted(list(v)) for k, v in sorted(extracted.items())}
    out_json = os.path.join(BASE_DIR, "i18n", "extracted_ui_strings.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out_dict, f, ensure_ascii=False, indent=2)
    print(f"Saved extracted strings to: {out_json}")

    # Check coverage against ui_ru.lua
    translated_keys = load_ui_ru_dict()
    print(f"\nLoaded {len(translated_keys)} translated terms from {UI_RU_LUA}")

    matched = 0
    unmatched = []
    for s in extracted.keys():
        if s in translated_keys or (s + ":") in translated_keys or s.rstrip(":") in translated_keys:
            matched += 1
        else:
            unmatched.append(s)

    coverage = (matched / len(extracted)) * 100 if extracted else 0
    print(f"Direct UI match count: {matched} / {len(extracted)} ({coverage:.1f}% coverage)")
    print(f"Note: Unmatched strings can also be resolved dynamically at runtime by i18n.lua patterns,")
    print(f"Key:Value splitting, Text (Subtext) decomposition, and affix numerical templates.")

if __name__ == "__main__":
    main()
