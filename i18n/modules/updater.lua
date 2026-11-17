-- ==============================================================================
-- Path of Building — ARPG-Life Edition
-- Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
-- Project: https://arpg-life.ru
--
-- In-app Auto-Updater module: checks remote GitHub upstream-versions.json,
-- notifies the user and provides 1-click dictionary update or full download.
-- ==============================================================================

local updater = {
	checked = false,
	updateAvailable = false,
	remoteData = nil,
	currentVersion = nil,
}

-- Simple non-dependent JSON parser for upstream-versions.json
local function parseSimpleJSON(str)
	if not str or #str == 0 then return nil end
	local res = { poe1 = {}, poe2 = {}, simple_graphic = {} }

	res.updated_at = str:match('"updated_at"%s*:%s*"([^"]+)"')

	-- poe1 section
	local p1 = str:match('"poe1"%s*:%s*{(.-)}')
	if p1 then
		res.poe1.commit = p1:match('"commit"%s*:%s*"([^"]+)"')
		res.poe1.commit_short = p1:match('"commit_short"%s*:%s*"([^"]+)"')
		res.poe1.commit_date = p1:match('"commit_date"%s*:%s*"([^"]+)"')
		res.poe1.latest_release_tag = p1:match('"latest_release_tag"%s*:%s*"([^"]+)"')
		res.poe1.commit_subject = p1:match('"commit_subject"%s*:%s*"([^"]+)"')
	end

	-- poe2 section
	local p2 = str:match('"poe2"%s*:%s*{(.-)}')
	if p2 then
		res.poe2.commit = p2:match('"commit"%s*:%s*"([^"]+)"')
		res.poe2.commit_short = p2:match('"commit_short"%s*:%s*"([^"]+)"')
		res.poe2.commit_date = p2:match('"commit_date"%s*:%s*"([^"]+)"')
		res.poe2.latest_release_tag = p2:match('"latest_release_tag"%s*:%s*"([^"]+)"')
		res.poe2.commit_subject = p2:match('"commit_subject"%s*:%s*"([^"]+)"')
	end

	return res
end

function updater.init(main, launch)
	local ver = nil
	-- 1. Try user-updated version metadata from GetUserPath()
	local userDir = _G.GetUserPath and _G.GetUserPath()
	if userDir then
		local vf = io.open(userDir .. "/i18n/version.lua", "r")
		if vf then
			local content = vf:read("*a")
			vf:close()
			if content and #content > 0 then
				local chunk = loadstring(content)
				if chunk then
					local ok, tbl = pcall(chunk)
					if ok and type(tbl) == "table" then
						ver = tbl
					end
				end
			end
		end
	end

	-- 2. Fall back to packaged i18n/version.lua
	if not ver then
		local verStatus, verTbl = pcall(require, "i18n.version")
		if verStatus and type(verTbl) == "table" then
			ver = verTbl
		end
	end

	-- 3. Ensure defaults for all vital fields
	if not ver or type(ver) ~= "table" then
		ver = {}
	end
	ver.version = ver.version or "2.49.3-arpg1"
	ver.buildDate = ver.buildDate or "2026-11-13"
	ver.upstreamCommitPoE1 = ver.upstreamCommitPoE1 or "a69391d"
	ver.upstreamCommitPoE2 = ver.upstreamCommitPoE2 or "601768b"
	ver.upstreamTagPoE1 = ver.upstreamTagPoE1 or "v2.67.2"
	ver.upstreamTagPoE2 = ver.upstreamTagPoE2 or "v2.49.3"
	ver.checkURL = ver.checkURL or "https://raw.githubusercontent.com/arpg-life-poe/arpg-life-poe/main/upstream-versions.json"
	ver.releasesURL = ver.releasesURL or "https://github.com/arpg-life-poe/arpg-life-poe/releases"
	ver.rawDictBaseURL = ver.rawDictBaseURL or "https://raw.githubusercontent.com/arpg-life-poe/arpg-life-poe/main/i18n/dictionaries/"

	updater.currentVersion = ver

	-- Trigger background check on launch
	updater.checkForUpdates(main, launch, false)
end

function updater.isPoE2()
	-- Check if we are running in PoE 2 instance
	local isPoE2 = false
	if main and main.gameVersion then
		isPoE2 = (main.gameVersion == "2.0" or main.gameVersion == "PoE2")
	end
	if not isPoE2 and main and main.tree then
		isPoE2 = (main.tree.subVersion == "poe2" or main.tree.gameVersion == "2.0")
	end
	return isPoE2
end

