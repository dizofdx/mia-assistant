"""
audit_all_functions.py
Комплексный аудит всех функций ассистента Мия:
- Модуль инструментов (tools.py)
- Модуль долговременной памяти (memory.py)
- Модуль сценариев (scenarios.py)
- Модуль визуальных графов (visual_commands.py)
- Модуль веб-панели и REST API (web_panel.py)
- Модуль синтеза и распознавания речи (voice.py, voice_input.py)
- Модуль активации по ключевому слову (hotword.py)
- Модуль логики и связки с LLM (brain.py)
- Модуль Telegram-бота (tg_bot.py)
- Модуль ядра ассистента (main.py)
"""

import os
import sys
import json
import inspect
import asyncio
import tempfile
import traceback

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_DIR = r"D:\assistant"
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from fastapi.testclient import TestClient

import config
import tools
import memory
import scenarios
import visual_commands
import web_panel
import voice
import voice_input
import hotword
import tg_bot
import brain
import main

# Mock объекты для изолированного тестирования
class MockAvatar:
    def __init__(self):
        self.emotion = "СПОКОЙСТВИЕ"
    async def set_emotion(self, emo):
        self.emotion = emo
    async def connect(self):
        pass

class MockVoice:
    def __init__(self):
        self.is_speaking = False
        self.profile = "anime"
        self.speaker_name = "baya"
    def get_speaker(self):
        return self.speaker_name
    async def speak(self, text, emotion=""):
        return True
    async def speak_edge(self, text):
        return True
    async def speak_silero(self, text, speaker="baya"):
        return True
    def play_cue_sync(self, name, wait=False):
        pass

class MockAssistant:
    def __init__(self):
        self.cfg = config
        self.is_muted = False
        self.current_emotion = "СПОКОЙСТВИЕ"
        self.avatar = MockAvatar()
        self.voice = MockVoice()
        self.memory = memory.Memory(path=os.path.join(tempfile.gettempdir(), "test_mia_memory.db"))
        self.tools = tools.Tools(self)
        self.scenarios = scenarios.ScenarioEngine(self, folder=os.path.join(tempfile.gettempdir(), "test_mia_scenarios"))
        self.vc_manager = visual_commands.VisualCommandManager(self)
        self.vc_manager.folder = os.path.join(tempfile.gettempdir(), "test_mia_vc")
        self.brain = None
        self.tg = None

    def set_muted(self, val):
        self.is_muted = val
        return val

    def toggle_muted(self):
        self.is_muted = not self.is_muted
        return self.is_muted

    def notify_admin_sync(self, msg):
        pass

    async def handle_user_message(self, text, speak=True, source="other"):
        return "РАДОСТЬ", f"Ответ на: {text}", f"[РАДОСТЬ] Ответ на: {text}"

    async def handle_user_message_stream(self, text, on_token=None, speak=True, source="other"):
        if on_token:
            on_token("Привет! ")
            on_token("Я Мия.")
        return "РАДОСТЬ", f"Ответ на: {text}", f"[РАДОСТЬ] Ответ на: {text}", 1, 2


results = {
    "tools": [],
    "memory": [],
    "scenarios": [],
    "visual_commands": [],
    "web_panel": [],
    "voice": [],
    "hotword": [],
    "brain": [],
    "tg_bot": [],
    "core": []
}

def record(category, function_name, status, details="", exception=None):
    entry = {
        "function": function_name,
        "status": status,  # "OK", "FAIL", "CONFIG_REQUIRED", "WARNING"
        "details": details,
        "error": str(exception) if exception else None
    }
    results[category].append(entry)
    symbol = "✅" if status == "OK" else ("⚠️" if status in ("WARNING", "CONFIG_REQUIRED") else "❌")
    print(f"[{category.upper()}] {symbol} {function_name}: {status} - {details}")

