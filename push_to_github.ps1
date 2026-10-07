# ============================================
# Скрипт для отправки проекта Мия на GitHub
# ============================================
# 
# ПЕРЕД ЗАПУСКОМ:
# 1. Зайди на https://github.com и создай новый репозиторий:
#    - Нажми "+" → "New repository"
#    - Имя: mia-assistant
#    - Описание: Голосовой ИИ-ассистент для Windows
#    - Public (публичный)
#    - НЕ ставь галочки на README, .gitignore, License
#    - Нажми "Create repository"
#
# 2. Замени YOUR_USERNAME на твой ник на GitHub ниже:

$env:PATH = "D:\PortableGit\cmd;" + $env:PATH

$GITHUB_USER = "dizofdx"

# Настраиваем удалённый репозиторий
git remote set-url origin "https://github.com/$GITHUB_USER/mia-assistant.git" 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin "https://github.com/$GITHUB_USER/mia-assistant.git"
}

# Пушим код
git push -u origin main

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  Готово! Проект загружен на GitHub!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Теперь настрой GitHub Pages:" -ForegroundColor Cyan
Write-Host "1. Зайди на https://github.com/$GITHUB_USER/mia-assistant/settings/pages"
Write-Host "2. Source: Deploy from a branch"
Write-Host "3. Branch: main"
Write-Host "4. Folder: /docs/gh-pages"
Write-Host "5. Нажми Save"
Write-Host ""
Write-Host "Через 1-2 минуты сайт будет доступен по адресу:"
Write-Host "  https://$GITHUB_USER.github.io/mia-assistant/" -ForegroundColor Yellow
Write-Host ""
