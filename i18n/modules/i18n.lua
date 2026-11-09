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
i18n.memo = {}

-- Load dictionaries safely
function i18n.init(gameVersion)
    local uiOk, uiTable = pcall(require, "i18n.dictionaries.ui_ru")
    if uiOk and type(uiTable) == "table" then
        i18n.uiDict = uiTable
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
    local trans = i18n.uiDict[token]
    if trans then
        return trans
    end
    trans = i18n.gameDict[token]
    if trans then
        return trans
    end
    return nil
end

-- Translate single line handling color escapes and colon suffix
local function translateLine(line)
    if not line or #line == 0 then
        return line
    end

    local prefix = ""
    local rest = line

    -- Check for leading color code: ^0..^9 or ^xRRGGBB
    if rest:sub(1, 1) == "^" then
        local second = rest:sub(2, 2)
        if second >= "0" and second <= "9" then
            prefix = rest:sub(1, 2)
            rest = rest:sub(3)
        elseif second == "x" and #rest >= 8 then
            prefix = rest:sub(1, 8)
            rest = rest:sub(9)
        end
    end

    -- Check for trailing colon (common in UI labels like "Life:" or "Total DPS:")
    local suffix = ""
    if rest:sub(-1) == ":" then
        suffix = ":"
        rest = rest:sub(1, -2)
    end

    -- Direct dictionary match
    local translated = lookupToken(rest)
    if translated then
        return prefix .. translated .. suffix
    end

    -- If no exact match, return original line
    return line
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