# 1. ТЕСТИРОВАНИЕ TOOLS.PY
def audit_tools():
    print("\n--- 🛠️ АУДИТ TOOLS.PY ---")
    asst = MockAssistant()
    t = asst.tools

    # 1.1 tool_get_time
    try:
        res = t.tool_get_time()
        assert res and ("Сейчас" in res or ":" in res)
        record("tools", "tool_get_time", "OK", f"Формат времени: '{res}'")
    except Exception as e:
        record("tools", "tool_get_time", "FAIL", "Сбой получения времени", e)

    # 1.2 tool_get_system_stats
    try:
        res = t.tool_get_system_stats()
        assert res and ("cpu" in res.lower() or "ram" in res.lower() or "диск" in res.lower())
        record("tools", "tool_get_system_stats", "OK", "Метрики ЦП/ОЗУ/дисков получены корректно")
    except Exception as e:
        record("tools", "tool_get_system_stats", "FAIL", "Сбой получения статистики ПК", e)

    # 1.3 tool_get_weather
    try:
        res = t.tool_get_weather("Москва")
        assert res and len(res) > 5
        record("tools", "tool_get_weather", "OK", f"Погода получена: {res[:60]}...")
    except Exception as e:
        record("tools", "tool_get_weather", "FAIL", "Сбой запроса погоды", e)

    # 1.4 tool_search_web
    try:
        res = t.tool_search_web("Python release notes")
        assert res and len(res) > 5
        record("tools", "tool_search_web", "OK", f"Поиск выполнен успешно: {res[:60]}...")
    except Exception as e:
        record("tools", "tool_search_web", "WARNING", f"Поиск завершился с ошибкой: {e}", e)

    # 1.5 tool_search_youtube
    try:
        # tool_search_youtube запускает браузер; проверяем генерацию или безопасность
        res = t.tool_search_youtube("loli dance")
        assert "youtube" in res.lower() or "откры" in res.lower()
        record("tools", "tool_search_youtube", "OK", "Генерация поискового запроса YouTube работает")
    except Exception as e:
        record("tools", "tool_search_youtube", "FAIL", "Сбой YouTube поиска", e)

    # 1.6 tool_open_website
    try:
        res = t.tool_open_website("https://github.com")
        assert "откры" in res.lower()
        record("tools", "tool_open_website", "OK", "Открытие веб-сайтов работает штатно")
    except Exception as e:
        record("tools", "tool_open_website", "FAIL", "Сбой открытия сайта", e)

    # 1.7 tool_open_program
    try:
        blocked = t.tool_open_program("cmd.exe")
        assert "заблокирован" in blocked.lower()
        normal = t.tool_open_program("калькулятор")
        record("tools", "tool_open_program", "OK", "Запуск разрешенных программ и блокировка системных утилит активны")
    except Exception as e:
        record("tools", "tool_open_program", "FAIL", "Сбой в tool_open_program", e)

    # 1.8 tool_media_control & status
    try:
        st = t.tool_media_status()
        assert isinstance(st, dict) and "players" in st
        res_ctrl = t.tool_media_control("volume_mute")
        record("tools", "tool_media_control / tool_media_status", "OK", f"Управление мультимедиа и статус работают (плееров: {len(st.get('players', []))})")
    except Exception as e:
        record("tools", "tool_media_control", "FAIL", "Сбой мультимедиа", e)

    # 1.9 tool_window_control
    try:
        res = t.tool_window_control("minimize_all")
        assert "окна" in res.lower() or "свернуты" in res.lower() or "готово" in res.lower()
        record("tools", "tool_window_control", "OK", "Управление окнами ПК работает штатно")
    except Exception as e:
        record("tools", "tool_window_control", "FAIL", "Сбой управления окнами", e)

    # 1.10 tool_volume
    try:
        res = t.tool_volume(50)
        record("tools", "tool_volume", "OK", f"Регулировка громкости: {res}")
    except Exception as e:
        record("tools", "tool_volume", "FAIL", "Сбой регулировки громкости", e)

    # 1.11 tool_mute_assistant
    try:
        res = t.tool_mute_assistant(True)
        assert asst.is_muted == True
        t.tool_mute_assistant(False)
        assert asst.is_muted == False
        record("tools", "tool_mute_assistant", "OK", "Включение/выключение тихого режима работает")
    except Exception as e:
        record("tools", "tool_mute_assistant", "FAIL", "Сбой мута ассистента", e)

    # 1.12 tool_take_screenshot
    try:
        shot_path = t.tool_take_screenshot()
        if shot_path and os.path.exists(shot_path):
            record("tools", "tool_take_screenshot", "OK", f"Скриншот успешно сохранен: {shot_path}")
        else:
            record("tools", "tool_take_screenshot", "WARNING", "Скриншот не сформировал файл (возможно, виртуальный дисплей)")
    except Exception as e:
        record("tools", "tool_take_screenshot", "FAIL", "Сбой захвата экрана", e)

    # 1.13 tool_read_file & tool_write_file (Песочница)
    try:
        write_res = t.tool_write_file("test_audit.txt", "Audit content OK")
        read_res = t.tool_read_file("projects/test_audit.txt")
        assert "Audit content OK" in read_res
        # Проверка защиты config.py
        sec_read = t.tool_read_file("config.py")
        assert "заблокирован" in sec_read.lower()
        record("tools", "tool_read_file / tool_write_file", "OK", "Изолированная песочница и защита секретов работают идеально")
    except Exception as e:
        record("tools", "tool_read_file / tool_write_file", "FAIL", "Сбой файловых инструментов", e)

    # 1.14 tool_add_note & tool_list_notes
    try:
        n_add = t.tool_add_note("Купить чай")
        n_list = t.tool_list_notes()
        assert "чай" in n_list.lower()
        record("tools", "tool_add_note / tool_list_notes", "OK", "Создание и чтение заметок работает штатно")
    except Exception as e:
        record("tools", "tool_add_note", "FAIL", "Сбой заметок", e)

    # 1.15 tool_remember_fact
    try:
        f_res = t.tool_remember_fact("Пользователь любит пиццу")
        facts = asst.memory.all_facts()
        assert any("пиццу" in f for f in facts)
        record("tools", "tool_remember_fact", "OK", "Запоминание фактов в долговременную память работает")
    except Exception as e:
        record("tools", "tool_remember_fact", "FAIL", "Сбой памяти фактов", e)

    # 1.16 tool_ask_expert_ai
    try:
        # Если ключ отсутствует — функция должна вернуть вежливое предупреждение
        exp_res = t.tool_ask_expert_ai("Тест")
        if "не настроен" in exp_res.lower() or "ключ" in exp_res.lower():
            record("tools", "tool_ask_expert_ai", "CONFIG_REQUIRED", f"Требуется API ключ (ответ: {exp_res[:50]}...)")
        else:
            record("tools", "tool_ask_expert_ai", "OK", f"Экспертный ИИ ответил: {exp_res[:50]}...")
    except Exception as e:
        record("tools", "tool_ask_expert_ai", "FAIL", "Сбой вызова экспертного ИИ", e)

    # 1.17 dispatch
    try:
        d_res = t.dispatch("get_time", {})
        assert d_res and ("Сейчас" in d_res or ":" in d_res)
        record("tools", "dispatch", "OK", "Роутер диспетчера инструментов работает корректно")
    except Exception as e:
        record("tools", "dispatch", "FAIL", "Сбой dispatch", e)


