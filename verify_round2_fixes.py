"""
verify_round2_fixes.py
Верификационный набор тестов для подтверждения устранения всех 5 уязвимостей
и сбоев второго раунда адверсариального ревью:
1. Защита от сбоя 500 в POST /api/chat_stream при невалидном/битом JSON или неверном теле.
2. Безопасная обработка не-dict структур данных в POST /api/scenarios и ScenarioEngine.save.
3. Блокировка перечисления директории .git и скрытых системных папок в GET /api/files/list.
4. Валидация входных данных в POST /api/set_voice и POST /api/test_say (HTTP 400 вместо 500).
5. Блокировка опасных системных исполняемых файлов (cmd.exe, powershell.exe, format.com и др.) в tool_open_program.
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
from fastapi.testclient import TestClient

PROJECT_DIR = r"D:\assistant"
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import config
import tools
import web_panel
import scenarios

class MockAvatar:
    async def set_emotion(self, emo): pass
    async def connect(self): pass

class MockVoice:
    is_speaking = False
    profile = "anime"
    def get_speaker(self): return "xenia"
    async def speak(self, text, emotion=""): pass
    def play_cue_sync(self, name, wait=False): pass

class MockMemory:
    def recent_dialog(self, limit=50, since_id=0): return []
    def all_facts(self): return []
    def recent_messages(self, limit=20): return []
    def add_message(self, *args, **kwargs): return 1

class MockAssistant:
    def __init__(self):
        self.cfg = config
        self.is_muted = False
        self.avatar = MockAvatar()
        self.voice = MockVoice()
        self.memory = MockMemory()
        self.tools = tools.Tools(self)
        self.scenarios = scenarios.ScenarioEngine(self, folder="scenarios")
        self.current_emotion = "СПОКОЙСТВИЕ"

    def set_muted(self, val):
        self.is_muted = val
        return val

    def notify_admin_sync(self, msg):
        pass

    async def handle_user_message_stream(self, text, on_token=None, speak=True, source="other"):
        if on_token:
            on_token("Привет!")
        return "РАДОСТЬ", f"Ответ на: {text}", f"[РАДОСТЬ] Ответ на: {text}", 1, 2

def test_1_chat_stream_validation():
    print("[1/5] Проверка защиты эндпоинта /api/chat_stream от сбоя 500...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app, raise_server_exceptions=False)

    # 1.1 Передача не-JSON байтов
    res1 = client.post("/api/chat_stream", content=b"CORRUPTED_RAW_BODY", headers={"Content-Type": "application/json"})
    assert res1.status_code == 400, f"Ожидался статус 400 при битом теле, получен {res1.status_code}"

    # 1.2 Передача массива вместо объекта
    res2 = client.post("/api/chat_stream", json=["invalid", "array"])
    assert res2.status_code == 400, f"Ожидался статус 400 при массиве, получен {res2.status_code}"

    # 1.3 Передача объекта с пустым текстом
    res3 = client.post("/api/chat_stream", json={"text": "   "})
    assert res3.status_code == 400, f"Ожидался статус 400 при пустом тексте, получен {res3.status_code}"

    # 1.4 Валидный запрос стримится штатно
    res4 = client.post("/api/chat_stream", json={"text": "Привет, Мия!"})
    assert res4.status_code == 200, f"Ожидался статус 200 при валидном запросе, получен {res4.status_code}"

    print("  ✅ [ИСПРАВЛЕНО] /api/chat_stream валидирует JSON и возвращает HTTP 400 вместо 500")
    return True

def test_2_scenarios_validation():
    print("[2/5] Проверка защиты сохранения сценариев от сбоя при не-dict типах...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app, raise_server_exceptions=False)

    # 2.1 Передача массива в POST /api/scenarios
    res1 = client.post("/api/scenarios", json=["item1", "item2"])
    assert res1.status_code == 400, f"Ожидался статус 400, получен {res1.status_code}"

    # 2.2 Передача битого JSON
    res2 = client.post("/api/scenarios", content=b"INVALID_JSON", headers={"Content-Type": "application/json"})
    assert res2.status_code == 400, f"Ожидался статус 400, получен {res2.status_code}"

    # 2.3 Прямой вызов ScenarioEngine.save с не-dict данными
    eng = scenarios.ScenarioEngine(asst, folder="scenarios")
    eng.save(["item1", "item2"])  # не должно вызывать AttributeError
    eng.save("simple string")     # не должно вызывать ошибку
    eng.save(None)                # не должно вызывать ошибку

    print("  ✅ [ИСПРАВЛЕНО] POST /api/scenarios и ScenarioEngine.save защищены от некорректных типов данных")
    return True

def test_3_files_list_git_blocking():
    print("[3/5] Проверка блокировки перечисления директории .git в /api/files/list...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    git_dir = os.path.join(PROJECT_DIR, ".git")
    res = client.get("/api/files/list", params={"path": git_dir})
    assert res.status_code == 200, f"Ожидался статус 200, получен {res.status_code}"
    data = res.json()

    assert "error" in data, f"Ожидалась ошибка политики безопасности, получен ответ: {data}"
    assert "заблокирован" in data["error"].lower(), f"Текст ошибки не содержит сообщение о блокировке: {data['error']}"

    # Проверка, что при листинге корня проекта скрытые файлы (.git, .env, config.py) отфильтрованы
    res_root = client.get("/api/files/list", params={"path": PROJECT_DIR})
    root_data = res_root.json()
    folder_names = [f["name"].lower() for f in root_data.get("folders", [])]
    file_names = [f["name"].lower() for f in root_data.get("files", [])]
    assert ".git" not in folder_names, ".git не должна отображаться в списке папок"
    assert "config.py" not in file_names, "config.py не должен отображаться в списке файлов"

    print("  ✅ [ИСПРАВЛЕНО] Перечисление каталога .git и конфигов заблокировано политикой безопасности")
    return True

def test_4_voice_endpoints_validation():
    print("[4/5] Проверка валидации входных данных в /api/set_voice и /api/test_say...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app, raise_server_exceptions=False)

    # 4.1 set_voice с битыми данными
    res1 = client.post("/api/set_voice", content=b"MALFORMED_VOICE", headers={"Content-Type": "application/json"})
    assert res1.status_code == 400, f"Ожидался статус 400, получен {res1.status_code}"

    # 4.2 set_voice с массивом
    res2 = client.post("/api/set_voice", json=["not", "a", "dict"])
    assert res2.status_code == 400, f"Ожидался статус 400, получен {res2.status_code}"

    # 4.3 test_say с битыми данными
    res3 = client.post("/api/test_say", content=b"MALFORMED_SAY", headers={"Content-Type": "application/json"})
    assert res3.status_code == 400, f"Ожидался статус 400, получен {res3.status_code}"

    # 4.4 test_say с массивом
    res4 = client.post("/api/test_say", json=["hello"])
    assert res4.status_code == 400, f"Ожидался статус 400, получен {res4.status_code}"

    print("  ✅ [ИСПРАВЛЕНО] /api/set_voice и /api/test_say возвращают HTTP 400 вместо падения с 500")
    return True

def test_5_open_program_security_blocklist():
    print("[5/5] Проверка блокировки запуска опасных системных утилит в tool_open_program...")
    asst = MockAssistant()
    t = tools.Tools(asst)

    blocked_targets = [
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "format.com",
        "regedit.exe",
        "vssadmin.exe",
        r"C:\Windows\System32\cmd.exe",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "cmd",
        "powershell",
    ]

    for target in blocked_targets:
        res = t.tool_open_program(target)
        assert "заблокирован" in res.lower(), f"Цель '{target}' не была заблокирована! Ответ: {res}"

    print("  ✅ [ИСПРАВЛЕНО] Запуск опасных системных утилит заблокирован политикой безопасности")
    return True

if __name__ == "__main__":
    print("\n" + "#" * 76)
    print("  🛡️ ПРОВЕРКА УСТРАНЕНИЯ УЯЗВИМОСТЕЙ РАУНДА 2 (ВЕРИФИКАЦИОННЫЙ СЬЮТ)")
    print("#" * 76 + "\n")

    suite = [
        test_1_chat_stream_validation,
        test_2_scenarios_validation,
        test_3_files_list_git_blocking,
        test_4_voice_endpoints_validation,
        test_5_open_program_security_blocklist,
    ]

    all_passed = True
    for test_fn in suite:
        try:
            test_fn()
        except Exception as e:
            print(f"  ❌ ОШИБКА: {e}")
            all_passed = False

    print("\n" + "#" * 76)
    if all_passed:
        print("  🎉 ВСЕ 5 УЯЗВИМОСТЕЙ ВТОРОГО РАУНДА УСПЕШНО УСТРАНЕНЫ И ПОДТВЕРЖДЕНЫ!")
    else:
        print("  ⚠️ ЧАСТЬ ТЕСТОВ НЕ ПРОШЛА, ТРЕБУЕТСЯ ДОРАБОТКА")
    print("#" * 76 + "\n")
    if not all_passed:
        sys.exit(1)
