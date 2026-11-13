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
	local verStatus, ver = pcall(require, "i18n.version")
	if not verStatus or not ver then
		ver = {
			version = "2.49.3-arpg1",
			buildDate = "2026-11-13",
			upstreamCommitPoE1 = "a69391d",
			upstreamCommitPoE2 = "601768b",
			upstreamTagPoE1 = "v2.67.2",
			upstreamTagPoE2 = "v2.49.3",
			checkURL = "https://raw.githubusercontent.com/arpg-life-poe/arpg-life-poe/main/upstream-versions.json",
			releasesURL = "https://github.com/arpg-life-poe/arpg-life-poe/releases",
			rawDictBaseURL = "https://raw.githubusercontent.com/arpg-life-poe/arpg-life-poe/main/i18n/dictionaries/",
		}
	end
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
	local isPoE2 = updater.isPoE2()
	local dictGameFile = isPoE2 and "poe2_ru.lua" or "poe1_ru.lua"
	local files = { "ui_ru.lua", "affix_templates.lua", dictGameFile }
	local remaining = #files
	local failed = false

	if main and main.OpenMessagePopup then
		main:OpenMessagePopup("Обновление словарей", "Загрузка свежих словарей с GitHub...\nПожалуйста, подождите.")
	end

	for _, fileName in ipairs(files) do
		local url = ver.rawDictBaseURL .. fileName
		launch:DownloadPage(url, function(resp, err)
			remaining = remaining - 1
			if err or not resp or not resp.body or #resp.body == 0 then
				failed = true
				ConPrintf("Failed to download dictionary %s: %s", fileName, err or "Empty")
			else
				-- Parse dictionary in-memory and update i18n
				local chunk = loadstring(resp.body)
				if chunk then
					local success, dictTable = pcall(chunk)
					if success and type(dictTable) == "table" then
						local i18n = rawget(_G, "i18n")
						if i18n and i18n.dict then
							for k, v in pairs(dictTable) do
								i18n.dict[k] = v
							end
							ConPrintf("Successfully updated %s in-memory (%d keys)", fileName, #dictTable)
						end
					end
				end

				-- Try saving to disk if writable
				pcall(function()
					local path = "src/i18n/dictionaries/" .. fileName
					local f = io.open(path, "w")
					if not f then
						path = "i18n/dictionaries/" .. fileName
						f = io.open(path, "w")
					end
					if f then
						f:write(resp.body)
						f:close()
					end
				end)
			end

			if remaining == 0 then
				if failed then
					if main and main.OpenMessagePopup then
						main:OpenMessagePopup("Результат обновления", "Часть словарей не удалось загрузить.\nПроверьте подключение к сети.")
					end
				else
					local i18n = rawget(_G, "i18n")
					if i18n and i18n.init then
						i18n.init()
					end
					updater.updateAvailable = false
					launch.arpgUpdateAvailable = false
					if main and main.OpenMessagePopup then
						main:OpenMessagePopup("Словари обновлены", "^x50E050Все словари успешно обновлены до последней версии!\n^7Перевод интерфейса и базы предметов актуализирован.")
					end
				end
			end
		end)
	end
end

return updater
