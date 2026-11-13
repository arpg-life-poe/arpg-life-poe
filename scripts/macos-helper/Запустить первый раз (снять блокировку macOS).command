#!/bin/bash
# ==============================================================================
# Path of Building — ARPG-Life Edition
# Author: vlad1116 <75042578+vlad1116@users.noreply.github.com>
# Project: https://arpg-life.ru
#
# Скрипт первого запуска: снимает блокировку карантина macOS (Gatekeeper quarantine)
# ==============================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "========================================================"
echo " Path of Building — ARPG-Life Edition"
echo " Проверка и снятие карантина macOS (Gatekeeper)"
echo "========================================================"
echo ""

APP_PATH=""
for app in "$DIR"/*.app; do
    if [ -d "$app" ]; then
        APP_PATH="$app"
        break
    fi
done

if [ -z "$APP_PATH" ] || [ ! -d "$APP_PATH" ]; then
    echo "❌ Ошибка: Файл приложения .app не найден рядом со скриптом!"
    echo "Убедитесь, что архив полностью распакован в одну папку."
    echo ""
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

APP_NAME="$(basename "$APP_PATH")"
echo "Найдено приложение: $APP_NAME"
echo "Снимаем атрибут карантина (xattr -cr)..."

xattr -cr "$APP_PATH" 2>/dev/null

echo "✅ Блокировка успешно снята!"
echo "Запускаем $APP_NAME..."
echo ""

open "$APP_PATH"

echo "Приложение запущено. Вы можете закрыть это окно терминала."
sleep 2
exit 0
