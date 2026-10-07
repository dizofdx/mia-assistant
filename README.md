<div align="center">
  <img src="static/avatar_default.png" width="180" alt="Мия AI">

  # 🎀 Мия — Голосовой ИИ-ассистент для Windows

  **Персональный ИИ-компаньон с голосовым управлением, аниме-стилем и веб-панелью Astra**

  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
  [![Telegram](https://img.shields.io/badge/Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
  [![License](https://img.shields.io/badge/License-MIT-a78bfa?style=for-the-badge)](LICENSE)
</div>

---

## 🌟 Что такое Мия?

**Мия** — полноценный голосовой ИИ-ассистент для Windows, объединяющий:

- 🎙️ **Голосовое управление** — распознавание речи (Vosk) + синтез голоса (Silero TTS), полностью офлайн
- 🧠 **ИИ-мозг** — Google Gemini для интеллектуальных ответов и tool-calling
- 🌐 **Веб-панель Astra** — красивый дашборд с мониторингом системы, картой, чатом
- 📱 **Telegram-бот** — управление ПК из любой точки мира
- 🎵 **Мультимедиа** — управление Яндекс Музыкой, YouTube, медиаплеерами
- ⚡ **Сценарии** — автоматизация задач (отдых, фокус, и т.д.)
- 📲 **PWA / Android** — мобильный пульт через Wi-Fi

## 🖥️ Скриншоты

<div align="center">
  <p><em>Веб-панель Astra с системным мониторингом и интерактивной картой</em></p>
</div>

## 🚀 Быстрый старт

### Требования
- Windows 10/11
- Python 3.11+
- Микрофон (для голосового управления)

### Установка

```bash
# 1. Клонируй репозиторий
git clone https://github.com/YOUR_USERNAME/mia-assistant.git
cd mia-assistant

# 2. Установи зависимости
pip install -r requirements.txt

# 3. Запусти Мию
python main.py
```

После запуска:
- **Веб-панель**: http://localhost:8000
- **Telegram-бот**: настрой токен в `config.py`
- **Голос**: скажи «Мия» для активации

## 📁 Структура проекта

```
mia-assistant/
├── main.py              # Точка входа
├── brain.py             # ИИ-мозг (Gemini + tool-calling)
├── tools.py             # Инструменты ассистента (60+ функций)
├── web_panel.py         # FastAPI веб-сервер
├── web_ui.html          # UI веб-панели (4000+ строк)
├── voice.py             # Silero TTS (синтез речи)
├── voice_input.py       # Vosk STT (распознавание)
├── hotword.py           # Детекция хотворда «Мия»
├── tg_bot.py            # Telegram-бот
├── scenarios.py         # Движок сценариев
├── visual_commands.py   # Визуальный редактор команд
├── config.py            # Конфигурация
├── memory.py            # Система памяти
├── audio_utils.py       # Утилиты для аудио
├── app_desktop.py       # Десктопное приложение
├── tray.py              # Трей-иконка Windows
├── scenarios/           # JSON-файлы сценариев
├── static/              # Статические файлы (аватар, иконки)
├── sounds/              # Звуковые эффекты
├── docs/                # Документация
└── requirements.txt     # Python-зависимости
```

## 🎙️ Голосовые команды

| Команда | Действие |
|---------|----------|
| «Мия, включи мою волну» | Запускает Яндекс Музыку |
| «Мия, открой YouTube» | Открывает YouTube в браузере |
| «Мия, сделай скриншот» | Создаёт снимок экрана |
| «Мия, запусти отдых» | Сценарий: YouTube + музыка |
| «Мия, заблокируй ПК» | Блокирует компьютер |
| «Мия, громкость выше/ниже» | Регулировка звука |
| «Мия, открой Steam» | Запускает приложение |

## ⚡ Сценарии

Сценарии — JSON-файлы в папке `scenarios/`:

```json
{
  "name": "отдых",
  "enabled": true,
  "trigger": { "type": "manual" },
  "actions": [
    { "type": "open_website", "url": "https://www.youtube.com" },
    { "type": "play_music" },
    { "type": "speak", "text": "Включаю режим отдыха!" }
  ]
}
```

## 🤖 Telegram-бот

Управляй Мией из Telegram:
- 📸 Скриншоты ПК
- 🎤 Голосовые сообщения с ответом
- ⌨️ Текстовые команды
- 🔒 Блокировка ПК
- 🎵 Управление музыкой

## 🗺️ Технологический стек

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.11 |
| Веб-сервер | FastAPI + Uvicorn |
| ИИ | Google Gemini (1.5/2.0) |
| STT | Vosk (офлайн) |
| TTS | Silero TTS v4 (офлайн) |
| Фронтенд | Vanilla JS, CSS3, MapLibre GL |
| Мессенджер | Telegram Bot API |
| Автоматизация | PyAutoGUI, ctypes |
| Мобильная | PWA (Progressive Web App) |

## 📄 Лицензия

MIT License — используй свободно!

---

<div align="center">
  <p>Сделано с 💜 by <strong>7ims</strong></p>
  <p><sub>Мия — твой персональный ИИ-компаньон</sub></p>
</div>
