#!/usr/bin/env python3
"""
Fetch detailed RU/EN item and gem cards from PoEDB for PoE 3.30 WordPress import.

Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
"""

import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_330 = PROJECT_ROOT / "i18n" / "sources_330" / "poedb_330_ru_en.json"
OUT_FILE = PROJECT_ROOT / "i18n" / "sources_330" / "poedb_330_wp_import.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru,en;q=0.9",
}

NEW_UNIQUES = [
    "Corpse_Rose",
    "The_Covetous_Dark",
    "Bane_of_the_Apostate",
    "The_Sword_of_Ages",
    "Ordered_Fate",
    "Veil_of_Flesh",
    "Hide_of_the_Vendigo",
    "Mantle_of_Dreams",
    "Unwilling_Embrace",
    "Dreadmaidens_Sacrament",
    "Putrid_Seed",
]

CHANGED_UNIQUES = [
    "Atziris_Acuity",
    "Doedres_Tongue",
    "Doryanis_Invitation",
    "Femurs_of_the_Saints",
    "The_Hallowed_Monarch",
    "The_Living_Blade",
    "Malachais_Loop",
    "Ralakeshs_Impatience",
    "Rotmothers_Mutiny",
    "Shadowstitch",
    "Shavronnes_Wrappings",
    "Steelworm",
]

NEW_GEMS = [
    "Arcane_Link",
    "Fireball_of_Radiation",
]

CHANGED_GEMS = [
    "Flame_Link",
    "Pact_of_Beidat",
    "Summon_Flame_Golem",
    "Summon_Lightning_Golem",
    "Summon_Stone_Golem",
    "Winter_Orb",
    "Transfusion_Support",
    "Vaal_Sacrifice_Support",
    "Dark_Bargain",
]

THREADS = [
    "Frayed_Thread",
    "Abyss_Thread",
    "Bestiary_Thread",
    "Betrayal_Thread",
    "Blight_Thread",
    "Breach_Thread",
    "Expedition_Thread",
    "Incursion_Thread",
    "Legion_Thread",
    "Ritual_Thread",
    "Ultimatum_Thread",
]

BASES = [
    "Mycelium_Core",
]


