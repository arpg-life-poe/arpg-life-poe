-- ==============================================================================
-- Path of Building — ARPG-Life Edition
-- Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
-- Project: https://arpg-life.ru
--
-- i18n Translation & Display Localization Engine
-- ==============================================================================

local i18n = {}

i18n.currentLanguage = "ru"
i18n.uiDict = {}
i18n.gameDict = {}
i18n.uiPatterns = {}
i18n.templates = {}
i18n.memo = {}
i18n.isHooked = false

-- Load dictionaries safely
function i18n.init(gameVersion)
	local uiOk, uiTable = pcall(require, "i18n.dictionaries.ui_ru")
	if uiOk and type(uiTable) == "table" then
		i18n.uiDict = uiTable
		i18n.uiPatterns = uiTable.patterns or {}
	end

	local tmplOk, tmplTable = pcall(require, "i18n.dictionaries.affix_templates")
	if tmplOk and type(tmplTable) == "table" then
		i18n.templates = tmplTable
	end

	local gameDictName = (gameVersion == "poe2" or gameVersion == 2) and "i18n.dictionaries.poe2_ru" or "i18n.dictionaries.poe1_ru"
	local gameOk, gameTable = pcall(require, gameDictName)
	if gameOk and type(gameTable) == "table" then
		i18n.gameDict = gameTable
	end

	i18n.memo = {}
end

function i18n.setLanguage(lang)
	if lang == "en" or lang == "ru" then
		i18n.currentLanguage = lang
		i18n.memo = {}
	end
end

function i18n.getLanguage()
	return i18n.currentLanguage
end

-- Strip all embedded PoB color formatting escapes: ^xRRGGBB, ^x..., ^0..^9
local function stripAllColors(str)
	if not str or not str:find("%^") then
		return str
	end
	return str:gsub("%^[xX]%x%x%x%x%x%x", ""):gsub("%^[xX]%x+", ""):gsub("%^%d", "")
end

-- Extract consecutive leading PoB color escape codes: ^0..^9, ^xRRGGBB
local function extractLeadingColor(str)
	local len = #str
	local pos = 1
	while pos <= len do
		if str:byte(pos) == 94 then -- '^'
			local b2 = str:byte(pos + 1)
			if b2 and b2 >= 48 and b2 <= 57 then -- '0'..'9'
				pos = pos + 2
			elseif b2 and (b2 == 120 or b2 == 88) and pos + 7 <= len and str:sub(pos + 2, pos + 7):find("^%x%x%x%x%x%x") then
				pos = pos + 8
			else
				break
			end
		else
			break
		end
	end
	if pos > 1 then
		return str:sub(1, pos - 1), str:sub(pos)
	else
		return "", str
	end
end

-- Core single-token translation lookup
local function lookupToken(token)
	if not token or #token == 0 or token == "patterns" then
		return nil
	end
	local trans = i18n.uiDict[token]
	if trans and type(trans) == "string" then
		return trans
	end
	trans = i18n.gameDict[token]
	if trans and type(trans) == "string" then
		return trans
	end
	-- Check with trailing colon stripped if token has no colon
	local transColon = i18n.uiDict[token .. ":"]
	if transColon and type(transColon) == "string" then
		return transColon:gsub("[:%s]+$", "")
	end
	return nil
end

-- Numerical template matching for complex item affixes ({0}, {1}, etc.)
local function tryMatchTemplate(text)
	local clean = stripAllColors(text)
	if not clean:find("%d") then
		return nil
	end

	local nums = {}
	local idx = 0

	local pattern = clean:lower()
	pattern = pattern:gsub("([%+%-]?)(%d+%.?%d*)", function(sign, num)
		local ph = (sign or "") .. "{" .. idx .. "}"
		nums[idx] = num
		idx = idx + 1
		return ph
	end)

	local trans = i18n.templates[pattern]
	if not trans then
		local trimmed = pattern:match("^%s*(.-)%s*$")
		if trimmed and trimmed ~= pattern then
			trans = i18n.templates[trimmed]
		end
	end

	if trans then
		local result = trans:gsub("{(%d+)}", function(n)
			local numIdx = tonumber(n)
			return nums[numIdx] or ("{" .. n .. "}")
		end)
		return result
	end

	return nil
