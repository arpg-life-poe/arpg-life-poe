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
# 1. UI Dictionary
# ------------------------------------------------------------------------------
UI_TRANSLATIONS = {
    # Main Navigation Tabs
    "Tree": "Дерево",
    "Skills": "Умения",
    "Items": "Предметы",
    "Calcs": "Расчеты",
    "Configuration": "Конфигурация",
    "Notes": "Заметки",
    "Import/Export Build": "Импорт/Экспорт",
    "Options": "Настройки",
    "About": "О программе",
    "Party": "Группа",

    # Common Buttons & Actions
    "Back": "Назад",
    "Save": "Сохранить",
    "Save As...": "Сохранить как...",
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
    "Check for Update": "Проверить обновления",

    # Character Attributes & Stats
    "Level": "Уровень",
    "Class": "Класс",
    "Ascendancy": "Восхождение",
    "Bandit": "Бандит",
    "Pantheon": "Пантеон",
    "Major God": "Старший бог",
    "Minor God": "Младший бог",

    # Left Sidebar Main Stats
    "Life": "Здоровье",
    "Mana": "Мана",
    "Spirit": "Дух",
    "Energy Shield": "Энергетический щит",
    "Ward": "Оберег",
    "Armour": "Броня",
    "Evasion": "Уклонение",
    "Evasion Rating": "Показатель уклонения",

    # Resistances
    "Fire Resistance": "Сопротивление огню",
    "Cold Resistance": "Сопротивление холоду",
    "Lightning Resistance": "Сопротивление молнии",
    "Chaos Resistance": "Сопротивление хаосу",
    "Fire": "Огонь",
    "Cold": "Холод",
    "Lightning": "Молния",
    "Chaos": "Хаос",
    "Physical": "Физический",

    # Offence Stats
    "Total DPS": "Общий ДПС",
    "Effective DPS": "Эффективный ДПС",
    "Hit DPS": "ДПС удара",
    "Damage over Time": "Урон со временем",
    "Dot DPS": "ДПС урона со временем",
    "Bleed DPS": "ДПС кровотечения",
    "Ignite DPS": "ДПС поджога",
    "Poison DPS": "ДПС яда",
    "Hit Chance": "Шанс попадания",
    "Attack Rate": "Скорость атаки",
    "Cast Rate": "Скорость сотворения",
    "Crit Chance": "Шанс крит. удара",
    "Crit Multiplier": "Множитель крит. удара",
    "Attack Speed": "Скорость атаки",
    "Cast Speed": "Скорость сотворения",

    # Defence Stats
    "Effective Hit Pool": "Эффективный запас здоровья (EHP)",
    "Maximum Hit Taken": "Макс. выдерживаемый удар",
    "Block Chance": "Шанс блока",
    "Spell Block Chance": "Шанс блока чар",
    "Spell Suppression Chance": "Шанс подавления чар",
    "Physical Damage Reduction": "Снижение физ. урона",
    "Movement Speed": "Скорость передвижения",

    # Core Attributes
    "Strength": "Сила",
    "Dexterity": "Ловкость",
    "Intelligence": "Интеллект",
    "Req Str": "Треб. силы",
    "Req Dex": "Треб. ловкости",
    "Req Int": "Треб. инт.",

    # Tree Tab
    "Passive Skill Tree": "Дерево пассивных умений",
    "Points Used": "Потрачено очков",
    "Ascendancy Points Used": "Очков восхождения",
    "Search Tree": "Поиск по дереву",
    "Reset Tree": "Сбросить дерево",
    "Show Node Power": "Сила нодов",

    # Skills Tab
    "Socket Groups": "Группы гнезд",
    "Enabled": "Включено",
    "Include in Full DPS": "Включить в полный ДПС",
    "Gem Level": "Уровень камня",
    "Gem Quality": "Качество камня",
    "Skill Gems": "Камни умений",

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

    # Branding & Custom UI
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
# 2. PoE 1 Dictionary
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
        if not isinstance(item, dict):
            continue
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

    # 4. Passive Tree Nodes
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

    out_path = os.path.join(DICT_DIR, "poe1_ru.lua")
    write_lua_table(out_path, "poe1_ru", dict1)

# ------------------------------------------------------------------------------
# 3. PoE 2 Dictionary
# ------------------------------------------------------------------------------
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
        if not isinstance(item, dict):
            continue
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

    # 4. Passive Tree Custom Translations
    tree2 = load_json(os.path.join(POE2_TREE_DIR, "src", "tree", "custom_translations.json")) or {}
    names2 = tree2.get("names", {})
    for en, ru in names2.items():
        if en and ru:
            dict2[en.strip()] = ru.strip()

    out_path = os.path.join(DICT_DIR, "poe2_ru.lua")
    write_lua_table(out_path, "poe2_ru", dict2)

if __name__ == "__main__":
    print("=== Generating Translation Dictionaries for PoB ARPG-Life ===")
    generate_ui_dictionary()
    generate_poe1_dictionary()
    generate_poe2_dictionary()
    print("=== Dictionaries generated successfully ===")
