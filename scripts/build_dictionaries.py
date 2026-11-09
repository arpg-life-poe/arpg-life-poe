#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Generates comprehensive Lua translation dictionaries for PoE 1, PoE 2,
# and Affix Templates from official GGG / PoEDB / PoE2DB datasets.
# Also exports structured JSON databases for the WordPress plugin.
#
# NOTE: ui_ru.lua is managed by the UI localization specialist (subagent #1).
# This script does NOT touch ui_ru.lua or i18n.lua.
# ==============================================================================

import glob
import gzip
import json
import os
import re
import sys
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DICT_DIR = os.path.join(ROOT_DIR, "i18n", "dictionaries")
WP_EXPORT_DIR = os.path.join(ROOT_DIR, "i18n", "export-for-wp-plugin")

# Source directories
POE_PARSER_DATA = "/Users/vlad1116/Мой диск/poe/parsers/data"
POE_TOOLTIP_DIR = "/Users/vlad1116/Мой диск/poe/poe-items-tooltip"
POE1_TREE_DIR = "/Users/vlad1116/Мой диск/poe/poe1-passive-tree"
POE2_TREE_DIR = "/Users/vlad1116/Мой диск/poe/poe2-passive-tree"
POE_ARPG_DATA = "/Users/vlad1116/Мой диск/poe-arpg-life/data"
POE_ARPG_BUILDS = "/Users/vlad1116/Мой диск/poe-arpg-life/builds/data"

# PoB Upstream directories
POB1_SRC = os.path.join(ROOT_DIR, "upstream", "PathOfBuilding-PoE1", "src")
POB2_SRC = os.path.join(ROOT_DIR, "upstream", "PathOfBuilding-PoE2", "src")