end

-- Forward declaration
local translateLine

local function translateToken(token)
	if not token or #token == 0 then
		return token
	end

	-- 1. Exact dictionary match (uiDict, then gameDict)
	local direct = lookupToken(token)
	if direct then
		return direct
	end

	-- 2. Strip colors if token has embedded codes
	local cleanToken = stripAllColors(token)
	if cleanToken ~= token and #cleanToken > 0 then
		local directClean = lookupToken(cleanToken)
		if directClean then
			return directClean
		end
	end

	-- 3. Unsupported mod suffix: " ^8(Not supported in PoB yet)"
	local unsuppSuffix = nil
	if token:find("%(Not supported in PoB yet%)") then
		token = token:gsub("%s*%^?8?%(Not supported in PoB yet%)", "")
		cleanToken = stripAllColors(token)
		unsuppSuffix = " ^8(Не поддерживается в PoB)"
	end

	-- 4. Item / Passive Node difference headers
	local eqSlot = token:match("^Equipping this item in (.+) will give you:$")
	if eqSlot then
		local tSlot = lookupToken(eqSlot) or eqSlot
		local res = "Экипировка этого предмета в " .. tSlot .. " даст вам:"
		return unsuppSuffix and (res .. unsuppSuffix) or res
	end
	local remSlot = token:match("^Removing this item from (.+) will give you:$")
	if remSlot then
		local tSlot = lookupToken(remSlot) or remSlot
		local res = "Снятие этого предмета из " .. tSlot .. " даст вам:"
		return unsuppSuffix and (res .. unsuppSuffix) or res
	end
	if token:match("^Equipping this item will give you:$") then
		return "Экипировка этого предмета даст вам:"
	end
	if token:match("^Removing this item will give you:$") then
		return "Снятие этого предмета даст вам:"
	end

	-- 5. Requirements line (e.g. "Requires Level 68, 155 Str, 120 Dex" with embedded colors)
	if token:find("Requires") or cleanToken:find("Requires") then
		local reqTrans = token:gsub("Requires", "Требуется"):gsub("Level", "Уровень"):gsub("Str", "Силы"):gsub("Dex", "Ловк."):gsub("Int", "Инт."):gsub("Omni", "Всезнания")
		if reqTrans ~= token then
			return unsuppSuffix and (reqTrans .. unsuppSuffix) or reqTrans
		end
	end

	-- 6. Trailing colon or punctuation ("Label:" -> "Метка:")
	local base, punct = token:match("^(.-)([:%.%s]+)$")
	if base and #base > 0 and punct then
		local tBase = lookupToken(base) or lookupToken(stripAllColors(base))
		if tBase then
			local res = tBase .. punct
			return unsuppSuffix and (res .. unsuppSuffix) or res
		end
	end

	-- 7. Resource value: "6 Mana", "100 Spirit", "50 Life"
	local numRes, resName = token:match("^(%d+%.?%d*)%s+(%a.*)$")
	if numRes and resName then
		local tRes = lookupToken(resName) or lookupToken(stripAllColors(resName))
		if tRes then
			local res = numRes .. " " .. tRes
			return unsuppSuffix and (res .. unsuppSuffix) or res
		end
	end

	-- 8. Stat comparison lines (with optional units: %, s, m)
	-- e.g. "+12.5% Total DPS (+12.5%) ^8[+12.5% per point]", "+0.3s Mine Throwing Time", "+2m AoE Radius"
	local num, unit, after = token:match("^([%+%-]?%d+[%d%,]*%.?%d*)([sm%%]?%s+)(.+)$")
	if num and unit and after then
		local mainPart, perPt = after:match("^(.-)%s*(%^8%[[^%]]+ per point%]%s*)$")
		if perPt then
			after = mainPart
			perPt = perPt:gsub("per point", "за очко")
		end
		local statPart, deltaPct = after:match("^(.-)%s*(%(%s*[%+%-]?%d+[%d%,]*%.?%d*%%%s*%))$")
		if deltaPct then
			after = statPart
		end
		local cleanAfter = stripAllColors(after)
		local tStat = lookupToken(after) or lookupToken(cleanAfter)
		if not tStat and i18n.uiPatterns then
			for _, pat in ipairs(i18n.uiPatterns) do
				local matched, count = after:gsub(pat.pattern, pat.repl)
				if count > 0 then
					tStat = matched
					break
				end
				if cleanAfter ~= after then
					matched, count = cleanAfter:gsub(pat.pattern, pat.repl)
					if count > 0 then
						tStat = matched
						break
					end
				end
			end
		end
		if tStat then
			local unitRu = unit:gsub("s%s+", " сек "):gsub("m%s+", "м ")
			local res = num .. unitRu .. tStat .. (deltaPct and (" " .. deltaPct) or "") .. (perPt and (" " .. perPt) or "")
			return unsuppSuffix and (res .. unsuppSuffix) or res
		end
	end

	-- 9. "Key: Value" pair where Key and Value are translated individually
	-- e.g. "Socketed in: Weapon 1", "Attacks per Second: 1.30", "Weapon Range: 1.1 metres"
	local key, sep, val = token:match("^(.-)(:%s+)(.+)$")
	if key and #key > 0 and val and #val > 0 then
		local tKey = lookupToken(key) or lookupToken(stripAllColors(key))
		if tKey then
			val = val:gsub("metres", "метров"):gsub("Instant", "Мгновенно"):gsub("sec", "сек")
			local tVal = translateLine(val)
			local res = tKey .. sep .. tVal
			return unsuppSuffix and (res .. unsuppSuffix) or res
		end
	end

	-- 10. "Text (Subtext)" where Text and Subtext are translated individually
	-- e.g. "Unnamed build (Ranger)" or "Level: 20 (Max)"
	local mainText, sub = token:match("^(.-)%s+%((.-)%)$")
	if mainText and sub and #mainText > 0 and #sub > 0 then
		local tMain = translateToken(mainText)
		local tSub = translateToken(sub)
		if tMain ~= mainText or tSub ~= sub then
			local res = tMain .. " (" .. tSub .. ")"
			return unsuppSuffix and (res .. unsuppSuffix) or res
		end
	end

	-- 11. Unique Name, Base Name pair: "Actum, Butcher Axe" -> "Делатель, Топор мясника"
	if token:find(", ", 1, true) and not token:find("%d") then
		local part1, part2 = token:match("^(.-),%s+(.+)$")
		if part1 and part2 and not part2:find(",") then
			local tPart1 = lookupToken(part1) or i18n.gameDict[part1] or part1
			local tPart2 = lookupToken(part2) or i18n.gameDict[part2] or lookupToken(stripAllColors(part2))
			if tPart2 and (tPart1 ~= part1 or tPart2 ~= part2) then
				local res = tPart1 .. ", " .. tPart2
				return unsuppSuffix and (res .. unsuppSuffix) or res
			end
		end
	end

	-- 12. Comma-separated tag list: "Mine, Spell, Projectile, Fire, AoE, Aura, Nova"
	if token:find(", ", 1, true) and not token:find("%d") then
		local parts = {}
		local anyTranslated = false
		local count = 0
		for part in token:gmatch("[^,]+") do
			local trimmed = part:match("^%s*(.-)%s*$")
			if #trimmed > 0 then
				count = count + 1
				local t = lookupToken(trimmed) or lookupToken(stripAllColors(trimmed))
				if t then
					table.insert(parts, t)
					anyTranslated = true
				else
					table.insert(parts, trimmed)
				end
			end
		end
		if anyTranslated and count > 1 then
			local res = table.concat(parts, ", ")
			return unsuppSuffix and (res .. unsuppSuffix) or res
		end
	end

	-- 13. Range values in tables: "1 to 2" -> "1 - 2"
	local r1, r2 = token:match("^(%d+%.?%d*)%s+to%s+(%d+%.?%d*)$")
	if r1 and r2 then
		local res = r1 .. " - " .. r2
		return unsuppSuffix and (res .. unsuppSuffix) or res
	end

	-- 14. UI regex patterns (tooltips, requirements, counters)
	if i18n.uiPatterns then
		for _, pat in ipairs(i18n.uiPatterns) do
			local matched, count = token:gsub(pat.pattern, pat.repl)
			if count > 0 then
				return unsuppSuffix and (matched .. unsuppSuffix) or matched
			end
			if cleanToken ~= token then
				matched, count = cleanToken:gsub(pat.pattern, pat.repl)
				if count > 0 then
					return unsuppSuffix and (matched .. unsuppSuffix) or matched
				end
			end
		end
	end

	-- 15. Numerical affix templates
	local templated = tryMatchTemplate(token) or (cleanToken ~= token and tryMatchTemplate(cleanToken))
	if templated then
		return unsuppSuffix and (templated .. unsuppSuffix) or templated
	end

	if unsuppSuffix then
		return token .. unsuppSuffix
	end

	return token
