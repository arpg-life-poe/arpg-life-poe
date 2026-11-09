#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Generates compact Lua translation dictionaries for PoE 1, PoE 2, and UI
# ==============================================================================

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DICT_DIR = os.path.join(ROOT_DIR, "i18n", "dictionaries")
POE_DATA_DIR = "/Users/vlad1116/Мой диск/poe/parsers/data"
POE_TOOLTIP_DIR = "/Users/vlad1116/Мой диск/poe/poe-items-tooltip"
POE_TREE_DIR = "/Users/vlad1116/Мой диск/poe/poe1-passive-tree"
POE2_TREE_DIR = "/Users/vlad1116/Мой диск/poe/poe2-passive-tree"
AFFIX_DATA_DIR = "/Users/vlad1116/Мой диск/poe-arpg-life/builds/data"

os.makedirs(DICT_DIR, exist_ok=True)

def escape_lua(s):
    if not isinstance(s, str):
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

def load_json(path):
    if not os.path.exists(path):
        print(f"Warning: file not found {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None

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
# 1. UI Dictionary (Optimized widths to avoid button/panel overflows)
# ------------------------------------------------------------------------------
UI_TRANSLATIONS = {
    # Top Bar Left Controls
    "<< Back": "<< Назад",
    "Back": "Назад",
    "Save": "Сохр.",
    "Save As": "Сохр. как",
    "Save As...": "Сохр. как...",
    "Current build: ": "Текущий билд: ",

    # Bottom Bar Controls
    "Options": "Опции",
    "About": "Инфо",
    "Update Ready": "Обновление готово",
    "Check for Update": "Проверить обновления",

    # Left Sidebar Tabs
    "Tree": "Дерево",
    "Skills": "Умения",
    "Items": "Предметы",
    "Calcs": "Расчеты",
    "Configuration": "Конфиг",
    "Config": "Конфиг",
    "Notes": "Заметки",
    "Import/Export Build": "Импорт/Экспорт",
    "Party": "Группа",
    "Compare": "Сравнить",

    # Tree Tab Controls
    "Compare:": "Сравнить:",
    "Reset Tree": "Сброс",
    "Passive Skill Tree": "Дерево пассивных умений",
    "Points Used": "Потрачено очков",
    "Points: ": "Очки: ",
    "Ascendancy Points Used": "Очков восхождения",
    "Search Tree": "Поиск по дереву",
    "Show Node Power": "Сила нодов",
    "Game Version: ": "Версия игры: ",
    "Warning: resetting your passive tree cannot be undone.": "Внимание: сброс дерева пассивок нельзя отменить.",

    # Skills Tab & Controls
    "Main Skill:": "Главное умение:",
    "Main Skill: ": "Главное умение: ",
    "Manage Spectres...": "Призраки...",
    "Manage Beasts...": "Звери...",
    "Socket Groups": "Группы гнезд",
    "Enabled": "Включено",
    "Include in Full DPS": "Включить в полный ДПС",
    "Gem Level": "Уровень камня",
    "Gem Quality": "Качество камня",
    "Skill Gems": "Камни умений",

    # Left Sidebar Compact Stats (strictly <= 170px width)
    "Average Damage: ": "Ср. урон: ",
    "Effective Crit Chance: ": "Эфф. крит: ",
    "Crit Multiplier: ": "Множ. крита: ",
    "Effective Hit Pool: ": "Эфф. HP (EHP): ",
    "Maximum Hit Taken: ": "Макс. удар: ",
    "Fire Resistance: ": "Сопр. огню: ",
    "Cold Resistance: ": "Сопр. холоду: ",
    "Lightning Resistance: ": "Сопр. молнии: ",
    "Chaos Resistance: ": "Сопр. хаосу: ",
    "Phys. Damage Reduction: ": "Физ. защита: ",
    "Spell Suppression Chance: ": "Подавл. чар: ",
    "Spell Block Chance: ": "Блок чар: ",
    "Block Chance: ": "Блок атак: ",
    "Movement Speed: ": "Скор. бега: ",
    "Attack Rate: ": "Скор. атаки: ",
    "Cast Rate: ": "Скор. чар: ",
    "Hit Chance: ": "Шанс попад.: ",
    "Total DPS: ": "Общий ДПС: ",
    "Hit DPS: ": "ДПС удара: ",
    "Dot DPS: ": "ДПС DOT: ",
    "Damage over Time: ": "Урон со врем.: ",
    "Bleed DPS: ": "ДПС кровот.: ",
    "Ignite DPS: ": "ДПС поджога: ",
    "Poison DPS: ": "ДПС яда: ",
    "Life: ": "Здоровье: ",
    "Mana: ": "Мана: ",
    "Energy Shield: ": "Эн. щит: ",
    "Ward: ": "Оберег: ",
    "Armour: ": "Броня: ",
    "Evasion: ": "Уклонение: ",
    "Evasion Rating: ": "Уклонение: ",
    "Spirit: ": "Дух: ",
    "MH Crit Multiplier: ": "Множ. крита осн.: ",
    "OH Crit Multiplier: ": "Множ. крита втор.: ",
    "MH Hit Chance: ": "Шанс попад. осн.: ",
    "OH Hit Chance: ": "Шанс попад. втор.: ",
    "MH Attack Rate: ": "Скор. атаки осн.: ",
    "OH Attack Rate: ": "Скор. атаки втор.: ",

    # Non-colon Stat Names
    "Average Damage": "Средний урон",
    "Effective Crit Chance": "Эффективный крит",
    "Crit Multiplier": "Множитель крита",
    "Effective Hit Pool": "Эффективный запас здоровья (EHP)",
    "Fire Resistance": "Сопротивление огню",
    "Cold Resistance": "Сопротивление холоду",
    "Lightning Resistance": "Сопротивление молнии",
    "Chaos Resistance": "Сопротивление хаосу",
    "Phys. Damage Reduction": "Снижение физ. урона",
    "Spell Suppression Chance": "Шанс подавления чар",
    "Total DPS": "Общий ДПС",
    "Hit DPS": "ДПС удара",
    "Damage over Time": "Урон со временем",
    "Life": "Здоровье",
    "Mana": "Мана",
    "Energy Shield": "Энергетический щит",
    "Ward": "Оберег",
    "Armour": "Броня",
    "Evasion": "Уклонение",
    "Spirit": "Дух",
    "Strength": "Сила",
    "Dexterity": "Ловкость",
    "Intelligence": "Интеллект",
    "Req Str": "Треб. силы",
    "Req Dex": "Треб. ловкости",
    "Req Int": "Треб. инт.",

    # Classes (PoE 1 & PoE 2)
    "Ranger": "Охотница",
    "Warrior": "Воин",
    "Monk": "Монах",
    "Mercenary": "Наемник",
    "Sorceress": "Заклинательница",
    "Witch": "Ведьма",
    "Duelist": "Дуэлянт",
    "Shadow": "Бандит",
    "Marauder": "Дикарь",
    "Templar": "Жрец",
    "Scion": "Дворянка",
    "Druid": "Друид",
    "Huntress": "Копейщица",

    # Ascendancies (PoE 1)
    "Juggernaut": "Покоритель",
    "Berserker": "Берсерк",
    "Chieftain": "Вождь",
    "Raider": "Налетчица",
    "Deadeye": "Снайпер",
    "Pathfinder": "Следопыт",
    "Occultist": "Оккультистка",
    "Elementalist": "Элементалист",
    "Necromancer": "Некромант",
    "Slayer": "Рубака",
    "Gladiator": "Гладиатор",
    "Champion": "Чемпион",
    "Assassin": "Убийца",
    "Saboteur": "Диверсант",
    "Trickster": "Плут",
    "Inquisitor": "Инквизитор",
    "Hierophant": "Иерофант",
    "Guardian": "Защитник",
    "Ascendant": "Вознесшаяся",

    # Ascendancies (PoE 2)
    "Titan": "Титан",
    "Warbringer": "Вестник войны",
    "Smith of Kitava": "Кузнец Китавы",
    "Stormweaver": "Ткач бурь",
    "Chronomancer": "Хрономант",
    "Disciple of Varashta": "Ученица Варашты",
    "Blood Mage": "Маг крови",
    "Infernalist": "Инферналист",
    "Lich": "Лич",
    "Abyssal Lich": "Лич Бездны",
    "Amazon": "Амазонка",
    "Spirit Walker": "Ходящая среди духов",
    "Ritualist": "Ритуалист",
    "Tactician": "Тактик",
    "Witchhunter": "Охотник на ведьм",
    "Gemling Legionnaire": "Легионер каменитов",
    "Martial Artist": "Мастер боевых искусств",
    "Invoker": "Заклинатель стихий",
    "Acolyte of Chayula": "Послушник Чаюлы",
    "Oracle": "Оракул",
    "Shaman": "Шаман",

    # Common UI Actions
    "New": "Создать",
    "Import": "Импорт",
    "Export": "Экспорт",
    "Copy": "Копировать",
    "Paste": "Вставить",
    "Delete": "Удалить",
    "Manage": "Управление",
    "Search": "Поиск",
    "Sort": "Сортировка",
    "Filter": "Фильтр",
    "Reset": "Сброс",
    "Default": "По умолчанию",
    "Close": "Закрыть",
    "Cancel": "Отмена",
    "Done": "Готово",
    "Apply": "Применить",
    "Edit": "Редактировать",
    "Create": "Создать",
    "Clear": "Очистить",
    "Update": "Обновить",

    # Items Tab
    "Equipped Items": "Экипированные предметы",
    "Craft Item...": "Создать предмет...",
    "Add to build": "Добавить в билд",
    "Item Sets": "Наборы предметов",
    "All Items": "Все предметы",
    "Weapon 1": "Оружие 1",
    "Weapon 2": "Оружие 2",
    "Helmet": "Шлем",
    "Body Armour": "Доспех",
    "Gloves": "Перчатки",
    "Boots": "Сапоги",
    "Amulet": "Амулет",
    "Ring 1": "Кольцо 1",
    "Ring 2": "Кольцо 2",
    "Belt": "Пояс",

    # Branding
    "Guides & Builds: arpg-life.ru": "Гайды и билды: arpg-life.ru",
    "ARPG-Life Edition": "ARPG-Life Edition (Русская версия)",
    "Language": "Язык",
    "Russian (ARPG-Life.ru)": "Русский (ARPG-Life.ru)",
    "English": "English",
}

def generate_ui_dictionary():
    out_path = os.path.join(DICT_DIR, "ui_ru.lua")
    write_lua_table(out_path, "ui_ru", UI_TRANSLATIONS)

# ------------------------------------------------------------------------------
# 2. Affix Templates (Pattern-based numerical translations)
# ------------------------------------------------------------------------------
def generate_affix_templates():
    templates = {}

    def add_pair(en_tmpl, ru_tmpl):
        if not en_tmpl or not ru_tmpl:
            return
        en_tmpl = en_tmpl.strip()
        ru_tmpl = ru_tmpl.strip()

        # Count {value} or numbers
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
            templates[pat_en] = pat_ru

    # 1. Load from poe1-affix-templates.json
    t1 = load_json(os.path.join(AFFIX_DATA_DIR, "poe1-affix-templates.json")) or {}
    for en, ru in t1.items():
        add_pair(en, ru)

    # 2. Load from poe1_scraped_affixes.json
    t2 = load_json(os.path.join(POE_TOOLTIP_DIR, "poe1_scraped_affixes.json")) or []
    for item in t2:
        if isinstance(item, dict):
            add_pair(item.get("templateEn"), item.get("template"))

    out_path = os.path.join(DICT_DIR, "affix_templates.lua")
    write_lua_table(out_path, "affix_templates", templates)

# ------------------------------------------------------------------------------
# 3. PoE 1 Dictionary
# ------------------------------------------------------------------------------
def generate_poe1_dictionary():
    dict1 = {}

    # 1. Gems
    gems = load_json(os.path.join(POE_DATA_DIR, "poe1_gems_enriched.json")) or []
    for g in gems:
        en = g.get("englishName")
        ru = g.get("nameRu")
        if en and ru:
            dict1[en.strip()] = ru.strip()

    # 2. Uniques
    uniques = load_json(os.path.join(POE_TOOLTIP_DIR, "poe1_unique_items.json")) or []
    items_list = uniques.values() if isinstance(uniques, dict) else uniques
    for item in items_list:
        if isinstance(item, dict):
            en = item.get("englishName")
            ru = item.get("nameRu")
            if en and ru:
                dict1[en.strip()] = ru.strip()

    # 3. Bases
    bases = load_json(os.path.join(POE_DATA_DIR, "poe1_base_items.json")) or []
    for b in bases:
        en = b.get("englishName")
        ru = b.get("nameRu")
        if en and ru:
            dict1[en.strip()] = ru.strip()

    # 4. Passive Tree Nodes & Tree Stats
    tree_raw = load_json(os.path.join(POE_TREE_DIR, "Skill Trees", "3.29.0", "raw.json")) or {}
    tree_loc = load_json(os.path.join(POE_TREE_DIR, "Skill Trees", "3.29.0", "localization-ru.json")) or {}
    raw_nodes = tree_raw.get("nodes", {})
    loc_nodes = tree_loc.get("nodes", {})
    for node_id, r_node in raw_nodes.items():
        if node_id in loc_nodes:
            l_node = loc_nodes[node_id]
            en_name = r_node.get("name")
            ru_name = l_node.get("name")
            if en_name and ru_name:
                dict1[en_name.strip()] = ru_name.strip()

            r_stats = r_node.get("stats", [])
            l_stats = l_node.get("stats", [])
            if len(r_stats) == len(l_stats):
                for s_en, s_ru in zip(r_stats, l_stats):
                    if s_en and s_ru:
                        dict1[s_en.strip()] = s_ru.strip()

    out_path = os.path.join(DICT_DIR, "poe1_ru.lua")
    write_lua_table(out_path, "poe1_ru", dict1)

# ------------------------------------------------------------------------------
# 4. PoE 2 Dictionary
# ------------------------------------------------------------------------------
def clean_tags(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\[[^\]|]+\|([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    return text.strip()

def generate_poe2_dictionary():
    dict2 = {}

    # 1. Gems
    gems2 = load_json(os.path.join(POE_DATA_DIR, "poe2_gems_enriched.json")) or []
    for g in gems2:
        en = g.get("englishName")
        ru = g.get("nameRu")
        if en and ru:
            dict2[en.strip()] = ru.strip()

    # 2. Uniques
    uniques2 = load_json(os.path.join(POE_DATA_DIR, "poe2_unique_items.json")) or []
    items_list2 = uniques2.values() if isinstance(uniques2, dict) else uniques2
    for item in items_list2:
        if isinstance(item, dict):
            en = item.get("englishName")
            ru = item.get("nameRu")
            if en and ru:
                dict2[en.strip()] = ru.strip()

    # 3. Bases
    bases2 = load_json(os.path.join(POE_DATA_DIR, "poe2_base_items.json")) or []
    for b in bases2:
        en = b.get("englishName")
        ru = b.get("nameRu")
        if en and ru:
            dict2[en.strip()] = ru.strip()

    # 4. Passive Tree Custom Translations (Names and Stats)
    tree2 = load_json(os.path.join(POE2_TREE_DIR, "src", "tree", "custom_translations.json")) or {}
    for en, ru in tree2.get("names", {}).items():
        if en and ru:
            dict2[clean_tags(en)] = clean_tags(ru)

    for en, ru in tree2.get("stats", {}).items():
        if en and ru:
            dict2[clean_tags(en)] = clean_tags(ru)

    out_path = os.path.join(DICT_DIR, "poe2_ru.lua")
    write_lua_table(out_path, "poe2_ru", dict2)

if __name__ == "__main__":
    print("=== Generating Translation Dictionaries for PoB ARPG-Life ===")
    generate_ui_dictionary()
    generate_affix_templates()
    generate_poe1_dictionary()
    generate_poe2_dictionary()
    print("=== Dictionaries generated successfully ===")