def fetch_html(lang: str, slug: str) -> str:
    url = f"https://poedb.tw/{lang}/{slug}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean_html(raw: str) -> str:
    text = re.sub(r'<span[^>]*class=["\']ndash["\'][^>]*>.*?</span>', "—", raw, flags=re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\[[^\]|]+\|([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_popup_block(page_html: str) -> str:
    for marker in ('class="itemPopupContainer', 'class="newItemPopup', 'class="itemBoxContent'):
        idx = page_html.find(marker)
        if idx != -1:
            return page_html[idx:idx + 15000]
    return page_html[:40000]


def extract_div_list(block: str, cls_name: str) -> List[str]:
    out: List[str] = []
    for m in re.finditer(rf'<div[^>]*class=["\'][^"\']*\b{cls_name}\b[^"\']*["\'][^>]*>(.*?)</div>', block, flags=re.S):
        txt = clean_html(m.group(1))
        for line in txt.splitlines():
            if line and line not in out:
                out.append(line)
    return out


def parse_detail(slug: str, kind: str) -> Dict:
    html_ru = fetch_html("ru", slug)
    html_us = fetch_html("us", slug)

    block_ru = extract_popup_block(html_ru)
    block_us = extract_popup_block(html_us)

    # Name
    h1_ru = re.search(r"<h1[^>]*>(.*?)</h1>", html_ru, flags=re.S)
    h1_us = re.search(r"<h1[^>]*>(.*?)</h1>", html_us, flags=re.S)
    name_ru = clean_html(h1_ru.group(1)) if h1_ru else slug.replace("_", " ")
    name_en = clean_html(h1_us.group(1)) if h1_us else slug.replace("_", " ")

    # Unique header / base type inside popup
    item_name_m = re.search(r'class=["\']itemName[^"\']*["\'][^>]*>(.*?)</div>', block_ru, flags=re.S)
    if item_name_m:
        lines = clean_html(item_name_m.group(1)).splitlines()
        if lines:
            name_ru = lines[0]
            type_line_ru = lines[1] if len(lines) > 1 else ""
        else:
            type_line_ru = ""
    else:
        type_line_ru = ""

    item_name_us_m = re.search(r'class=["\']itemName[^"\']*["\'][^>]*>(.*?)</div>', block_us, flags=re.S)
    if item_name_us_m:
        lines_us = clean_html(item_name_us_m.group(1)).splitlines()
        if lines_us:
            name_en = lines_us[0]

    # Icon (prefer Art/2DItems/, exclude minimap/nav icons)
    icon_m = re.search(r'<img[^>]+src=["\'](https://cdn\.poedb\.tw/image/Art/2DItems/[^"\']+)["\']', html_ru)
    icon_url = icon_m.group(1) if icon_m else ""

    implicits = extract_div_list(block_ru, "implicitMod")
    explicits = [
        line for line in extract_div_list(block_ru, "explicitMod")
        if re.search(r"[а-яА-ЯёЁ]", line)
    ]
    reqs = extract_div_list(block_ru, "requirements")
    props = extract_div_list(block_ru, "property")
    sec_descr = extract_div_list(block_ru, "secDescrText")
    flavour = extract_div_list(block_ru, "flavourText")

    return {
        "slug": slug,
        "kind": kind,
        "name_en": name_en,
        "name_ru": name_ru,
        "type_line_ru": type_line_ru,
        "implicits_ru": implicits,
        "explicits_ru": explicits,
        "requirements_ru": "\n".join(reqs),
        "properties_ru": props,
        "description_ru": sec_descr[0] if sec_descr else "",
        "flavour_ru": "\n".join(flavour),
        "icon_url": icon_url,
    }


def main() -> int:
    tasks = (
        [(s, "new_unique") for s in NEW_UNIQUES]
        + [(s, "changed_unique") for s in CHANGED_UNIQUES]
        + [(s, "new_gem") for s in NEW_GEMS]
        + [(s, "changed_gem") for s in CHANGED_GEMS]
        + [(s, "thread") for s in THREADS]
        + [(s, "base") for s in BASES]
    )

    src = json.loads(SRC_330.read_text(encoding="utf-8")) if SRC_330.exists() else {}
    src_uniques = src.get("uniques") or {}
    src_gems = src.get("gems") or {}
    src_items = src.get("items_330") or {}

    items = []
    for slug, kind in tasks:
        print(f"Fetching [{kind}] {slug}...", flush=True)
        try:
            entry = parse_detail(slug, kind)
            ref = src_uniques.get(slug) or src_gems.get(slug) or src_items.get(slug) or {}
            if not entry["type_line_ru"] and ref.get("base_ru"):
                entry["type_line_ru"] = ref["base_ru"]
            if not entry["icon_url"] and ref.get("icon"):
                entry["icon_url"] = ref["icon"]
            items.append(entry)
        except Exception as exc:
            print(f"  WARN: {slug}: {exc}", file=sys.stderr)

    # Also include Viscera from poedb_330_ru_en.json
    viscera_items = []
    for slug, v in src_items.items():
        if "/Viscera/" in (v.get("icon") or ""):
            viscera_items.append({
                "slug": slug,
                "kind": "viscera",
                "name_en": v.get("name_en", ""),
                "name_ru": v.get("name_ru", ""),
                "explicits_ru": v.get("mods_ru") or [],
                "icon_url": v.get("icon", ""),
            })

    payload = {
        "patch": "3.30.0",
        "items": items,
        "viscera": viscera_items,
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {OUT_FILE}: items={len(items)}, viscera={len(viscera_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
