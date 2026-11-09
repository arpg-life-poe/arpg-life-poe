# Path of Building — ARPG-Life Edition (PoE 1 & PoE 2)

> Автор проекта: **vlad1116** (`vlad1116 <75042578+vlad1116@users.noreply.github.com>`)  
> Проект: [arpg-life.ru](https://arpg-life.ru)

Сборка и русская локализация Path of Building Community для Path of Exile 1 и Path of Exile 2:
- Нативная сборка `PoBFrontend` под macOS (Apple Silicon / Intel) и Windows.
- Полная русская локализация (пассивное дерево, умения, камни, свойства предметов, интерфейс) с сохранением оригинальных названий и поиском на обоих языках (RU / EN).
- Автоматизированное обновление данных при выходе новых версий PoE 1 и PoE 2.

## Структура репозитория

- `patches/` — патчи для Lua-исходников PoB 1, PoB 2 и C++ фронтенда `PoBFrontend`.
- `i18n/` — модули интернационализации (`i18n.lua`), генераторы словарей из баз данных PoE 1/2 и скомпилированные словари.
- `scripts/` — скрипты сборки нативных бинарников (`.app`, `.dmg`, `.exe`) и синхронизации с upstream.
- `.github/workflows/` — CI/CD пайплайны автоматической сборки релизов.
- `upstream/` — исходники официальных репозиториев PathOfBuildingCommunity (не включены в git, скачиваются скриптами).