os.makedirs(DICT_DIR, exist_ok=True)
os.makedirs(WP_EXPORT_DIR, exist_ok=True)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def escape_lua(s):
    if not isinstance(s, str):
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def clean_tags(text):
    """Clean PoE markup: [Tag|Display] -> Display, [Tag] -> Tag, <rgb> -> text."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>{([^}]+)}", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[[^\]|]+\|([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    return text.strip()


def norm_key(s):
    """Normalize string key by stripping curly/straight apostrophes and spaces."""
    if not isinstance(s, str):
        return ""
    return s.replace("'", "").replace("’", "").strip()


def load_json(path):
    if not os.path.exists(path):
        print(f"  [Notice] File not found: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [Error] Failed loading {path}: {e}")
        return None


def load_json_gz(path):
    if not os.path.exists(path):
        print(f"  [Notice] GZ file not found: {path}")
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [Error] Failed loading {path}: {e}")
        return None


def save_json(path, data):
    print(f"Saving JSON to {path} ({len(data)} entries)...")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_lua_table(path, table_name, data):
    print(f"Writing {len(data)} entries to {path}...")
    with open(path, "w", encoding="utf-8") as f:
        f.write("-- ==============================================================================\n")
        f.write("-- Path of Building — ARPG-Life Edition\n")
        f.write("-- Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>\n")
        f.write("-- Project: https://arpg-life.ru\n")
        f.write("-- ==============================================================================\n\n")
        f.write(f"local {table_name} = {{\n")
        for k in sorted(data.keys()):
            v = data[k]
            if k and v and k != v:
                f.write(f'  ["{escape_lua(k)}"] = "{escape_lua(v)}",\n')
        f.write("}\n\n")
        f.write(f"return {table_name}\n")


# ------------------------------------------------------------------------------
# 1. Extract Affix Templates
# ------------------------------------------------------------------------------

def make_template_pair(en_tmpl, ru_tmpl):
    """
    Normalizes an (en, ru) pair into PoB i18n template format:
    Key: lowercase with +{0}, -{0}, {0}% placeholders
    Val: translated with +{0}, -{0}, {0}% placeholders
    """
    if not en_tmpl or not ru_tmpl:
        return None, None
    en_tmpl = clean_tags(en_tmpl).strip()
    ru_tmpl = clean_tags(ru_tmpl).strip()

    # 1. Check {value} placeholders
    c_en = en_tmpl.count("{value}")
    c_ru = ru_tmpl.count("{value}")
    if c_en > 0 and c_en == c_ru:
        idx_en = 0
        def repl_en(m):
            nonlocal idx_en
            res = f"{{{idx_en}}}"
            idx_en += 1
            return res

        idx_ru = 0
        def repl_ru(m):
            nonlocal idx_ru
            res = f"{{{idx_ru}}}"
            idx_ru += 1
            return res

        pat_en = re.sub(r"\{value\}", repl_en, en_tmpl.lower())
        pat_ru = re.sub(r"\{value\}", repl_ru, ru_tmpl)
        return pat_en, pat_ru

    # 2. Check concrete numbers / ranges: e.g. +15 to Strength / (10-15)%
    # Replaces numbers with {0}, {1} keeping signs
    idx_en = 0
    def repl_en_num(m):
        nonlocal idx_en
        sign = m.group(1) or ""
        ph = f"{sign}{{{idx_en}}}"
        idx_en += 1
        return ph
    pat_en = re.sub(r"([+-]?)(\d+(?:\.\d+)?)", repl_en_num, en_tmpl.lower())

    idx_ru = 0
    def repl_ru_num(m):
        nonlocal idx_ru
        sign = m.group(1) or ""
        ph = f"{sign}{{{idx_ru}}} "
        idx_ru += 1
        return ph.strip()
    pat_ru = re.sub(r"([+-]?)(\d+(?:\.\d+)?)", repl_ru_num, ru_tmpl)

    if idx_en > 0 and idx_en == idx_ru:
        return pat_en, pat_ru

    return None, None


# ------------------------------------------------------------------------------
# 2. Parse PoB Tree Files
# ------------------------------------------------------------------------------

def parse_pob_tree_nodes(tree_lua_path):
    """
    Extracts all node blocks from PoB tree.lua using brace counting.
    Returns dict: nodeId_str -> { "name": str, "stats": [str, ...] }
    """
    if not os.path.exists(tree_lua_path):
        print(f"Warning: tree.lua not found at {tree_lua_path}")
        return {}

    with open(tree_lua_path, "r", encoding="utf-8") as f:
        text = f.read()

    m_start = re.search(r'\n(?:\s{4}|\t)\[?\"?nodes\"?\]?\s*=\s*\{', text)
    if not m_start:
        print(f"Could not find root nodes table in {tree_lua_path}")
        return {}

    pos = m_start.end()
    pob_nodes = {}
    pattern = re.compile(r'\n(?: {8}|\t{2})\[(?:\"?([a-zA-Z0-9_]+)\"?|(\d+))\]\s*=\s*\{')

    while True:
        m = pattern.search(text, pos)
        if not m:
            break
        nid_str = m.group(1) or m.group(2)
        start_body = m.end()

        # Count braces to find node end
        depth = 1
        i = start_body
        text_len = len(text)
        while i < text_len and depth > 0:
            ch = text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            i += 1

        body = text[start_body:i-1]
        pos = i

        # Extract name
        name_m = re.search(r'\[?\"?name\"?\]?\s*=\s*\"([^\"]*)\"', body)
        name = name_m.group(1) if name_m else None

        # Extract stats block
        stats_m = re.search(r'\[?\"?stats\"?\]?\s*=\s*\{(.*?)\}', body, re.DOTALL)
        stats = []
        if stats_m:
            stats = re.findall(r'\"([^\"]+)\"', stats_m.group(1))

        if name or stats:
            pob_nodes[nid_str] = {"name": name, "stats": stats}

    return pob_nodes


# ------------------------------------------------------------------------------
# 3. Main Builder Class
# ------------------------------------------------------------------------------

class DictionaryBuilder:
    def __init__(self):
        self.affix_templates = {}
        self.unified_affixes_metadata = {}
        self.poe1_dict = {}
        self.poe2_dict = {}
        self.poe1_nodes_by_id = {}
        self.poe2_nodes_by_id = {}
        self.poe1_gems_map = {}
        self.poe2_gems_map = {}
        self.items_bases_uniques_map = {}

    def add_affix_template(self, en, ru, game="poe1"):
        k, v = make_template_pair(en, ru)
        if k and v:
            self.affix_templates[k] = v
            self.unified_affixes_metadata[k] = {
                "ru": v,
                "game": game,
            }

    # --------------------------------------------------------------------------
    # Collect All Affix Templates
    # --------------------------------------------------------------------------
    def collect_affix_templates(self):
        print("\n=== Collecting Affix Templates from All Datasets ===")

        # 1. affixes.json.gz (9 964 affixes)
        aff_gz_path = os.path.join(POE_ARPG_DATA, "affixes.json.gz")
        aff_gz = load_json_gz(aff_gz_path) or {}
        count_gz = 0
        for item in aff_gz.get("affixes", []):
            en = item.get("template_en")
            ru = item.get("template_ru")
            game = item.get("game", "poe1")
            if en and ru:
                self.add_affix_template(en, ru, game=game)
                count_gz += 1
        print(f"  Loaded {count_gz} pairs from affixes.json.gz")

        # 2. poe1_scraped_affixes.json
        s1 = load_json(os.path.join(POE_TOOLTIP_DIR, "poe1_scraped_affixes.json")) or []
        for item in s1:
            if isinstance(item, dict):
                self.add_affix_template(item.get("templateEn"), item.get("template"), game="poe1")

        # 3. poe1_eldritch_affixes.json
        s_eld = load_json(os.path.join(POE_TOOLTIP_DIR, "poe1_eldritch_affixes.json")) or []
        for item in s_eld:
            if isinstance(item, dict):
                self.add_affix_template(item.get("templateEn"), item.get("template"), game="poe1")

        # 4. poe1-affix-templates.json
        t_json = load_json(os.path.join(POE_ARPG_BUILDS, "poe1-affix-templates.json")) or {}
        for en, ru in t_json.items():
            self.add_affix_template(en, ru, game="poe1")

        # 5. Handcrafted PoE 2 Regex Stat Patterns from statTranslator.ts
        poe2_patterns = [
            ("+{value} to Strength", "+{value} к силе"),
            ("+{value} to Dexterity", "+{value} к ловкости"),
            ("+{value} to Intelligence", "+{value} к интеллекту"),
            ("+{value} to all Attributes", "+{value} ко всем характеристикам"),
            ("+{value} to any Attribute", "+{value} к любой характеристике"),
            ("+{value} to maximum Life", "+{value} к максимуму здоровья"),
            ("{value}% increased maximum Life", "{value}% увеличение максимума здоровья"),
            ("+{value} to maximum Mana", "+{value} к максимуму маны"),
            ("{value}% increased maximum Mana", "{value}% увеличение максимума маны"),
            ("{value}% increased maximum Energy Shield", "{value}% увеличение максимума энергетического щита"),
            ("+{value} to maximum Energy Shield", "+{value} к максимуму энергетического щита"),
            ("{value}% increased Mana Regeneration Rate", "{value}% увеличение скорости регенерации маны"),
            ("Recover {value}% of maximum Mana on Kill", "Восполняет {value}% от максимума маны при убийстве"),
            ("Recover {value}% of maximum Life on Kill", "Восполняет {value}% от максимума здоровья при убийстве"),
            ("+{value} to Evasion Rating", "+{value} к показателю уклонения"),
            ("{value}% increased Evasion Rating", "{value}% увеличение показателя уклонения"),
            ("+{value} to Armour", "+{value} к броне"),
            ("{value}% increased Armour", "{value}% увеличение брони"),
            ("+{value}% to Fire Resistance", "+{value}% к сопротивлению огню"),
            ("+{value}% to Cold Resistance", "+{value}% к сопротивлению холоду"),
            ("+{value}% to Lightning Resistance", "+{value}% к сопротивлению молнии"),
            ("+{value}% to Chaos Resistance", "+{value}% к сопротивлению хаосу"),
            ("+{value}% to all Elemental Resistances", "+{value}% к сопротивлению всем стихиям"),
            ("Damage Penetrates {value}% of Enemy Elemental Resistances", "Урон пробивает {value}% сопротивления стихиям врагов"),
            ("Damage Penetrates {value}% Cold Resistance", "Урон пробивает {value}% сопротивления холоду"),
            ("Damage Penetrates {value}% Lightning Resistance", "Урон пробивает {value}% сопротивления молнии"),
            ("Damage Penetrates {value}% Fire Resistance", "Урон пробивает {value}% сопротивления огню"),
            ("{value}% increased Physical Damage", "{value}% увеличение физического урона"),
            ("{value}% increased Elemental Damage", "{value}% увеличение урона от стихий"),
            ("{value}% increased Spell Damage", "{value}% увеличение урона чар"),
            ("{value}% increased Melee Damage", "{value}% увеличение урона в ближнем бою"),
            ("{value}% increased Projectile Damage", "{value}% увеличение урона снарядов"),
            ("{value}% increased Fire Damage", "{value}% увеличение урона от огня"),
            ("{value}% increased Cold Damage", "{value}% увеличение урона от холода"),
            ("{value}% increased Lightning Damage", "{value}% увеличение урона от молнии"),
            ("{value}% increased Chaos Damage", "{value}% увеличение урона от хаоса"),
            ("{value}% increased Attack Speed", "{value}% увеличение скорости атаки"),
            ("{value}% increased Cast Speed", "{value}% увеличение скорости сотворения чар"),
            ("{value}% increased Movement Speed", "{value}% увеличение скорости передвижения"),
            ("{value}% increased Critical Strike Chance", "{value}% увеличение шанса критического удара"),
            ("{value}% increased Critical Hit Chance", "{value}% увеличение шанса критического удара"),
            ("+{value}% to Critical Strike Multiplier", "+{value}% к множителю критического удара"),
            ("{value}% increased Critical Damage Bonus", "{value}% увеличение дополнительного урона от критических ударов"),
            ("{value}% increased Life Flask Charges gained", "{value}% увеличение получаемых зарядов флакона здоровья"),
            ("{value}% increased Mana Flask Charges gained", "{value}% увеличение получаемых зарядов флакона маны"),
            ("Minions deal {value}% increased Damage", "Приспешники наносят на {value}% больше урона"),
            ("Minions have {value}% increased maximum Life", "Максимум здоровья приспешников увеличен на {value}%"),
            ("Companions have {value}% increased Area of Effect", "Область действия спутников увеличена на {value}%"),
            ("{value}% increased Area of Effect", "{value}% увеличение области действия"),
            ("{value}% increased Accuracy Rating", "{value}% увеличение точности"),
            ("{value}% increased Bleeding Duration", "{value}% увеличение длительности кровотечения"),
            ("{value}% increased Freeze Buildup", "{value}% ускорение накопления заморозки"),
            ("{value}% increased Shock Buildup", "{value}% ускорение накопления шока"),
            ("{value}% increased Ignite Buildup", "{value}% ускорение накопления поджога"),
        ]
        for en, ru in poe2_patterns:
            self.add_affix_template(en, ru, game="poe2")

        print(f"  Current Affix Templates count: {len(self.affix_templates)}")

    # --------------------------------------------------------------------------
    # Build PoE 1 Data & Tree Mapping
    # --------------------------------------------------------------------------
    def build_poe1(self):
        print("\n=== Building PoE 1 Localization & Node ID Mapping ===")

        # 1. Gems
        gems1 = load_json(os.path.join(POE_PARSER_DATA, "poe1_gems_enriched.json")) or []
        for g in gems1:
            en = g.get("englishName", "").strip()
            ru = g.get("nameRu", "").strip()
            gid = g.get("gameId", "") or en
            if en and ru:
                self.poe1_dict[en] = ru
                self.poe1_gems_map[en] = ru
                if gid:
                    self.poe1_gems_map[gid] = ru
                # Support gem variations
                if en.endswith(" Support"):
                    base = en[:-8].strip()
                    self.poe1_dict[base] = ru
                    self.poe1_gems_map[base] = ru
                else:
                    self.poe1_dict[en + " Support"] = ru + " (поддержка)"
                # Normalized apostrophes
                if norm_key(en) != en:
                    self.poe1_dict[norm_key(en)] = ru

        # Manual glossaries for gems, unique jewels, and talismans/tinctures
        manual_gems = {
            "Alchemist's Mark": "Метка алхимика",
            "Alchemists Mark": "Метка алхимика",
            "Arctic Armour": "Северная броня",
            "Assassin's Mark": "Метка убийцы",
            "Assassins Mark": "Метка убийцы",
            "Battlemage's Cry": "Клич боевого мага",
            "Battlemages Cry": "Клич боевого мага",
            "General's Cry": "Клич полководца",
            "Generals Cry": "Клич полководца",
            "Guardian's Blessing": "Благословение Стража",
            "Guardians Blessing": "Благословение Стража",
            "Item Quantity": "Количество найденных предметов",
            "Phase Run": "Спешка призрака",
            "Poacher's Mark": "Метка браконьера",
            "Poachers Mark": "Метка браконьера",
            "Sniper's Mark": "Метка снайпера",
            "Snipers Mark": "Метка снайпера",
            "Vaal Breach": "Разлом Ваал",
            "Warlord's Mark": "Метка вождя",
            "Warlords Mark": "Метка вождя",
            "Chain Hook of Angling": "Цепляющий крюк ловли",
            "Dark Bargain": "Тёмная сделка",
            "Dark Bargain of Trarthus": "Тёмная сделка Трартуса",
            "Divine Blast of Radiance": "Божественный взрыв сияния",
            "Holy Hammers of Spirals": "Священные молоты спиралей",
            "Holy Sweep of Hammerfalls": "Священная расчистка камнепадов",
            "Mana-Infused Staff": "Наполненный маной посох",
            "Pact of Beidat": "Пакт Бейдата",
            "Pact of Ghorr": "Пакт Горра",
            "Pact of K'Tash": "Пакт К'Таша",
            "Pact of Lycia": "Пакт Ликии",
            "Reap of Butchery": "Жатва резни",
            "Coursing Current": "Бегущий поток",
            "Crystalfall": "Кристаллопад",
            "Communion": "Причастие",
        }
        for en, ru in manual_gems.items():
            self.poe1_dict[en] = ru
            self.poe1_gems_map[en] = ru

        # Unique jewels & special unlisted uniques
        manual_poe1_uniques = {
            "Amplification Rod": "Стержень усиления",
            "Anatomical Knowledge": "Анатомическое познание",
            "Ancient Waystones": "Древние путевые камни",
            "Apparitions": "Привидения",
            "Asenath's Chant": "Напев Асенат",
            "Assassin's Haste": "Спешка убийцы",
            "Atziri's Mirror": "Зеркало Азири",
            "Bisco's Collar": "Ошейник Биско",
            "Blood Sacrifice": "Кровавая жертва",
            "Bloodboil": "Кипение крови",
            "Brawn": "Мускулы",
            "Brittle Barrier": "Хрупкая преграда",
            "Chaber Cairn": "Каирн Чабера",
            "Cheap Construction": "Дешёвое строительство",
            "Chitus' Needle": "Игла Читуса",
            "Clear Mind": "Чистый разум",
            "Coated Shrapnel": "Смазанная картечь",
            "Cold Steel": "Холодная сталь",
            "Collateral Damage": "Сопутствующий урон",
            "Combustibles": "Горючие материалы",
            "Conqueror's Efficiency": "Эффективность покорителя",
            "Conqueror's Longevity": "Долголетие покорителя",
            "Conqueror's Potency": "Могущество покорителя",
            "Corrupted Energy": "Оскверненная энергия",
            "Dead Reckoning": "Смертоносный расчет",
            "Efficient Training": "Эффективная тренировка",
            "Energised Armour": "Энергичный доспех",
            "Energy From Within": "Внутренняя энергия",
            "Fight for Survival": "Борьба за выживание",
            "First Snow": "Первый снег",
            "Fluid Motion": "Плавность движений",
            "Fortified Legion": "Укрепленный легион",
            "Fragile Bloom": "Хрупкое цветение",
            "Growing Agony": "Растущая агония",
            "Hair Trigger": "Легкий спуск",
            "Hidden Potential": "Скрытый потенциал",
            "Inevitability": "Неизбежность",
            "Inertia": "Инерция",
            "Infectious Spores": "Заразные споры",
            "Lord of Steel": "Повелитель стали",
            "Might and Influence": "Власть и влияние",
            "Might in Mortality": "Сила в смертности",
            "Militant Faith": "Воинственная вера",
            "Natural Affinity": "Естественная близость",
            "Omen on the Winds": "Знамение на ветру",
            "One With Nothing": "Налегке",
            "Overwhelming Odds": "Превосходящие силы",
            "Pacifism": "Пацифизм",
            "Pure Talent": "Чистый талант",
            "Rain of Splinters": "Град осколков",
            "Rapid Decay": "Быстрое увядание",
            "Reckless Defence": "Безрассудная защита",
            "Ring of Blades": "Кольцо клинков",
            "Rolling Flames": "Перекатывающееся пламя",
            "Rotten Quickness": "Гнилая проворность",
            "Self-Flagellation": "Самоистязание",
            "Spire of Stone": "Каменный шпиль",
            "Split Personality": "Раздвоение личности",
            "Spirited Response": "Бодрый ответ",
            "Static Electricity": "Статическое электричество",
            "Steel Spirit": "Стальной дух",
            "The Anima Stone": "Одушевляющий камень",
            "The Blue Dream": "Голубая мечта",
            "The Blue Nightmare": "Синий кошмар",
            "The Brass Dome": "Латунный свод",
            "The Green Dream": "Зеленая мечта",
            "The Green Nightmare": "Зеленый кошмар",
            "The Red Dream": "Красная мечта",
            "The Red Nightmare": "Красный кошмар",
            "The Siege": "Осада",
            "To Dust": "В пыль",
            "Unending Hunger": "Бесконечный голод",
            "Volley Fire": "Залповый огонь",
            "Weight of the Empire": "Вес империи",
            "Winter's Bounty": "Щедрость зимы",
            "Winter's Presence": "Присутствие зимы",
        }
        for en, ru in manual_poe1_uniques.items():
            self.poe1_dict[en] = ru
            self.items_bases_uniques_map[en] = ru
            if norm_key(en) != en:
                self.poe1_dict[norm_key(en)] = ru
                self.items_bases_uniques_map[norm_key(en)] = ru

        # Talismans, Tinctures and Necropolis base types
        manual_poe1_bases = {
            "Ape Talisman": "Талисман обезьяны",
            "Ashbark Tincture": "Настойка из пепельной коры",
            "Blood Sap Tincture": "Настойка из кровавого сока",
            "Borealwood Tincture": "Настойка из северного дерева",
            "Prismatic Tincture": "Призматическая настойка",
            "Rosethorn Tincture": "Настойка из шипов розы",
            "Fulgurite Tincture": "Фульгуритовая настойка",
            "Ironwood Tincture": "Настойка из железного дерева",
            "Black Widow Talisman": "Талисман черной вдовы",
            "Blood Viper Talisman": "Талисман кровавой гадюки",
            "Bonespire Talisman": "Талисман костяного шпиля",
            "Breakrib Talisman": "Талисман сломанного ребра",
            "Chittering Talisman": "Стрекочущий талисман",
            "Claw Talisman": "Талисман когтя",
            "Deadhand Talisman": "Талисман мертвой руки",
            "Deep One Talisman": "Талисман Глубинного",
            "Fang Talisman": "Талисман клыка",
            "Horned Talisman": "Рогатый талисман",
            "Lone Antler Talisman": "Талисман одинокого рога",
            "Longtooth Talisman": "Длиннозубый талисман",
            "Mandible Talisman": "Талисман челюсти",
            "Monkey Paw Talisman": "Талисман обезьяньей лапы",
            "Monkey Twins Talisman": "Талисман обезьяньих близнецов",
            "Primal Skull Talisman": "Талисман первобытного черепа",
            "Rot Head Talisman": "Талисман гнилой головы",
            "Rotfeather Talisman": "Талисман гнилого пера",
            "Spinefuse Talisman": "Талисман сращенного хребта",
            "Splitnewt Talisman": "Талисман расколотого тритона",
            "Three Hands Talisman": "Талисман трех рук",
            "Three Rat Talisman": "Талисман трех крыс",
            "Undying Flesh Talisman": "Талисман бессмертной плоти",
            "Wereclaw Talisman": "Талисман волчьего когтя",
            "Writhing Talisman": "Извивающийся талисман",
            "Avian Twins Talisman": "Талисман птичьих близнецов",
            "Avian Twins Talisman (Cold-To-Fire)": "Талисман птичьих близнецов (Холод в огонь)",
            "Avian Twins Talisman (Cold-To-Lightning)": "Талисман птичьих близнецов (Холод в молнию)",
            "Avian Twins Talisman (Fire-To-Cold)": "Талисман птичьих близнецов (Огонь в холод)",
            "Avian Twins Talisman (Fire-To-Lightning)": "Талисман птичьих близнецов (Огонь в молнию)",
            "Avian Twins Talisman (Lightning-To-Cold)": "Талисман птичьих близнецов (Молния в холод)",
            "Boot Blade": "Сапожный клинок",
            "Boot Knife": "Сапожный нож",
            "Butcher Knife": "Мясницкий нож",
        }
        for en, ru in manual_poe1_bases.items():
            self.poe1_dict[en] = ru
            self.items_bases_uniques_map[en] = ru

        # 2. Uniques
        uniques1 = load_json(os.path.join(POE_TOOLTIP_DIR, "poe1_unique_items.json")) or []
        uniques_allflame = load_json(os.path.join(POE_TOOLTIP_DIR, "poe1_unique_items_3_29_allflame.json")) or []
        for u in (uniques1 + uniques_allflame):
            if isinstance(u, dict):
                en = u.get("englishName", "").strip()
                ru = u.get("nameRu", "").strip()
                if en and ru:
                    self.poe1_dict[en] = ru
                    self.items_bases_uniques_map[en] = ru
                    # Normalized apostrophes
                    if norm_key(en) != en:
                        self.poe1_dict[norm_key(en)] = ru
                        self.items_bases_uniques_map[norm_key(en)] = ru
                    # Replicas
                    replica_en = f"Replica {en}"
                    replica_ru = f"Копия {ru}"
                    self.poe1_dict[replica_en] = replica_ru
                    self.items_bases_uniques_map[replica_en] = replica_ru

        # 3. Bases
        bases1 = load_json(os.path.join(POE_PARSER_DATA, "poe1_base_items.json")) or []
        for b in bases1:
            en = b.get("englishName", "").strip()
            ru = b.get("nameRu", "").strip()
            if en and ru:
                self.poe1_dict[en] = ru
                self.items_bases_uniques_map[en] = ru
                if norm_key(en) != en:
                    self.poe1_dict[norm_key(en)] = ru
                    self.items_bases_uniques_map[norm_key(en)] = ru

        # 4. Currency
        curr1 = load_json(os.path.join(POE_TOOLTIP_DIR, "poe1_currency.json")) or []
        for c in curr1:
            en = c.get("englishName", "").strip()
            ru = c.get("nameRu", "").strip()
            if en and ru:
                self.poe1_dict[en] = ru
                if norm_key(en) != en:
                    self.poe1_dict[norm_key(en)] = ru

        # 5. Passive Tree (Skill Trees/3.29.0)
        tree_raw = load_json(os.path.join(POE1_TREE_DIR, "Skill Trees", "3.29.0", "raw.json")) or {}
        tree_loc = load_json(os.path.join(POE1_TREE_DIR, "Skill Trees", "3.29.0", "localization-ru.json")) or {}
        raw_nodes = tree_raw.get("nodes", {})
        loc_nodes = tree_loc.get("nodes", {})

        # Also load PoB tree.lua directly to ensure exact string matching
        pob1_nodes = parse_pob_tree_nodes(os.path.join(POB1_SRC, "TreeData", "3_29", "tree.lua"))
        print(f"  PoB1 3_29 tree.lua parsed: {len(pob1_nodes)} nodes")

        # Missing Forbidden Flesh/Flame Ascendant nodes manual glossary
        ascendant_missing = {
            "Nine Lives": "Девять жизней",
            "Harness the Void": "Впрячь пустоту",
            "Fury of Nature": "Ярость природы",
            "Indomitable Resolve": "Неукротимая решимость",
            "Fatal Flourish": "Роковой росчерк",
            "Searing Purity": "Опаляющая чистота",
            "Unleashed Potential": "Высвобожденный потенциал",
        }
        for en, ru in ascendant_missing.items():
            self.poe1_dict[en] = ru

        matched_pob1_names = 0
        matched_pob1_stats = 0
        total_pob1_names = sum(1 for n in pob1_nodes.values() if n["name"])
        total_pob1_stats = sum(len(n["stats"]) for n in pob1_nodes.values())

        # Match all nodes by ID
        all_node_ids = set(raw_nodes.keys()).union(set(loc_nodes.keys())).union(set(str(k) for k in pob1_nodes.keys()))
        for nid_str in all_node_ids:
            nid_int = int(nid_str) if nid_str.isdigit() else None
            r_node = raw_nodes.get(nid_str, {})
            l_node = loc_nodes.get(nid_str, {})
            p_node = pob1_nodes.get(nid_str) or (pob1_nodes.get(nid_int, {}) if nid_int is not None else {})

            en_name = p_node.get("name") or r_node.get("name")
            ru_name = l_node.get("name") or (ascendant_missing.get(en_name) if en_name else None)

            if en_name and ru_name:
                self.poe1_dict[en_name.strip()] = ru_name.strip()
                if p_node.get("name"):
                    matched_pob1_names += 1

            r_stats = p_node.get("stats") or r_node.get("stats") or []
            l_stats = l_node.get("stats") or []

            stats_en_export = []
            stats_ru_export = []

            for i, s_en in enumerate(r_stats):
                s_en_clean = clean_tags(s_en).strip()
                s_ru = l_stats[i].strip() if i < len(l_stats) and l_stats[i] else None

                if s_en_clean and s_ru:
                    self.poe1_dict[s_en_clean] = s_ru
                    self.add_affix_template(s_en_clean, s_ru, game="poe1")
                    stats_en_export.append(s_en_clean)
                    stats_ru_export.append(s_ru)
                    if p_node.get("stats"):
                        matched_pob1_stats += 1
                elif s_en_clean:
                    stats_en_export.append(s_en_clean)

            if en_name or stats_en_export:
                self.poe1_nodes_by_id[nid_str] = {
                    "name_en": en_name or "",
                    "name_ru": ru_name or "",
                    "stats_en": stats_en_export,
                    "stats_ru": stats_ru_export,
                }

        print(f"  PoE 1 Node Names direct match: {matched_pob1_names}/{total_pob1_names} ({matched_pob1_names/total_pob1_names*100:.1f}%)")
        print(f"  PoE 1 Node Stats direct match: {matched_pob1_stats}/{total_pob1_stats} ({matched_pob1_stats/total_pob1_stats*100:.1f}%)")

    # --------------------------------------------------------------------------
    # Build PoE 2 Data & Tree Mapping
    # --------------------------------------------------------------------------
    def build_poe2(self):
        print("\n=== Building PoE 2 Localization & Node ID Mapping ===")

        # 1. Distilled Emotions (PoE 2 anointment oils / emotions)
        emotions = {
            "Suffering": "Страдание",
            "Isolation": "Изоляция",
            "Fear": "Страх",
            "Despair": "Отчаяние",
            "Disgust": "Отвращение",
            "Greed": "Жадность",
            "Envy": "Зависть",
            "Ire": "Гнев",
            "Guilt": "Вина",
            "Contempt": "Презрение",
            "Ferocity": "Свирепость",
            "Melancholy": "Меланхолия",
            "Paranoia": "Паранойя",
        }
        for en, ru in emotions.items():
            self.poe2_dict[en] = ru

        # 2. Classes & Ascendancies
        classes_poe2 = {
            "Warrior": "Воин",
            "Titan": "Титан",
            "Warbringer": "Вестник войны",
            "Smith of Kitava": "Кузнец Китавы",
            "Monk": "Монах",
            "Invoker": "Заклинатель стихий",
            "Acolyte of Chayula": "Послушник Чаюлы",
            "Martial Artist": "Мастер боевых искусств",
            "Sorceress": "Заклинательница",
            "Stormweaver": "Ткач бурь",
            "Chronomancer": "Хрономант",
            "Disciple of Varashta": "Ученица Варашты",
            "Mercenary": "Наемник",
            "Witchhunter": "Охотник на ведьм",
            "Gemling Legionnaire": "Легионер каменитов",
            "Tactician": "Тактик",
            "Ranger": "Охотница",
            "Deadeye": "Снайпер",
            "Pathfinder": "Следопыт",
            "Huntress": "Копейщица",
            "Amazon": "Амазонка",
            "Spirit Walker": "Ходящая среди духов",
            "Ritualist": "Ритуалист",
            "Witch": "Ведьма",
            "Infernalist": "Инферналист",
            "Blood Mage": "Маг крови",
            "Lich": "Лич",
            "Abyssal Lich": "Лич Бездны",
            "Druid": "Друид",
            "Oracle": "Оракул",
            "Shaman": "Шаман",
        }
        for en, ru in classes_poe2.items():
            self.poe2_dict[en] = ru

        # 3. Gems
        gems2 = load_json(os.path.join(POE_PARSER_DATA, "poe2_gems_enriched.json")) or []
        for g in gems2:
            en = g.get("englishName", "").strip()
            ru = g.get("nameRu", "").strip()
            gid = g.get("gameId", "") or en
            if en and ru:
                self.poe2_dict[en] = ru
                self.poe2_gems_map[en] = ru
                if gid:
                    self.poe2_gems_map[gid] = ru
                if en.endswith(" Support"):
                    base = en[:-8].strip()
                    self.poe2_dict[base] = ru
                    self.poe2_gems_map[base] = ru
                else:
                    self.poe2_dict[en + " Support"] = ru + " (поддержка)"
                if norm_key(en) != en:
                    self.poe2_dict[norm_key(en)] = ru

        manual_poe2_gems = {
            "Abyssal Apparition": "Призрак Бездны",
            "Ancestral Aid": "Помощь предков",
            "Arms Length": "Расстояние вытянутой руки",
            "Atziri's Communion": "Причастие Азири",
            "Azmerian Swarms": "Азмирийские рои",
            "Azmerian Wolf": "Азмирийский волк",
            "Black Powder Blitz": "Блиц черного пороха",
            "Breachlord's Rift": "Разлом владыки Разлома",
            "Bursting Fen Toad": "Взрывающаяся болотная жаба",
            "Cackling Companions": "Хохочущие спутники",
            "Cast on Charm Use": "Сотворение чар при использовании талисмана",
            "Cast on Melee Kill": "Сотворение чар при убийстве в ближнем бою",
            "Cast on Melee Stun": "Сотворение чар при оглушении в ближнем бою",
            "Chaotic Surge": "Всплеск хаоса",
            "Charm Bounty": "Щедрость талисмана",
            "Crackling Palm": "Трещащая ладонь",
            "Crushing Fear": "Сокрушительный страх",
            "Curse on Block": "Проклятие при блоке",
            "Daze": "Ошеломление",
            "Ahn's Citadel": "Цитадель Ана",
            "Ailith's Chimes": "Колокольчики Айлит",
            "Alchemist's Boon": "Дар алхимика",
            "Amanamu's Tithe": "Десятина Аманаму",
            "Arakaali's Lust": "Похоть Аракаали",
            "Arbiter's Ignition": "Воспламенение Вершителя",
            "Arbiter's Reach": "Хватка Вершителя",
            "Arjun's Medal": "Медаль Арджуна",
            "Atalui's Bloodletting": "Кровопускание Аталуи",
            "Atziri's Allure": "Очарование Азири",
            "Atziri's Impatience": "Нетерпение Азири",
            "Bhatair's Vengeance": "Месть Батейра",
            "Bloodhound's Mark": "Метка ищейки",
            "Breachlord's Amalgam": "Амальгама владыки Разлома",
            "Brutus' Brain": "Мозг Брута",
        }
        for en, ru in manual_poe2_gems.items():
            self.poe2_dict[en] = ru
            self.poe2_gems_map[en] = ru
            if norm_key(en) != en:
                self.poe2_dict[norm_key(en)] = ru
                self.poe2_gems_map[norm_key(en)] = ru

        # Special tree stat fragments in PoE 2
        manual_poe2_stats = {
            "Energy Shield does not Recharge": "Энергетический щит не перезаряжается",
            "Cannot Dodge Roll or Sprint": "Нельзя кувыркаться или бежать со спринтом",
            "Deal no Non-Fire Damage": "Не наносит не-огненный урон",
            "Chance to Deflect is Lucky": "Шанс отражения удачлив",
            "additional Elemental Infusion of the same type": "дополнительный стихийный настой того же типа",
            "expend Ammunition if you've Reloaded Recently": "тратят боеприпасы, если вы недавно перезарядились",
            "a One-Handed Martial Weapon equipped in your Main Hand": "одноручное боевое оружие в основной руке",
            "contributes to Flammability and Ignite Magnitudes": "увеличивает силу воспламеняемости и поджога",
            "Invocation Skills cannot gain Energy while Triggering Spells": "Умения взывания не могут получать энергию во время срабатывания чар",
            "by no Elemental Ailments": "никакими стихийными состояниями",
            "tenth of their maximum Life as Fire Damage": "десятую часть от максимума здоровья в виде урона от огня",
            "Your Offerings affect you instead of your Minions": "Ваши подношения действуют на вас вместо ваших приспешников",
            "Base Bleeding Duration is 1 second": "Базовая длительность кровотечения 1 сек.",
            "50% more Magnitude of Bleeding you inflict": "На 50% больше силы накладываемого вами кровотечения",
            "Gain additional Critical Hit Chance equal to 25% of excess chance to Hit with Attacks": "Дарует дополнительный шанс критического удара, равный 25% избыточного шанса попадания атаками",
            "Invoked Spells consume 50% less Energy": "Взываемые чары расходуют на 50% меньше энергии",
            "40% increased Critical Hit Chance after 7 metres": "40% увеличение шанса критического удара после 7 метров",
            "to 25% of your main hand Weapon's damage": "до 25% урона оружия в основной руке",
            "30% more Recovery from Flasks": "На 30% больше восстановления от флаконов",
        }
        for en, ru in manual_poe2_stats.items():
            self.poe2_dict[en] = ru
            self.add_affix_template(en, ru, game="poe2")

        # 4. Uniques
        uniques2 = load_json(os.path.join(POE_PARSER_DATA, "poe2_unique_items.json")) or []
        for u in uniques2:
            if isinstance(u, dict):
                en = u.get("englishName", "").strip()
                ru = u.get("nameRu", "").strip()
                if en and ru:
                    self.poe2_dict[en] = ru
                    self.items_bases_uniques_map[en] = ru
                    if norm_key(en) != en:
                        self.poe2_dict[norm_key(en)] = ru
                        self.items_bases_uniques_map[norm_key(en)] = ru
                # Extract granted skills
                for gs in u.get("grantsSkills", []):
                    m = re.search(r"Дарует умение:\s*(?:Уровень \d+\s*)?(.*)", gs)
                    if m:
                        skill_ru = m.group(1).strip()
                        # Often English skill name is linked in PoB
                        pass

        # 5. Bases
        bases2 = load_json(os.path.join(POE_PARSER_DATA, "poe2_base_items.json")) or []
        for b in bases2:
            en = b.get("englishName", "").strip()
            ru = b.get("nameRu", "").strip()
            if en and ru:
                self.poe2_dict[en] = ru
                self.items_bases_uniques_map[en] = ru
                if norm_key(en) != en:
                    self.poe2_dict[norm_key(en)] = ru
                    self.items_bases_uniques_map[norm_key(en)] = ru

        # 6. Currency
        curr2 = load_json(os.path.join(POE_TOOLTIP_DIR, "poe2_currency.json")) or []
        for c in curr2:
            en = c.get("englishName", "").strip()
            ru = c.get("nameRu", "").strip()
            if en and ru:
                self.poe2_dict[en] = ru
                if norm_key(en) != en:
                    self.poe2_dict[norm_key(en)] = ru

        # 7. Passive Tree (Skill Trees/0.5.0/data.json + nodes_to_translate.json + custom_translations.json)
        tree2_data = load_json(os.path.join(POE2_TREE_DIR, "Skill Trees", "0.5.0", "data.json")) or {}
        data2_nodes = tree2_data.get("nodes", {})

        nt2 = load_json(os.path.join(POE2_TREE_DIR, "nodes_to_translate.json")) or {}
        ct2 = load_json(os.path.join(POE2_TREE_DIR, "src", "tree", "custom_translations.json")) or {}

        all_tree2_names = {**ct2.get("names", {}), **nt2.get("names", {})}
        all_tree2_stats = {**ct2.get("stats", {}), **nt2.get("stats", {})}

        # Populate dictionaries with cleaned tag variants
        for en_k, ru_v in all_tree2_names.items():
            if en_k and ru_v:
                en_c = clean_tags(en_k).strip()
                ru_c = clean_tags(ru_v).strip()
                self.poe2_dict[en_c] = ru_c
                self.poe2_dict[en_k.strip()] = ru_c

        for en_k, ru_v in all_tree2_stats.items():
            if en_k and ru_v:
                en_c = clean_tags(en_k).strip()
                ru_c = clean_tags(ru_v).strip()
                self.poe2_dict[en_c] = ru_c
                self.poe2_dict[en_k.strip()] = ru_c
                self.add_affix_template(en_c, ru_c, game="poe2")

        # Load PoB2 0_5/tree.lua
        pob2_nodes = parse_pob_tree_nodes(os.path.join(POB2_SRC, "TreeData", "0_5", "tree.lua"))
        print(f"  PoB2 0_5 tree.lua parsed: {len(pob2_nodes)} nodes")

        matched_pob2_names = 0
        matched_pob2_stats = 0
        total_pob2_names = sum(1 for n in pob2_nodes.values() if n["name"])
        total_pob2_stats = sum(len(n["stats"]) for n in pob2_nodes.values())

        all_node_ids = set(data2_nodes.keys()).union(set(str(k) for k in pob2_nodes.keys()))
        for nid_str in all_node_ids:
            nid_int = int(nid_str) if nid_str.isdigit() else None
            d_node = data2_nodes.get(nid_str, {})
            p_node = pob2_nodes.get(nid_str) or (pob2_nodes.get(nid_int, {}) if nid_int is not None else {})

            en_raw_name = d_node.get("name") or p_node.get("name")
            en_clean_name = clean_tags(en_raw_name).strip() if en_raw_name else ""

            ru_name = all_tree2_names.get(en_raw_name) or all_tree2_names.get(en_clean_name) or classes_poe2.get(en_clean_name)
            if ru_name:
                ru_name = clean_tags(ru_name).strip()
                self.poe2_dict[en_clean_name] = ru_name
                if p_node.get("name"):
                    matched_pob2_names += 1

            d_stats = d_node.get("stats") or []
            p_stats = p_node.get("stats") or []

            stats_en_export = []
            stats_ru_export = []

            # Handle direct stats matching by node ID
            for i, p_stat in enumerate(p_stats):
                p_clean = clean_tags(p_stat).strip()
                ru_stat = None

                # 1. Match against corresponding data.json stat index
                if i < len(d_stats):
                    d_raw = d_stats[i]
                    ru_stat = all_tree2_stats.get(d_raw) or all_tree2_stats.get(clean_tags(d_raw))

                # 2. Match against global stats dictionary
                if not ru_stat:
                    ru_stat = all_tree2_stats.get(p_stat) or all_tree2_stats.get(p_clean)

                if ru_stat:
                    ru_clean = clean_tags(ru_stat).strip()
                    self.poe2_dict[p_clean] = ru_clean
                    self.add_affix_template(p_clean, ru_clean, game="poe2")
                    stats_en_export.append(p_clean)
                    stats_ru_export.append(ru_clean)
                    matched_pob2_stats += 1
                else:
                    stats_en_export.append(p_clean)

            # Also handle merged multi-line stats (e.g. phrases split across 2 lines in tree.lua)
            if len(p_stats) >= 2:
                combined_en = " ".join(clean_tags(s).strip() for s in p_stats)
                for d_s in d_stats:
                    if clean_tags(d_s).strip() == combined_en:
                        combined_ru = all_tree2_stats.get(d_s)
                        if combined_ru:
                            combined_ru_clean = clean_tags(combined_ru).strip()
                            self.poe2_dict[combined_en] = combined_ru_clean
                            self.add_affix_template(combined_en, combined_ru_clean, game="poe2")

            if en_clean_name or stats_en_export:
                self.poe2_nodes_by_id[nid_str] = {
                    "name_en": en_clean_name,
                    "name_ru": ru_name or "",
                    "stats_en": stats_en_export,
                    "stats_ru": stats_ru_export,
                }

        print(f"  PoE 2 Node Names direct match: {matched_pob2_names}/{total_pob2_names} ({matched_pob2_names/total_pob2_names*100:.1f}%)")
        print(f"  PoE 2 Node Stats direct match: {matched_pob2_stats}/{total_pob2_stats} ({matched_pob2_stats/total_pob2_stats*100:.1f}%)")

    # --------------------------------------------------------------------------
    # Collect Reminder Texts for Tooltips
    # --------------------------------------------------------------------------
    def collect_reminder_texts(self):
        print("\n=== Collecting Reminder Texts from Passive Trees ===")
        rem_path = os.path.join(POE1_TREE_DIR, "Skill Trees", "3.29.0", "reminder-text-ru.json")
        raw_path = os.path.join(POE1_TREE_DIR, "Skill Trees", "3.29.0", "raw.json")

        rem_ru = load_json(rem_path) or {}
        raw_nodes = (load_json(raw_path) or {}).get("nodes", {})

        count = 0
        for nid, ru_lines in rem_ru.items():
            if nid in raw_nodes:
                en_lines = raw_nodes[nid].get("reminderText", [])
                if len(en_lines) == len(ru_lines):
                    for s_en, s_ru in zip(en_lines, ru_lines):
                        s_en_clean = clean_tags(s_en).strip()
                        s_ru_clean = clean_tags(s_ru).strip()
                        if s_en_clean and s_ru_clean:
                            self.poe1_dict[s_en_clean] = s_ru_clean
                            if s_en_clean.startswith("(") and s_en_clean.endswith(")"):
                                self.poe1_dict[s_en_clean[1:-1].strip()] = s_ru_clean.strip("()")
                            count += 1
                    if nid in self.poe1_nodes_by_id:
                        self.poe1_nodes_by_id[nid]["reminder_text_en"] = en_lines
                        self.poe1_nodes_by_id[nid]["reminder_text_ru"] = ru_lines
        print(f"  Loaded {count} reminderText pairs for PoE 1")

    # --------------------------------------------------------------------------
    # Collect Gem Descriptions for Tooltips
    # --------------------------------------------------------------------------
    def collect_gem_descriptions(self):
        print("\n=== Collecting Gem Descriptions for Tooltips ===")
        # PoE 1
        g1 = load_json(os.path.join(POE_PARSER_DATA, "poe1_gems_enriched.json")) or []
        g1_map = {x.get("englishName", "").strip(): x.get("description", "").strip() for x in g1 if x.get("description")}

        count1 = 0
        pob1_skills_path = os.path.join(POB1_SRC, "Data", "Skills", "*.lua")
        for p in glob.glob(pob1_skills_path):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            for name, desc in re.findall(r'name\s*=\s*\"([^\"]+)\".*?description\s*=\s*\"([^\"]+)\"', content, re.DOTALL):
                ru_desc = g1_map.get(name) or g1_map.get(name.replace(" Support", ""))
                if ru_desc:
                    desc_clean = clean_tags(desc).strip()
                    ru_desc_clean = clean_tags(ru_desc).strip()
                    self.poe1_dict[desc_clean] = ru_desc_clean
                    count1 += 1
        print(f"  Loaded {count1} gem descriptions for PoE 1")

        # PoE 2
        g2 = load_json(os.path.join(POE_PARSER_DATA, "poe2_gems_enriched.json")) or []
        g2_map = {x.get("englishName", "").strip(): x.get("description", "").strip() for x in g2 if x.get("description")}

        count2 = 0
        pob2_skills_path = os.path.join(POB2_SRC, "Data", "Skills", "*.lua")
        for p in glob.glob(pob2_skills_path):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            for name, desc in re.findall(r'name\s*=\s*\"([^\"]+)\".*?description\s*=\s*\"([^\"]+)\"', content, re.DOTALL):
                ru_desc = g2_map.get(name) or g2_map.get(name.replace(" Support", ""))
                if ru_desc:
                    desc_clean = clean_tags(desc).strip()
                    ru_desc_clean = clean_tags(ru_desc).strip()
                    self.poe2_dict[desc_clean] = ru_desc_clean
                    count2 += 1
        print(f"  Loaded {count2} gem descriptions for PoE 2")

    # --------------------------------------------------------------------------
    # Collect Unique Item Mod Pairs for Tooltips
    # --------------------------------------------------------------------------
    def collect_unique_mod_pairs(self):
        print("\n=== Collecting Unique Item Mod Pairs for Tooltips ===")

        def process_uniques(uniques_json_path, pob_uniques_glob, target_dict, game):
            u_list = load_json(uniques_json_path) or []
            u_by_name = {x.get("englishName", "").strip(): x for x in u_list if x.get("englishName")}
            u_norm = {norm_key(k): v for k, v in u_by_name.items()}

            pair_count = 0
            for file_path in glob.glob(pob_uniques_glob):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                blocks = re.findall(r'\[\[\s*\n(.*?)\n\]\]', content, re.DOTALL)
                for b in blocks:
                    lines = [line.strip() for line in b.split('\n') if line.strip()]
                    if not lines:
                        continue
                    item_name = lines[0]
                    u_json = u_by_name.get(item_name) or u_norm.get(norm_key(item_name))
                    if not u_json:
                        continue

                    # Filter English mod lines
                    en_mods = []
                    for line in lines[2:]:
                        if line.startswith("Variant:") or line.startswith("Requires ") or line.startswith("Implicits:"):
                            continue
                        clean_line = re.sub(r'\{variant:[^}]+\}', '', line)
                        clean_line = re.sub(r'\{tags:[^}]+\}', '', clean_line).strip()
                        if clean_line:
                            en_mods.append(clean_line)

                    ru_mods = (u_json.get("implicitMods") or []) + (u_json.get("explicitMods") or [])
                    if len(en_mods) == len(ru_mods):
                        for s_en, s_ru in zip(en_mods, ru_mods):
                            s_en_clean = clean_tags(s_en).strip()
                            s_ru_clean = clean_tags(s_ru).strip()
                            if s_en_clean and s_ru_clean:
                                target_dict[s_en_clean] = s_ru_clean
                                self.add_affix_template(s_en_clean, s_ru_clean, game=game)
                                pair_count += 1
            return pair_count

        p1_pairs = process_uniques(
            os.path.join(POE_TOOLTIP_DIR, "poe1_unique_items.json"),
            os.path.join(POB1_SRC, "Data", "Uniques", "*.lua"),
            self.poe1_dict,
            "poe1"
        )
        print(f"  Extracted {p1_pairs} unique item mod pairs for PoE 1")

        p2_pairs = process_uniques(
            os.path.join(POE_PARSER_DATA, "poe2_unique_items.json"),
            os.path.join(POB2_SRC, "Data", "Uniques", "*.lua"),
            self.poe2_dict,
            "poe2"
        )
        print(f"  Extracted {p2_pairs} unique item mod pairs for PoE 2")

    # --------------------------------------------------------------------------
    # Save Everything
    # --------------------------------------------------------------------------
    def save_all(self):
        print("\n=== Saving Lua Dictionaries and WP JSON Databases ===")

        # 1. Lua dictionaries for PoB
        write_lua_table(os.path.join(DICT_DIR, "affix_templates.lua"), "affix_templates", self.affix_templates)
        write_lua_table(os.path.join(DICT_DIR, "poe1_ru.lua"), "poe1_ru", self.poe1_dict)
        write_lua_table(os.path.join(DICT_DIR, "poe2_ru.lua"), "poe2_ru", self.poe2_dict)

        # 2. Structured JSON for WordPress PoE Plugin
        save_json(os.path.join(WP_EXPORT_DIR, "poe1_nodes_by_id.json"), self.poe1_nodes_by_id)
        save_json(os.path.join(WP_EXPORT_DIR, "poe2_nodes_by_id.json"), self.poe2_nodes_by_id)
        save_json(os.path.join(WP_EXPORT_DIR, "poe1_gems_map.json"), self.poe1_gems_map)
        save_json(os.path.join(WP_EXPORT_DIR, "poe2_gems_map.json"), self.poe2_gems_map)
        save_json(os.path.join(WP_EXPORT_DIR, "unified_affix_templates.json"), self.unified_affixes_metadata)
        save_json(os.path.join(WP_EXPORT_DIR, "items_bases_uniques_map.json"), self.items_bases_uniques_map)

    # --------------------------------------------------------------------------
    # Coverage Verification Engine
    # --------------------------------------------------------------------------
    def verify_coverage(self):
        print("\n==============================================================================")
        print("Path of Building ARPG-Life: Comprehensive Translation Coverage Audit")
        print("==============================================================================")

        def simulate_translate(text, game_dict):
            if not text:
                return text, True
            t_strip = text.strip()
            # 1. Direct dictionary match
            if t_strip in game_dict:
                return game_dict[t_strip], True
            if t_strip.lower() in game_dict:
                return game_dict[t_strip.lower()], True
            if norm_key(t_strip) in game_dict:
                return game_dict[norm_key(t_strip)], True

            # 2. Template matching
            if any(ch.isdigit() for ch in t_strip):
                idx = 0
                nums = []
                def repl(m):
                    nonlocal idx
                    sign = m.group(1) or ""
                    num = m.group(2)
                    ph = f"{sign}{{{idx}}}"
                    nums.append(num)
                    idx += 1
                    return ph

                pat = re.sub(r"([+-]?)(\d+(?:\.\d+)?)", repl, t_strip.lower())
                trans = self.affix_templates.get(pat) or self.affix_templates.get(pat.strip())
                if trans:
                    return trans, True

            return t_strip, False

        # --- AUDIT POE 1 ---
        print("\n--- Auditing Path of Building (PoE 1) ---")
        pob1_nodes = parse_pob_tree_nodes(os.path.join(POB1_SRC, "TreeData", "3_29", "tree.lua"))
        pob1_names_total = 0
        pob1_names_ok = 0
        pob1_stats_total = 0
        pob1_stats_ok = 0

        for n in pob1_nodes.values():
            if n["name"]:
                pob1_names_total += 1
                _, ok = simulate_translate(n["name"], self.poe1_dict)
                if ok:
                    pob1_names_ok += 1
            for s in n["stats"]:
                pob1_stats_total += 1
                _, ok = simulate_translate(s, self.poe1_dict)
                if ok:
                    pob1_stats_ok += 1

        # Gems
        with open(os.path.join(POB1_SRC, "Data", "Gems.lua"), "r", encoding="utf-8") as f:
            pob1_gems = set(re.findall(r'name\s*=\s*\"([^\"]+)\"', f.read()))
        pob1_gems_ok = sum(1 for g in pob1_gems if simulate_translate(g, self.poe1_dict)[1])

        # Bases
        pob1_bases = set()
        for p in glob.glob(os.path.join(POB1_SRC, "Data", "Bases", "*.lua")):
            with open(p, "r", encoding="utf-8") as f:
                pob1_bases.update(re.findall(r'itemBases\[\"([^\"]+)\"\]', f.read()))
        pob1_bases_ok = sum(1 for b in pob1_bases if simulate_translate(b, self.poe1_dict)[1])

        # Uniques
        pob1_uniques = set()
        for p in glob.glob(os.path.join(POB1_SRC, "Data", "Uniques", "*.lua")):
            with open(p, "r", encoding="utf-8") as f:
                pob1_uniques.update(re.findall(r'\[\[\s*\n([^\n]+)', f.read()))
        pob1_uniques_ok = sum(1 for u in pob1_uniques if simulate_translate(u, self.poe1_dict)[1])

        print(f"  Passive Tree Node Names: {pob1_names_ok}/{pob1_names_total} ({pob1_names_ok/pob1_names_total*100:.2f}%)")
        print(f"  Passive Tree Node Stats: {pob1_stats_ok}/{pob1_stats_total} ({pob1_stats_ok/pob1_stats_total*100:.2f}%)")
        print(f"  Skill & Support Gems:    {pob1_gems_ok}/{len(pob1_gems)} ({pob1_gems_ok/len(pob1_gems)*100:.2f}%)")
        print(f"  Base Item Types:         {pob1_bases_ok}/{len(pob1_bases)} ({pob1_bases_ok/len(pob1_bases)*100:.2f}%)")
        print(f"  Unique Items:            {pob1_uniques_ok}/{len(pob1_uniques)} ({pob1_uniques_ok/len(pob1_uniques)*100:.2f}%)")

        # --- AUDIT POE 2 ---
        print("\n--- Auditing Path of Building (PoE 2) ---")
        pob2_nodes = parse_pob_tree_nodes(os.path.join(POB2_SRC, "TreeData", "0_5", "tree.lua"))
        pob2_names_total = 0
        pob2_names_ok = 0
        pob2_stats_total = 0
        pob2_stats_ok = 0

        for n in pob2_nodes.values():
            if n["name"]:
                pob2_names_total += 1
                _, ok = simulate_translate(n["name"], self.poe2_dict)
                if ok:
                    pob2_names_ok += 1
            for s in n["stats"]:
                pob2_stats_total += 1
                _, ok = simulate_translate(s, self.poe2_dict)
                if ok:
                    pob2_stats_ok += 1

        # Gems
        with open(os.path.join(POB2_SRC, "Data", "Gems.lua"), "r", encoding="utf-8") as f:
            pob2_gems = set(re.findall(r'name\s*=\s*\"([^\"]+)\"', f.read()))
        pob2_gems_ok = sum(1 for g in pob2_gems if simulate_translate(g, self.poe2_dict)[1])

        # Bases
        pob2_bases = set()
        for p in glob.glob(os.path.join(POB2_SRC, "Data", "Bases", "*.lua")):
            with open(p, "r", encoding="utf-8") as f:
                pob2_bases.update(re.findall(r'itemBases\[\"([^\"]+)\"\]', f.read()))
        pob2_bases_ok = sum(1 for b in pob2_bases if simulate_translate(b, self.poe2_dict)[1])

        # Uniques
        pob2_uniques = set()
        for p in glob.glob(os.path.join(POB2_SRC, "Data", "Uniques", "*.lua")):
            with open(p, "r", encoding="utf-8") as f:
                pob2_uniques.update(re.findall(r'\[\[\s*\n([^\n]+)', f.read()))
        pob2_uniques_ok = sum(1 for u in pob2_uniques if simulate_translate(u, self.poe2_dict)[1])

        print(f"  Passive Tree Node Names: {pob2_names_ok}/{pob2_names_total} ({pob2_names_ok/pob2_names_total*100:.2f}%)")
        print(f"  Passive Tree Node Stats: {pob2_stats_ok}/{pob2_stats_total} ({pob2_stats_ok/pob2_stats_total*100:.2f}%)")
        print(f"  Skill & Support Gems:    {pob2_gems_ok}/{len(pob2_gems)} ({pob2_gems_ok/len(pob2_gems)*100:.2f}%)")
        print(f"  Base Item Types:         {pob2_bases_ok}/{len(pob2_bases)} ({pob2_bases_ok/len(pob2_bases)*100:.2f}%)")
        print(f"  Unique Items:            {pob2_uniques_ok}/{len(pob2_uniques)} ({pob2_uniques_ok/len(pob2_uniques)*100:.2f}%)")
        print("==============================================================================\n")


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------

def main():
    builder = DictionaryBuilder()
    builder.collect_affix_templates()
    builder.build_poe1()
    builder.build_poe2()
    builder.collect_reminder_texts()
    builder.collect_gem_descriptions()
    builder.collect_unique_mod_pairs()
    builder.save_all()
    builder.verify_coverage()


if __name__ == "__main__":
    main()
