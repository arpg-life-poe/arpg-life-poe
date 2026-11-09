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
    return nil
end

-- Extract all consecutive leading PoB color escape codes: ^0..^9, ^xRRGGBB
local function extractLeadingColor(str)
    local len = #str
    local pos = 1
    while pos <= len do
        if str:byte(pos) == 94 then -- '^'
            local b2 = str:byte(pos + 1)
            if b2 and b2 >= 48 and b2 <= 57 then -- '0'..'9'
                pos = pos + 2
            elseif b2 and (b2 == 120 or b2 == 88) and pos + 7 <= len and str:sub(pos + 2, pos + 7):find("^%x%x%x%x%x%x") then -- 'x' or 'X' + 6 hex
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

-- Numerical template matching for complex item affixes ({0}, {1}, etc.)
local function tryMatchTemplate(text)
    if not text:find("%d") then
        return nil
    end

    local nums = {}
    local idx = 0

    local pattern = text:lower()
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

-- Multi-step translation pipeline forward declaration
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

    -- 2. Trailing colon or punctuation ("Label:" -> "Метка:")
    local base, punct = token:match("^(.-)([:%.%s]+)$")
    if base and #base > 0 and punct then
        local tBase = lookupToken(base)
        if tBase then
            return tBase .. punct
        end
    end

    -- 3. Stat comparison lines in tooltips:
    -- e.g. "+12.5% Total DPS (+12.5%) ^8[+12.5% per point]" or "+15 Life ^8[+15 per point]"
    local num, after = token:match("^([%+%-]?%d+%.?%d*%%?)%s+(.+)$")
    if num and after then
        local mainPart, perPt = after:match("^(.-)%s*(%^8%[[^%]]+ per point%]%s*)$")
        if perPt then
            after = mainPart
            perPt = perPt:gsub("per point", "за очко")
        end
        local statPart, deltaPct = after:match("^(.-)%s*(%(%s*[%+%-]?%d+%.?%d*%%%s*%))$")
        if deltaPct then
            after = statPart
        end
        local tStat = lookupToken(after)
        if not tStat and i18n.uiPatterns then
            for _, pat in ipairs(i18n.uiPatterns) do
                local matched, count = after:gsub(pat.pattern, pat.repl)
                if count > 0 then
                    tStat = matched
                    break
                end
            end
        end
        if tStat then
            return num .. " " .. tStat .. (deltaPct and (" " .. deltaPct) or "") .. (perPt and (" " .. perPt) or "")
        end
    end

    -- 4. "Key: Value" pair where Key and Value are translated individually
    -- e.g. "Socketed in: Weapon 1" or "Main Skill: Fireball"
    local key, sep, val = token:match("^(.-)(:%s+)(.+)$")
    if key and #key > 0 and val and #val > 0 then
        local tKey = lookupToken(key)
        if tKey then
            local tVal = translateLine(val)
            return tKey .. sep .. tVal
        end
    end

    -- 5. "Text (Subtext)" where Text and Subtext are translated individually
    -- e.g. "Unnamed build (Ranger)" or "Level: 20 (Max)"
    local mainText, sub = token:match("^(.-)%s+%((.-)%)$")
    if mainText and sub and #mainText > 0 and #sub > 0 then
        local tMain = translateToken(mainText)
        local tSub = translateToken(sub)
        if tMain ~= mainText or tSub ~= sub then
            return tMain .. " (" .. tSub .. ")"
        end
    end

    -- 6. UI regex patterns (tooltips, requirements, counters)
    if i18n.uiPatterns then
        for _, pat in ipairs(i18n.uiPatterns) do
            local matched, count = token:gsub(pat.pattern, pat.repl)
            if count > 0 then
                return matched
            end
        end
    end

    -- 7. Numerical affix templates
    local templated = tryMatchTemplate(token)
    if templated then
        return templated
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
end

return i18n