function updater.checkForUpdates(main, launch, manual)
	if not launch or not launch.DownloadPage then
		if manual and main and main.OpenMessagePopup then
			main:OpenMessagePopup("Обновление", "Функция проверки обновлений недоступна в текущем окружении.")
		end
		return
	end

	local ver = updater.currentVersion
	launch.arpgCheckingUpdate = true

	launch:DownloadPage(ver.checkURL, function(response, errMsg)
		launch.arpgCheckingUpdate = false
		if errMsg or not response or not response.body then
			ConPrintf("ARPG-Life Updater error: %s", errMsg or "No response")
			if manual and main and main.OpenMessagePopup then
				main:OpenMessagePopup("Проверка обновления", "Не удалось связаться с сервером обновлений.\nПроверьте подключение к интернету.")
			end
			return
		end

		local data = parseSimpleJSON(response.body)
		if not data then
			if manual and main and main.OpenMessagePopup then
				main:OpenMessagePopup("Проверка обновления", "Не удалось разобрать данные версии.")
			end
			return
		end

		updater.remoteData = data
		updater.checked = true

		local isPoE2 = updater.isPoE2()
		local remoteGame = isPoE2 and data.poe2 or data.poe1
		local localCommit = isPoE2 and ver.upstreamCommitPoE2 or ver.upstreamCommitPoE1
		local localTag = isPoE2 and ver.upstreamTagPoE2 or ver.upstreamTagPoE1

		local hasUpdate = false
		if remoteGame and remoteGame.commit_short and localCommit and remoteGame.commit_short ~= localCommit then
			hasUpdate = true
		end
		if remoteGame and remoteGame.latest_release_tag and localTag and remoteGame.latest_release_tag ~= localTag then
			hasUpdate = true
		end
		if data.updated_at and ver.buildDate and data.updated_at > ver.buildDate then
			hasUpdate = true
		end

		if hasUpdate then
			updater.updateAvailable = true
			launch.arpgUpdateAvailable = true
			if manual then
				updater.showPopup(main, launch)
			end
		else
			updater.updateAvailable = false
			launch.arpgUpdateAvailable = false
			if manual and main and main.OpenMessagePopup then
				main:OpenMessagePopup("Обновление ARPG-Life", "^7У вас установлена самая актуальная версия!\n^8Дата базы: " .. (ver.buildDate or "актуально"))
			end
		end
	end)
end

function updater.showPopup(main, launch)
	if not main or not main.OpenConfirmPopup then return end

	local ver = updater.currentVersion or {}
	local data = updater.remoteData or {}
	local isPoE2 = updater.isPoE2()
	local remoteGame = isPoE2 and (data.poe2 or {}) or (data.poe1 or {})
	local gameName = isPoE2 and "PoE 2" or "PoE 1"

	local currentTag = isPoE2 and ver.upstreamTagPoE2 or ver.upstreamTagPoE1
	local remoteTag = remoteGame.latest_release_tag or "Новая версия"
	local remoteCommit = remoteGame.commit_short or ""
	local commitDesc = remoteGame.commit_subject or ""
	if #commitDesc > 60 then
		commitDesc = commitDesc:sub(1, 57) .. "..."
	end

	local msg = "^7Доступно обновление для ^xDDAA00Path of Building (" .. gameName .. " — ARPG-Life)^7!\n\n"
	msg = msg .. "^8Текущая версия: ^7" .. (currentTag or "v2.x") .. "\n"
	msg = msg .. "^8Свежий upstream: ^x50E050" .. remoteTag .. " (" .. remoteCommit .. ")\n"
	if #commitDesc > 0 then
		msg = msg .. "^8Изменения: ^7" .. commitDesc .. "\n"
	end
	msg = msg .. "\n^7Выберите действие:\n"
	msg = msg .. "^xD0D0D0• ^x50E050Обновить словари^7: скачивает свежие переводы без перезапуска.\n"
	msg = msg .. "^xD0D0D0• ^x60A0FFСкачать релиз (.zip)^7: открывает страницу загрузки нового .app/.exe."

	main:OpenConfirmPopup(
		"Обновление PoB — ARPG-Life",
		msg,
		"Обновить словари",
		function()
			updater.downloadDictionaries(main, launch)
		end,
		"Скачать полный .zip",
		function()
			if OpenURL then
				OpenURL(ver.releasesURL or "https://github.com/arpg-life-poe/arpg-life-poe/releases")
			end
		end
	)
end