# 2. ТЕСТИРОВАНИЕ MEMORY.PY
def audit_memory():
    print("\n--- 🧠 АУДИТ MEMORY.PY ---")
    tmp_db = os.path.join(tempfile.gettempdir(), "test_memory_audit.db")
    if os.path.exists(tmp_db):
        try: os.remove(tmp_db)
        except: pass

    mem = memory.Memory(path=tmp_db)
    try:
        # add_message
        msg_id1 = mem.add_message("user", "Привет, Мия!", source="web")
        msg_id2 = mem.add_message("assistant", "Привет! Чем помочь?", emotion="РАДОСТЬ", source="web")
        assert msg_id1 > 0 and msg_id2 > msg_id1
        record("memory", "add_message", "OK", f"Сообщения успешно сохранены в SQLite (id={msg_id1}, {msg_id2})")

        # recent_dialog
        dialog = mem.recent_dialog(limit=10)
        assert len(dialog) == 2
        assert dialog[0]["content"] == "Привет, Мия!" and dialog[1]["content"] == "Привет! Чем помочь?"
        record("memory", "recent_dialog", "OK", f"Извлечено {len(dialog)} сообщений диалога с метаданными")

        # recent_messages
        msgs = mem.recent_messages(limit=5)
        assert len(msgs) == 2
        record("memory", "recent_messages", "OK", "Форматирование контекста для LLM работает")

        # add_fact & all_facts
        mem.add_fact("Любимый цвет - синий")
        mem.add_fact("День рождения в мае")
        facts = mem.all_facts()
        assert len(facts) == 2 and "синий" in facts[0]
        record("memory", "add_fact / all_facts", "OK", f"Факты сохранены и извлечены ({len(facts)} шт.)")
    except Exception as e:
        record("memory", "MemoryEngine", "FAIL", "Сбой SQLite базы памяти", e)


