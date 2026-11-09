#!/usr/bin/env python3
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Source Patcher for PoB 1 & PoB 2: UI, i18n hooks, and arpg-life.ru branding
# ==============================================================================

import os
import sys
import re

def patch_launch_lua(src_path, game):
    launch_path = os.path.join(src_path, "Launch.lua")
    if not os.path.exists(launch_path):
        print(f"Error: {launch_path} not found")
        return False

    with open(launch_path, "r", encoding="utf-8") as f:
        content = f.read()

    game_title = "PoE 1" if game == "poe1" else "PoE 2"
    brand_name = f'Path of Building ({game_title}) — ARPG-Life.ru Edition'

    # 0. Clean #@ SimpleGraphic directive from line 1 so standard LuaJIT parses it cleanly
    content = re.sub(r'^#@.*?\n', '-- #@ SimpleGraphic\n', content)

    # 1. Update APP_NAME
    content = re.sub(
        r'APP_NAME\s*=\s*"[^"]*"',
        f'APP_NAME = "{brand_name}"',
        content,
        count=1
    )

    # 2. Inject i18n hook
    i18n_inject = f'''
-- [ARPG-Life.ru] i18n Translation Hook
local i18nOk, i18n = pcall(require, "i18n.modules.i18n")
if i18nOk and i18n then
    i18n.init("{game}")
    i18n.hookEngine()
end
'''
    if "-- [ARPG-Life.ru] i18n Translation Hook" not in content:
        content = re.sub(
            r'(SetWindowTitle\(APP_NAME\))',
            r'\1' + i18n_inject,
            content,
            count=1
        )

    # 3. Disable updater logic
    updater_disable = '''
function launch:CheckForUpdate() end
function launch:ApplyUpdate(mode) end
'''
    content += "\n" + updater_disable

    with open(launch_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Successfully patched {launch_path}")
    return True

def patch_main_lua(src_path, game):
    main_path = os.path.join(src_path, "Modules", "Main.lua")
    if not os.path.exists(main_path):
        print(f"Error: {main_path} not found")
        return False

    with open(main_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add arpg-life.ru button in bottom bar
    btn_target = r'(self\.controls\.about\s*=\s*new\("ButtonControl"\)[^\n]+\n[^\n]+\n\s*end\))'
    btn_replacement = r'''\1
	-- [ARPG-Life.ru] Branding Button
	self.controls.arpgLife = new("ButtonControl"):ButtonControl({"BOTTOMLEFT",self.anchorMain,"BOTTOMLEFT"}, {144, 0, 160, 20}, "^xA0C0FFarpg-life.ru", function()
		OpenURL("https://arpg-life.ru")
	end)'''

    if "self.controls.arpgLife" not in content:
        content = re.sub(btn_target, btn_replacement, content, count=1)

    # 2. Hide checkUpdate button
    content = re.sub(
        r'self\.controls\.checkUpdate\.shown\s*=\s*function\(\)[^}]+end',
        'self.controls.checkUpdate.shown = function() return false end',
        content,
        count=1
    )

    # 3. Add language switcher to OpenOptionsPopup
    options_target = r'(drawSectionHeader\("app",\s*"Application options"\))'
    lang_dropdown = r'''\1
	-- [ARPG-Life.ru] Language Switcher
	controls.language = new("DropDownControl"):DropDownControl({ "TOPLEFT", controls.sectionAnchor, "TOPLEFT" }, { currentX + defaultLabelPlacementX, currentY, 180, 18 }, {
		{ label = "Русский (ARPG-Life.ru)", lang = "ru" },
		{ label = "English", lang = "en" },
	}, function(index, value)
		self.language = value.lang
		local i18nOk, i18n = pcall(require, "i18n.modules.i18n")
		if i18nOk and i18n then
			i18n.setLanguage(value.lang)
		end
	end)
	controls.languageLabel = new("LabelControl"):LabelControl({ "RIGHT", controls.language, "LEFT" }, { defaultLabelSpacingPx, 0, 0, 16 }, "^7Язык / Language:")
	controls.language:SelByValue(self.language or "ru", "lang")
	nextRow()'''

    if "controls.language =" not in content:
        content = re.sub(options_target, lang_dropdown, content, count=1)

    # 4. Load language in LoadSettings
    load_target = r'(if node\.attrib\.dpiScaleOverridePercent then)'
    load_inject = r'''if node.attrib.language then
					self.language = node.attrib.language
					local i18nOk, i18n = pcall(require, "i18n.modules.i18n")
					if i18nOk and i18n then
						i18n.setLanguage(self.language)
					end
				end
				\1'''
    if "node.attrib.language" not in content:
        content = re.sub(load_target, load_inject, content, count=1)

    # 5. Save language in SaveSettings
    save_target = r'(t_insert\(setXML,\s*\{\s*elem\s*=\s*"Misc",\s*attrib\s*=\s*\{)'
    save_inject = r'\1\n		language = self.language or "ru",'
    if 'language = self.language' not in content:
        content = re.sub(save_target, save_inject, content, count=1)

    with open(main_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Successfully patched {main_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: patch_sources.py <src_directory> <poe1|poe2>")
        sys.exit(1)

    src_dir = sys.argv[1]
    game_mode = sys.argv[2]
    print(f"=== Patching sources in {src_dir} for {game_mode} ===")
    patch_launch_lua(src_dir, game_mode)
    patch_main_lua(src_dir, game_mode)
    print("=== Patching complete ===")