function updater.downloadDictionaries(main, launch)
	local ver = updater.currentVersion or {}
	local rawBase = (ver and ver.rawDictBaseURL and #ver.rawDictBaseURL > 0)
		and ver.rawDictBaseURL
		or "https://raw.githubusercontent.com/arpg-life-poe/arpg-life-poe/main/i18n/dictionaries/"

	local isPoE2 = updater.isPoE2()
	local dictGameFile = isPoE2 and "poe2_ru.lua" or "poe1_ru.lua"
	local fileList = {
		{ name = "ui_ru.lua", label = "интерфейс" },
		{ name = "affix_templates.lua", label = "шаблоны свойств" },
		{ name = dictGameFile, label = "база предметов" },
	}

	local waitPopup = nil
	if main and main.OpenMessagePopup then
		waitPopup = main:OpenMessagePopup("Обновление словарей", "Загрузка свежих словарей с GitHub...\nПожалуйста, подождите.")
	end

	local function closeWaitPopup()
		if waitPopup and main and main.popups then
			for i, p in ipairs(main.popups) do
				if p == waitPopup then
					table.remove(main.popups, i)
					break
				end
			end
			waitPopup = nil
		end
	end

	local failed = false
	local failedFiles = {}

	local function downloadNext(index)
		if index > #fileList then
			-- All files processed!
			closeWaitPopup()
			if failed then
				if main and main.OpenMessagePopup then
					local errList = table.concat(failedFiles, ", ")
					main:OpenMessagePopup("Результат обновления", "Не удалось загрузить: " .. errList .. "\nПроверьте подключение к сети.")
				end
			else
				local i18n = rawget(_G, "i18n")
				if i18n and i18n.init then
					i18n.init(isPoE2 and "poe2" or "poe1")
				end

				-- Update local version metadata in memory and on disk
				if updater.remoteData then
					local data = updater.remoteData
					local remGame = isPoE2 and (data.poe2 or {}) or (data.poe1 or {})
					if not updater.currentVersion then
						updater.currentVersion = {}
					end
					if data.updated_at then
						updater.currentVersion.buildDate = data.updated_at:sub(1, 10)
					end
					if isPoE2 then
						if remGame.commit_short then updater.currentVersion.upstreamCommitPoE2 = remGame.commit_short end
						if remGame.latest_release_tag then updater.currentVersion.upstreamTagPoE2 = remGame.latest_release_tag end
					else
						if remGame.commit_short then updater.currentVersion.upstreamCommitPoE1 = remGame.commit_short end
						if remGame.latest_release_tag then updater.currentVersion.upstreamTagPoE1 = remGame.latest_release_tag end
					end

					-- Persist version.lua to GetUserPath()
					pcall(function()
						local userDir = _G.GetUserPath and _G.GetUserPath()
						if userDir then
							if _G.MakeDir then
								_G.MakeDir(userDir .. "/i18n")
							end
							local vf = io.open(userDir .. "/i18n/version.lua", "w")
							if vf then
								local code = "return {\n"
								for k, v in pairs(updater.currentVersion) do
									if type(v) == "string" then
										code = code .. string.format("\t%s = %q,\n", k, v)
									end
								end
								code = code .. "}\n"
								vf:write(code)
								vf:close()
							end
						end
					end)
				end

				updater.updateAvailable = false
				launch.arpgUpdateAvailable = false
				if main and main.OpenMessagePopup then
					main:OpenMessagePopup("Словари обновлены", "^x50E050Все словари успешно обновлены до последней версии!\n^7Перевод интерфейса и базы предметов актуализирован без перезапуска.")
				end
			end
			return
		end

		local item = fileList[index]
		local fileName = item.name
		local url = rawBase .. fileName

		-- Download current file sequentially
		launch:DownloadPage(url, function(resp, err)
			if err or not resp or not resp.body or #resp.body == 0 then
				failed = true
				table.insert(failedFiles, fileName)
				ConPrintf("Failed to download dictionary %s: %s", fileName, err or "Empty")
			else
				-- Parse dictionary chunk
				local chunk = loadstring(resp.body)
				if chunk then
					local success, dictTable = pcall(chunk)
					if success and type(dictTable) == "table" then
						local i18n = rawget(_G, "i18n")
						if i18n then
							if fileName == "ui_ru.lua" then
								i18n.uiDict = dictTable
								i18n.uiPatterns = dictTable.patterns or {}
								package.loaded["i18n.dictionaries.ui_ru"] = dictTable
							elseif fileName == "affix_templates.lua" then
								i18n.templates = dictTable
								package.loaded["i18n.dictionaries.affix_templates"] = dictTable
							elseif fileName == dictGameFile then
								i18n.gameDict = dictTable
								local modName = isPoE2 and "i18n.dictionaries.poe2_ru" or "i18n.dictionaries.poe1_ru"
								package.loaded[modName] = dictTable
							end
							i18n.memo = {}
							i18n.memoCount = 0
							ConPrintf("Successfully applied updated dictionary %s in-memory", fileName)
						end
					end
				end

				-- Save to disk in UserPath (always writable)
				pcall(function()
					local userDir = _G.GetUserPath and _G.GetUserPath()
					if userDir then
						if _G.MakeDir then
							_G.MakeDir(userDir .. "/i18n")
							_G.MakeDir(userDir .. "/i18n/dictionaries")
						end
						local f = io.open(userDir .. "/i18n/dictionaries/" .. fileName, "w")
						if f then
							f:write(resp.body)
							f:close()
						end
					end
					local scriptDir = _G.GetScriptPath and _G.GetScriptPath()
					if scriptDir then
						local f2 = io.open(scriptDir .. "/i18n/dictionaries/" .. fileName, "w")
						if f2 then
							f2:write(resp.body)
							f2:close()
						end
					end
				end)
			end

			-- Proceed to next file sequentially
			downloadNext(index + 1)
		end)
	end

	-- Start download chain
	downloadNext(1)
end

return updater