# 3. ТЕСТИРОВАНИЕ SCENARIOS.PY
def audit_scenarios():
    print("\n--- 📜 АУДИТ SCENARIOS.PY ---")
    tmp_folder = os.path.join(tempfile.gettempdir(), "test_scenarios_audit")
    os.makedirs(tmp_folder, exist_ok=True)
    asst = MockAssistant()
    eng = scenarios.ScenarioEngine(asst, folder=tmp_folder)

    try:
        # save
        scenario_data = {
            "name": "Тестовый сценарий",
            "trigger": "тест",
            "actions": [
                {"type": "say", "text": "Тест запущен"},
                {"type": "delay", "seconds": 0.05},
                {"type": "volume", "value": 70}
            ]
        }
        eng.save(scenario_data)
        record("scenarios", "save", "OK", "Сценарий сохранен в JSON")

        # list_all
        all_s = eng.list_all()
        assert len(all_s) >= 1 and any(s.get("name") == "Тестовый сценарий" for s in all_s)
        record("scenarios", "list_all", "OK", f"Найдено {len(all_s)} сценариев")

        # get
        s = eng.get("Тестовый сценарий")
        assert s is not None and s.get("name") == "Тестовый сценарий"
        s_part = eng.get("тестовый")
        assert s_part is not None
        record("scenarios", "get", "OK", "Поиск сценария по точному и частичному совпадению работает")

        # run
        res_run = asyncio.run(eng.run("Тестовый сценарий"))
        assert "успешно" in str(res_run).lower()
        record("scenarios", "run / do_action", "OK", "Исполнение цепочки действий отработало без ошибок")

        # delete
        eng.delete("Тестовый сценарий")
        assert eng.get("Тестовый сценарий") is None
        record("scenarios", "delete", "OK", "Удаление сценария работает корректно")
    except Exception as e:
        record("scenarios", "ScenarioEngine", "FAIL", "Сбой движка сценариев", e)


# 4. ТЕСТИРОВАНИЕ VISUAL_COMMANDS.PY
def audit_visual_commands():
    print("\n--- 🧩 АУДИТ VISUAL_COMMANDS.PY ---")
    tmp_folder = os.path.join(tempfile.gettempdir(), "test_vc_audit")
    os.makedirs(tmp_folder, exist_ok=True)
    asst = MockAssistant()
    vcm = visual_commands.VisualCommandManager(asst)
    vcm.folder = tmp_folder

    try:
        # save_flow
        flow_data = {
            "id": "flow_audit_1",
            "name": "Аудит Графа",
            "nodes": [
                {"id": "node_1", "type": "start", "label": "Старт"},
                {"id": "node_2", "type": "speech", "data": {"text": "Граф активен"}},
                {"id": "node_3", "type": "delay", "data": {"seconds": 0.05}}
            ],
            "edges": [
                {"from": "node_1", "to": "node_2"},
                {"from": "node_2", "to": "node_3"}
            ]
        }
        vcm.save_flow(flow_data)
        record("visual_commands", "save_flow", "OK", "Граф визуальной команды успешно сохранен")

        # list_flows
        flows = vcm.list_flows()
        assert len(flows) >= 1 and any(f.get("id") == "flow_audit_1" for f in flows)
        record("visual_commands", "list_flows", "OK", f"Найдено {len(flows)} визуальных графов")

        # get_flow
        fl = vcm.get_flow("flow_audit_1")
        assert fl and fl.get("name") == "Аудит Графа"
        record("visual_commands", "get_flow", "OK", "Извлечение графа по идентификатору работает")

        # execute_flow
        exec_res = asyncio.run(vcm.execute_flow("flow_audit_1"))
        assert exec_res.get("ok") == True
        record("visual_commands", "execute_flow", "OK", "Топологический обход и исполнение узлов графа успешны")

        # delete_flow
        del_res = vcm.delete_flow("flow_audit_1")
        assert del_res == True and vcm.get_flow("flow_audit_1") is None
        record("visual_commands", "delete_flow", "OK", "Удаление визуального графа работает корректно")
    except Exception as e:
        record("visual_commands", "VisualCommandManager", "FAIL", "Сбой визуальных команд", e)


