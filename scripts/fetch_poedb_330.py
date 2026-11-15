#!/usr/bin/env python3
"""
Fetch and pair Path of Exile 3.30 (Covens of Umbra) EN/RU data from PoEDB.

Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
"""

import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUT_DIR = PROJECT_ROOT / "i18n" / "sources_330"
OUT_FILE = OUT_DIR / "poedb_330_ru_en.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru,en;q=0.9",
}

PAGES = [
    ("gems", "Gem"),
    ("covens_gems", "Covens_gems"),
    ("uniques", "Unique_item"),
    ("covens_uniques", "Covens_uniques"),
    ("viscera", "Viscera"),
    ("threads", "Threads"),
    ("covens_items", "Covens_items"),
]


def fetch_html(lang: str, page: str) -> str:
    url = f"https://poedb.tw/{lang}/{page}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean_html_text(raw: str) -> str:
    text = re.sub(r'<span[^>]*class=["\']ndash["\'][^>]*>.*?</span>', "-", raw, flags=re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_slug(href: str) -> Optional[str]:
    if not href or href.startswith("http") or href.startswith("#") or href.startswith("?"):
        return None
    slug = re.sub(r"^/(?:ru|us)/", "", href).strip("/")
    if not slug or "/" in slug:
        return None
    return slug


def split_cards(page_html: str) -> List[str]:
    # Split by PoEDB card container
    parts = re.split(r'<div\s+class="d-flex\s+border-top\s+rounded">', page_html)
    return parts[1:] if len(parts) > 1 else []


def parse_card(card_html: str, lang: str) -> Optional[Dict]:
    # Truncate at next major section if any
    end_idx = card_html.find('class="col">')
    if end_idx != -1:
        card_html = card_html[:end_idx]

    # Icon
    icon_m = re.search(r'<img[^>]+src="([^"]+)"', card_html)
    icon = icon_m.group(1) if icon_m else ""

    # Unique item pattern
    uniq_m = re.search(
        r'<a[^>]+href="([^"]+)"[^>]*>\s*<span\s+class="uniqueName"[^>]*>(.*?)</span>\s*(?:<span\s+class="uniqueTypeLine"[^>]*>(.*?)</span>)?\s*</a>',
        card_html,
        flags=re.S,
    )
    if uniq_m:
        slug = extract_slug(uniq_m.group(1))
        if not slug:
            return None
        name = clean_html_text(uniq_m.group(2))
        base = clean_html_text(uniq_m.group(3) or "")
        mods = parse_mods(card_html)
        return {
            "slug": slug,
            "name": name,
            "base": base,
            "mods": mods,
            "icon": icon,
            "is_unique": True,
        }

    # Generic / Gem / Viscera / Thread / Base item link inside flex-grow-1
    grow_idx = card_html.find("flex-grow-1")
    search_area = card_html[grow_idx:] if grow_idx != -1 else card_html
    link_m = re.search(
        r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        search_area,
        flags=re.S,
    )
    if not link_m:
        return None

    slug = extract_slug(link_m.group(1))
    if not slug:
        return None
    name = clean_html_text(link_m.group(2))
    if not name or name in ("RU Русский", "US English"):
        return None

    mods = parse_mods(card_html)
    return {
        "slug": slug,
        "name": name,
        "base": "",
        "mods": mods,
        "icon": icon,
        "is_unique": False,
    }


def parse_mods(card_html: str) -> List[str]:
    mods: List[str] = []
    for m in re.finditer(
        r'<div\s+class="(?:implicitMod|explicitMod|enchantMod|craftedMod)"[^>]*>(.*?)</div>',
        card_html,
        flags=re.S,
    ):
        cleaned = clean_html_text(m.group(1))
        for line in cleaned.splitlines():
            line = line.strip()
            # Strip Viscera tier prefixes like "High: " / "Low: " / "Medium: " if present
            line = re.sub(r"^(?:High|Medium|Low):\s*", "", line)
            if line:
                mods.append(line)
    return mods


def parse_page_cards(page_html: str, lang: str) -> Dict[str, Dict]:
    result: Dict[str, Dict] = {}
    for card in split_cards(page_html):
        parsed = parse_card(card, lang)
        if parsed and parsed["slug"] not in result:
            result[parsed["slug"]] = parsed
    return result


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    gems: Dict[str, Dict] = {}
    uniques: Dict[str, Dict] = {}
    items_330: Dict[str, Dict] = {}
    mod_pairs: List[Tuple[str, str]] = []
    seen_mod_pairs = set()

    for key, page in PAGES:
        print(f"Fetching {page} (us & ru)...", flush=True)
        try:
            html_us = fetch_html("us", page)
            html_ru = fetch_html("ru", page)
        except Exception as exc:
            print(f"  WARN: failed to fetch {page}: {exc}", file=sys.stderr)
            continue

        us_cards = parse_page_cards(html_us, "us")
        ru_cards = parse_page_cards(html_ru, "ru")
        matched = 0

        for slug, ru_item in ru_cards.items():
            us_item = us_cards.get(slug)
            if not us_item:
                continue
            matched += 1

            en_name = us_item["name"]
            ru_name = ru_item["name"]
            en_base = us_item["base"]
            ru_base = ru_item["base"]
            en_mods = us_item["mods"]
            ru_mods = ru_item["mods"]
            icon = ru_item["icon"] or us_item["icon"]

            if len(en_mods) == len(ru_mods) and len(en_mods) > 0:
                for m_en, m_ru in zip(en_mods, ru_mods):
                    pair = (m_en, m_ru)
                    if pair not in seen_mod_pairs:
                        seen_mod_pairs.add(pair)
                        mod_pairs.append([m_en, m_ru])

            entry = {
                "slug": slug,
                "name_en": en_name,
                "name_ru": ru_name,
                "icon": icon,
                "source": page,
            }

            if key in ("gems", "covens_gems"):
                gems[slug] = entry
            elif key in ("uniques", "covens_uniques") or ru_item["is_unique"]:
                entry["base_en"] = en_base
                entry["base_ru"] = ru_base
                entry["mods_en"] = en_mods
                entry["mods_ru"] = ru_mods
                uniques[slug] = entry
            else:
                entry["mods_en"] = en_mods
                entry["mods_ru"] = ru_mods
                items_330[slug] = entry

        print(f"  {page}: us={len(us_cards)}, ru={len(ru_cards)}, paired={matched}")

    payload = {
        "patch": "3.30.0",
        "source": "poedb.tw",
        "stats": {
            "gems": len(gems),
            "uniques": len(uniques),
            "items_330": len(items_330),
            "mod_pairs": len(mod_pairs),
        },
        "gems": gems,
        "uniques": uniques,
        "items_330": items_330,
        "mod_pairs": mod_pairs,
    }

    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {OUT_FILE}:")
    print(json.dumps(payload["stats"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