end

function translateLine(line)
	if not line or #line == 0 then
		return line
	end

	-- Extract leading color codes (e.g. ^7, ^xRRGGBB)
	local colorPrefix, rest = extractLeadingColor(line)
	if #rest == 0 then
		return line
	end

	-- Preserve leading and trailing whitespace
	local leadingSpaces, content, trailingSpaces = rest:match("^(%s*)(.-)(%s*)$")
	if #content == 0 then
		return line
	end

	local translated = translateToken(content)
	return colorPrefix .. leadingSpaces .. translated .. trailingSpaces
end

function i18n.translate(text)
	if i18n.currentLanguage ~= "ru" or not text or type(text) ~= "string" or #text == 0 then
		return text
	end

	local cached = i18n.memo[text]
	if cached ~= nil then
		return cached
	end

	local result
	if text:find("\n", 1, true) then
		-- Multi-line string
		local lines = {}
		for line in text:gmatch("([^\r\n]*)(\r?\n?)") do
			if #line > 0 then
				table.insert(lines, translateLine(line))
			end
		end
		result = table.concat(lines, "\n")
	else
		result = translateLine(text)
	end

	i18n.memo[text] = result
	return result
end

-- Hook into PoB drawing pipeline
function i18n.hookEngine()
	if i18n.isHooked then
		return
	end
	i18n.isHooked = true

	local rawDrawString = _G.DrawString
	local rawDrawStringWidth = _G.DrawStringWidth

	if rawDrawString then
		_G.DrawString = function(left, top, align, height, font, text)
			return rawDrawString(left, top, align, height, font, i18n.translate(text))
		end
	end

	if rawDrawStringWidth then
		_G.DrawStringWidth = function(height, font, text)
			return rawDrawStringWidth(height, font, i18n.translate(text))
		end
	end

	-- Dynamically hook TooltipClass:AddLine if classes table exists
	if _G.common and _G.common.classes and _G.common.classes["Tooltip"] and _G.common.classes["Tooltip"].AddLine then
		local rawAddLine = _G.common.classes["Tooltip"].AddLine
		_G.common.classes["Tooltip"].AddLine = function(self, size, text, ...)
			if text and i18n.translate then
				text = i18n.translate(text)
			end
			return rawAddLine(self, size, text, ...)
		end
	end
end

-- Submodule: updater
i18n.updater = setmetatable({}, {
	__index = function(_, key)
		local ok, mod = pcall(require, "i18n.modules.updater")
		if ok and mod then
			return mod[key]
		end
		return nil
	end
})

return i18n