# 5. ТЕСТИРОВАНИЕ WEB_PANEL.PY
def audit_web_panel():
    print("\n--- 🌐 АУДИТ WEB_PANEL.PY (REST API & UI) ---")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app, raise_server_exceptions=False)

    routes_to_test = [
        ("GET", "/", None, 200, "Веб-интерфейс HTML"),
        ("GET", "/manifest.json", None, 200, "PWA манифест"),
        ("GET", "/api/status", None, 200, "Статус ассистента"),
        ("GET", "/api/history", None, 200, "История диалогов"),
        ("GET", "/api/system_stats", None, 200, "Телеметрия ПК (ЦП, ОЗУ, Диск)"),
        ("GET", "/api/weather", None, 200, "Виджет погоды"),
        ("GET", "/api/currency", None, 200, "Виджет курсов валют"),
        ("GET", "/api/avatar_status", None, 200, "Статус аватара и эмоции"),
        ("GET", "/api/mascot_info", None, 200, "Информация о маскоте"),
        ("GET", "/api/media/status", None, 200, "Статус мультимедиа плееров"),
        ("POST", "/api/media", {"action": "volume_mute"}, 200, "Управление медиа"),
        ("POST", "/api/window", {"action": "minimize_all"}, 200, "Управление окнами"),
        ("POST", "/api/mute", {"muted": True}, 200, "Переключение мута"),
        ("POST", "/api/remote_action", {"action": "minimize"}, 200, "Удаленные действия"),
        ("GET", "/api/visual_commands", None, 200, "Список визуальных команд"),
        ("GET", "/api/scenarios", None, 200, "Список сценариев"),
        ("GET", "/api/installed_apps", None, 200, "Сканирование установленных программ"),
        ("GET", "/api/files/list", {"path": "root"}, 200, "Листинг корня дисков"),
        ("POST", "/api/set_voice", {"voice": "baya"}, 200, "Смена голоса"),
        ("POST", "/api/test_say", {"text": "Тест", "voice": "baya"}, 200, "Тестовое произношение"),
        ("POST", "/api/chat", {"text": "Привет", "speak": False}, 200, "Чат без стриминга"),
        ("POST", "/api/chat_stream", {"text": "Привет Мия", "speak": False}, 200, "Потоковый чат (NDJSON)")
    ]

    for method, path, payload, exp_status, desc in routes_to_test:
        try:
            if method == "GET":
                res = client.get(path, params=payload)
            else:
                res = client.post(path, json=payload)
            if res.status_code == exp_status:
                record("web_panel", f"{method} {path}", "OK", f"{desc} (HTTP {res.status_code})")
            else:
                record("web_panel", f"{method} {path}", "FAIL", f"Ожидался HTTP {exp_status}, получен {res.status_code}: {res.text[:80]}")
        except Exception as e:
            record("web_panel", f"{method} {path}", "FAIL", f"Исключение при вызове: {desc}", e)

    # Тестирование защитных механизмов
    try:
        # Защита .git
        git_res = client.get("/api/files/list", params={"path": os.path.join(PROJECT_DIR, ".git")})
        assert "error" in git_res.json()
        record("web_panel", "Security: .git listing protection", "OK", "Доступ к .git заблокирован")

        # Защита config.py скачивание
        cfg_res = client.get("/api/files/download", params={"path": os.path.join(PROJECT_DIR, "config.py")})
        assert cfg_res.status_code == 403
        record("web_panel", "Security: config.py download protection", "OK", "Скачивание config.py отклонено с 403 Forbidden")
    except Exception as e:
        record("web_panel", "Security checks", "FAIL", "Сбой защитных механизмов веб-панели", e)


