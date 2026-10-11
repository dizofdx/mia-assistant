"""
verify_security_fixes.py
Верификационный тест-сьют для проверки устранения уязвимостей и сбоев.
Проверяет, что все 8 найденных сбоев теперь безопасно обработаны и система стабильна.
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
import visual_commands
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
        self.scenarios = None
        self.current_emotion = "СПОКОЙСТВИЕ"

    def set_muted(self, val):
        self.is_muted = val
        return val

    async def handle_user_message(self, text, speak=True, source="other"):
        return "РАДОСТЬ", f"Ответ на: {text}", f"[РАДОСТЬ] Ответ на: {text}"

def test_1_path_traversal_blocked():
    print("[1/8] Тест блокировки Path Traversal (/api/files/download)...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    secret_file = os.path.join(PROJECT_DIR, "config.py")
    res = client.get("/api/files/download", params={"path": secret_file})
    assert res.status_code == 403, f"Ожидался код 403 Forbidden, получен {res.status_code}"
    print("  ✅ [ИСПРАВЛЕНО] Доступ к config.py заблокирован со статусом 403 Forbidden")
    return True

def test_2_scenario_keyerror_handled():
    print("[2/8] Тест безопасной обработки действия без 'text' в сценариях...")
    asst = MockAssistant()
    se = scenarios.ScenarioEngine(asst)

    # Не должно бросать KeyError
    asyncio.run(se.do_action({"type": "say"}))
    asyncio.run(se.do_action({"type": "speak"}))
    asyncio.run(se.do_action({"type": "emote"}))
    print("  ✅ [ИСПРАВЛЕНО] Действия без обязательных полей отрабатывают штатно без KeyError")
    return True

def test_3_powershell_rce_blocked():
    print("[3/8] Тест блокировки несанкционированного PowerShell в visual_commands...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    flow_id = "test_ps_blocked"
    flow_data = {
        "id": flow_id,
        "name": "PS Test",
        "nodes": [
            {"id": "n1", "type": "trigger", "value": "test"},
            {"id": "n2", "type": "action", "subType": "powershell", "value": "Write-Output 'SHOULD_BE_BLOCKED'"}
        ],
        "edges": [{"from": "n1", "to": "n2"}]
    }

    client.post("/api/visual_commands", json=flow_data)
    res = client.post("/api/visual_commands/run", json={"id": flow_id})
    client.delete(f"/api/visual_commands/{flow_id}")

    steps = res.json().get("steps", [])
    ps_step = next((s for s in steps if s.get("id") == "n2"), {})
    assert ps_step.get("status") == "skipped", f"Шаг должен быть skipped: {ps_step}"
    assert "заблокировано" in ps_step.get("result", "").lower()
    print("  ✅ [ИСПРАВЛЕНО] Произвольный запуск PowerShell заблокирован политикой безопасности")
    return True

def test_4_sandbox_escape_prevented():
    print("[4/8] Тест принудительной изоляции файлов в песочнице (tool_write_file)...")
    asst = MockAssistant()
    t = tools.Tools(asst)

    target_outside = os.path.join(PROJECT_DIR, "memory", "malicious_outside.txt")
    if os.path.exists(target_outside):
        os.remove(target_outside)

    t.tool_write_file(target_outside, "Safe Sandbox Test")

    # Файл не должен появиться в memory!
    assert not os.path.exists(target_outside), "Файл не должен создаваться вне папки projects"
    # Файл должен быть изолирован в projects!
    safe_path = os.path.join(PROJECT_DIR, "projects", "malicious_outside.txt")
    assert os.path.exists(safe_path), "Файл должен быть безопасно перемещен в папку projects"
    if os.path.exists(safe_path):
        os.remove(safe_path)
    print("  ✅ [ИСПРАВЛЕНО] Попытка записи вне проектов безопасно перенаправлена в projects/")
    return True

def test_5_xss_upload_blocked():
    print("[5/8] Тест отклонения опасных расширений в /api/upload_mascot_2d...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    html_payload = b"<html><body><script>alert(1)</script></body></html>"
    files = {"file": ("exploit.html", html_payload, "text/html")}
    res = client.post("/api/upload_mascot_2d", files=files)
    assert res.status_code == 415, f"Ожидался код 415, получен {res.status_code}"

    # Проверяем, что легитимный PNG принимается
    png_payload = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    files_ok = {"file": ("avatar.png", png_payload, "image/png")}
    res_ok = client.post("/api/upload_mascot_2d", files=files_ok)
    assert res_ok.status_code == 200, f"Ожидался код 200 для PNG, получен {res_ok.status_code}"
    print("  ✅ [ИСПРАВЛЕНО] Загрузка .html отклонена с HTTP 415, разрешены только изображения")
    return True

def test_6_chat_missing_text_validated():
    print("[6/8] Тест валидации входных данных в /api/chat...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    res = client.post("/api/chat", json={"speak": False})
    assert res.status_code == 400, f"Ожидался код 400 Bad Request, получен {res.status_code}"
    assert "text" in res.text
    print("  ✅ [ИСПРАВЛЕНО] Запрос без 'text' возвращает понятную ошибку HTTP 400 вместо падения 500")
    return True

def test_7_visual_commands_missing_id_handled():
    print("[7/8] Тест устойчивости visual_commands к узлам без 'id'...")
    asst = MockAssistant()
    vc = visual_commands.VisualCommandManager(asst)

    flow = {
        "id": "safe_no_id_flow",
        "name": "No ID Flow",
        "nodes": [{"type": "action", "subType": "delay", "value": "0.01"}],
        "edges": []
    }
    vc.flows.append(flow)
    try:
        res = asyncio.run(vc.execute_flow("safe_no_id_flow"))
        assert res.get("ok") is True, f"Ожидался ok: True, получено: {res}"
        print("  ✅ [ИСПРАВЛЕНО] Граф визуальных команд автоматически присвоил ID и выполнился без сбоя")
        return True
    finally:
        vc.delete_flow("safe_no_id_flow")

def test_8_sensitive_file_read_blocked():
    print("[8/8] Тест блокировки чтения конфигов через tool_read_file...")
    asst = MockAssistant()
    t = tools.Tools(asst)

    res = t.tool_read_file(os.path.join(PROJECT_DIR, "config.py"))
    assert "заблокирован" in res.lower(), f"Чтение конфига не заблокировано: {res}"
    print("  ✅ [ИСПРАВЛЕНО] Прямое чтение config.py заблокировано политикой безопасности")
    return True

if __name__ == "__main__":
    print("\n" + "#" * 76)
    print("  🛡️ ПРОВЕРКА УСТРАНЕНИЯ УЯЗВИМОСТЕЙ И СТАБИЛЬНОСТИ АССИСТЕНТА МИЯ")
    print("#" * 76 + "\n")

    all_passed = True
    tests = [
        test_1_path_traversal_blocked,
        test_2_scenario_keyerror_handled,
        test_3_powershell_rce_blocked,
        test_4_sandbox_escape_prevented,
        test_5_xss_upload_blocked,
        test_6_chat_missing_text_validated,
        test_7_visual_commands_missing_id_handled,
        test_8_sensitive_file_read_blocked,
    ]

    for fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"  ❌ Ошибка теста: {e}")
            all_passed = False

    print("\n" + "#" * 76)
    if all_passed:
        print("  🎉 ВСЕ 8 УЯЗВИМОСТЕЙ И СБОЕВ УСПЕШНО УСТРАНЕНЫ! СИСТЕМА ЗАЩИЩЕНА.")
    else:
        print("  ⚠️ Некоторые тесты не прошли.")
    print("#" * 76 + "\n")