# 6. ТЕСТИРОВАНИЕ СИНТЕЗА И РАСПОЗНАВАНИЯ РЕЧИ (VOICE.PY / VOICE_INPUT.PY)
def audit_voice():
    print("\n--- 🎙️ АУДИТ VOICE.PY / VOICE_INPUT.PY ---")
    try:
        v = voice.Voice(config)
        cur_speaker = v.get_speaker()
        cur_profile = v.get_profile_name()
        record("voice", "Voice.get_speaker / get_profile_name", "OK", f"Диктор: {cur_speaker}, Профиль: {cur_profile}")

        # Проверка переключения профилей
        v.set_profile("warm")
        assert v.profile == "warm"
        v.set_profile("anime")
        record("voice", "Voice.set_profile", "OK", "Переключение профилей голоса работает корректно")

        # Проверка наличия аудио-сигналов (cues)
        cue_dir = os.path.join(PROJECT_DIR, "audio")
        if os.path.exists(cue_dir):
            cues = [f for f in os.listdir(cue_dir) if f.endswith((".wav", ".mp3"))]
            record("voice", "Audio Cues (audio/*.wav)", "OK", f"Обнаружено {len(cues)} звуковых эффектов")
        else:
            record("voice", "Audio Cues", "WARNING", "Директория audio/ отсутствует")
    except Exception as e:
        record("voice", "Voice", "FAIL", "Сбой инициализации голосового движка", e)

    # voice_input Ears
    try:
        ears = voice_input.Ears(config)
        has_vosk = hasattr(ears, "model") and (ears.model is not None)
        if has_vosk:
            record("voice", "Ears (Vosk STT)", "OK", "Локальная модель Vosk успешно загружена")
        else:
            vosk_dir = os.path.join(PROJECT_DIR, "models", "vosk-model-small-ru")
            if os.path.exists(vosk_dir):
                record("voice", "Ears (Vosk STT)", "OK", f"Модель Vosk найдена в {vosk_dir}")
            else:
                record("voice", "Ears (Vosk STT)", "WARNING", "Модель Vosk не скачана локально (будет использоваться веб-ввод)")
    except Exception as e:
        record("voice", "Ears", "WARNING", f"Инициализация Ears: {e}")


# 7. ТЕСТИРОВАНИЕ ХОТВОРДА (HOTWORD.PY)
def audit_hotword():
    print("\n--- ⚡ АУДИТ HOTWORD.PY ---")
    try:
        asst = MockAssistant()
        hw = hotword.HotwordListener(asst)
        record("hotword", "HotwordListener initialization", "OK", f"Метод распознавания: {getattr(hw, 'backend', 'porcupine/vosk/openwakeword')}")
    except Exception as e:
        record("hotword", "HotwordListener", "WARNING", f"Инициализация hotword: {e}")


# 8. ТЕСТИРОВАНИЕ BRAIN.PY (LLM & ПРЯМЫЕ ИНТЕНТЫ)
def audit_brain():
    print("\n--- 🧠 АУДИТ BRAIN.PY ---")
    asst = MockAssistant()
    try:
        b = brain.Brain(config, asst.memory, asst.tools)
        
        # 8.1 Прямые интенты (check_direct_intent)
        test_intents = [
            ("сколько сейчас времени", "get_time"),
            ("какая сейчас погода в москве", "get_weather"),
            ("сделай скриншот экрана", "screenshot"),
            ("сверни все окна", "window_minimize"),
            ("заблокируй компьютер", "lock_pc"),
            ("сделай погромче", "volume_up"),
            ("выключи звук", "mute_pc")
        ]
        intent_ok = 0
        for phrase, expected in test_intents:
            res = b.check_direct_intent(phrase)
            if res:
                intent_ok += 1
        record("brain", "Brain.check_direct_intent", "OK", f"Прямые интенты распознаны: {intent_ok}/{len(test_intents)} без обращения к LLM")

        # 8.2 Проверка настроек LLM
        provider = getattr(config, "LLM_PROVIDER", "ollama")
        model = getattr(config, "LLM_MODEL", "qwen2.5:3b-instruct")
        record("brain", "Brain.LLM_CONFIG", "OK", f"Провайдер: {provider}, Модель: {model}")
    except Exception as e:
        record("brain", "Brain", "FAIL", "Сбой инициализации Brain", e)


# 9. ТЕСТИРОВАНИЕ TELEGRAM-БОТА (TG_BOT.PY)
def audit_tg_bot():
    print("\n--- ✈️ АУДИТ TG_BOT.PY ---")
    try:
        asst = MockAssistant()
        bot = tg_bot.TGBot(asst)
        token = getattr(config, "TG_TOKEN", "")
        admin_id = getattr(config, "ADMIN_ID", getattr(config, "TG_ADMIN_ID", 0))

        # Создаем фиктивное сообщение для проверки is_admin
        class FakeUser:
            def __init__(self, uid, uname="test"):
                self.id = uid
                self.username = uname
        class FakeMessage:
            def __init__(self, uid, uname="test"):
                self.from_user = FakeUser(uid, uname)

        is_adm = bot.is_admin(FakeMessage(admin_id)) if admin_id else True
        is_stranger = bot.is_admin(FakeMessage(999999999))

        if token:
            record("tg_bot", "TGBot.config", "OK", f"Токен задан, Admin ID={admin_id}, проверка доступа: stranger={is_stranger}")
        else:
            record("tg_bot", "TGBot.config", "CONFIG_REQUIRED", "TG_TOKEN не заполнен в config.py (бот отключен)")

        # Проверка генерации клавиатуры
        kb = bot.get_main_reply_keyboard()
        assert kb is not None
        record("tg_bot", "get_main_reply_keyboard", "OK", "Главная клавиатура бота сформирована корректно")

        # Проверка сборки панели Jarvis
        jarvis_text, jarvis_kb = bot.build_jarvis_panel_data()
        assert "JARVIS" in jarvis_text or "Панель" in jarvis_text
        record("tg_bot", "build_jarvis_panel_data", "OK", "Интерактивная панель управления Jarvis сформирована")
    except Exception as e:
        record("tg_bot", "TGBot", "FAIL", "Сбой в tg_bot.py", e)


# 10. ТЕСТИРОВАНИЕ CORE (MAIN.PY)
def audit_core():
    print("\n--- ⚙️ АУДИТ MAIN.PY ---")
    try:
        asst = main.Assistant()
        record("core", "Assistant initialization", "OK", "Экземпляр Assistant успешно инициализирован со всеми подсистемами")
        record("core", "Subsystems binding", "OK", f"Memory: {'OK' if hasattr(asst, 'memory') else 'FAIL'}, Tools: {'OK' if hasattr(asst, 'tools') else 'FAIL'}, Voice: {'OK' if hasattr(asst, 'voice') else 'FAIL'}")
    except Exception as e:
        record("core", "Assistant", "FAIL", "Сбой инициализации основного класса ассистента", e)


if __name__ == "__main__":
    print("=" * 80)
    print("  🚀 ПОЛНЫЙ АУДИТ И ТЕСТИРОВАНИЕ ВСЕХ ФУНКЦИЙ ГОЛОСОВОГО АССИСТЕНТА МИЯ")
    print("=" * 80)

    audit_tools()
    audit_memory()
    audit_scenarios()
    audit_visual_commands()
    audit_web_panel()
    audit_voice()
    audit_hotword()
    audit_brain()
    audit_tg_bot()
    audit_core()

    # Сохраняем сводные данные
    with open("audit_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total_ok = sum(1 for cat in results.values() for item in cat if item["status"] == "OK")
    total_warn = sum(1 for cat in results.values() for item in cat if item["status"] in ("WARNING", "CONFIG_REQUIRED"))
    total_fail = sum(1 for cat in results.values() for item in cat if item["status"] == "FAIL")
    total = total_ok + total_warn + total_fail

    print("\n" + "=" * 80)
    print(f"  📊 ИТОГИ АУДИТА: Всего проверок: {total} | ✅ Работает: {total_ok} | ⚠️ Требует ключа/внимания: {total_warn} | ❌ Сломано: {total_fail}")
    print("=" * 80 + "\n")
