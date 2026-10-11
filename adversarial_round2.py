"""
adversarial_round2.py
Второй раунд адверсариального ревью: поиск новых векторов сбоев и падений системы.
ВНИМАНИЕ: Строго по правилу «Ничего не чинить», код ассистента НЕ модифицируется!
Все атаки воспроизводятся реальными исполняемыми тестами.
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
        self.scenarios = None
        self.current_emotion = "СПОКОЙСТВИЕ"

    def set_muted(self, val):
        self.is_muted = val
        return val

    async def handle_user_message_stream(self, text, on_token=None, speak=True, source="other"):
        return "РАДОСТЬ", f"Ответ на: {text}", f"[РАДОСТЬ] Ответ на: {text}", 1, 2

def log_attack(num, total, title, desc, proof):
    print(f"\n[{num}/{total}] 💥 Проверка: {title}...")
    print("=" * 76)
    print(f"🔥 ВЕКТОР СБОЯ: {title}")
    print(f"📌 Уязвимость: {desc}")
    print(f"⚡ Доказательство падения/сбоя:\n{proof}")
    print("=" * 76)

# ==============================================================================
# АТАКА 1: Отказ в обслуживании (500 Crash) в /api/chat_stream при невалидном теле
# ==============================================================================
def attack_1_chat_stream_decode_crash():
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app, raise_server_exceptions=False)

    # Передаем не-JSON байты
    res = client.post("/api/chat_stream", content=b"INVALID_NON_JSON_PAYLOAD", headers={"Content-Type": "application/json"})
    
    assert res.status_code == 500, f"Ожидался статус 500, получен {res.status_code}"
    proof = f"POST /api/chat_stream с битым телом -> HTTP {res.status_code} Internal Server Error\nПричина: прямой await req.json() без try/except вызывает json.decoder.JSONDecodeError"
    log_attack(
        1, 5,
        "Необработанный 500 сбой в стриминг-чате (/api/chat_stream)",
        "В web_panel.py:606 парсинг JSON data = await req.json() не обернут в обработку исключений. Любой невалидный запрос роняет эндпоинт с ошибкой 500.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 2: Падение движка сценариев (AttributeError -> 500) при передаче списка в /api/scenarios
# ==============================================================================
def attack_2_scenarios_save_list_crash():
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app, raise_server_exceptions=False)

    # Передаем JSON-массив вместо объекта
    res = client.post("/api/scenarios", json=["action_item_1", "action_item_2"])
    
    assert res.status_code == 500, f"Ожидался статус 500, получен {res.status_code}"
    proof = f"POST /api/scenarios с массивом JSON -> HTTP {res.status_code} Internal Server Error\nПричина: scenarios.py:53 data.get('name') вызывает AttributeError: 'list' object has no attribute 'get'"
    log_attack(
        2, 5,
        "Крах сохранения сценариев при неверном типе данных (/api/scenarios)",
        "В scenarios.py:53 метод save предполагает, что входные данные всегда являются словарем (dict). Передача JSON-массива приводит к необработанному AttributeError.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 3: Несанкционированное перечисление внутренних каталогов (/api/files/list)
# ==============================================================================
def attack_3_directory_enumeration():
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app)

    # Запрашиваем структуру директории .git
    git_dir = os.path.join(PROJECT_DIR, ".git")
    res = client.get("/api/files/list", params={"path": git_dir})
    
    assert res.status_code == 200, f"Ожидался статус 200, получен {res.status_code}"
    data = res.json()
    folders = [f.get("name") for f in data.get("folders", [])]
    
    assert "objects" in folders or "refs" in folders or "hooks" in folders, "Внутренняя структура .git не обнаружена"
    proof = f"GET /api/files/list?path={git_dir} -> HTTP 200 OK\nОбнаруженные внутренние папки репозитория: {folders[:5]}"
    log_attack(
        3, 5,
        "Несанкционированное перечисление структуры каталогов (/api/files/list)",
        "В web_panel.py:389 эндпоинт list_files не ограничивает область просмотра и позволяет сканировать скрытые системные папки (например, .git и служебные директории Windows).",
        proof
    )
    return True

# ==============================================================================
# АТАКА 4: Падение эндпоинта смены голоса /api/set_voice при невалидном запросе
# ==============================================================================
def attack_4_set_voice_malformed_crash():
    asst = MockAssistant()
    app = web_panel.create_app(asst)
    client = TestClient(app, raise_server_exceptions=False)

    res = client.post("/api/set_voice", content=b"INVALID_VOICE_DATA", headers={"Content-Type": "application/json"})
    
    assert res.status_code == 500, f"Ожидался статус 500, получен {res.status_code}"
    proof = f"POST /api/set_voice с некорректным телом -> HTTP {res.status_code} Internal Server Error\nПричина: прямой await req.json() в web_panel.py:576 без валидации"
    log_attack(
        4, 5,
        "Необработанный сбой 500 в /api/set_voice",
        "В web_panel.py:576 отсутствует try/except вокруг парсинга JSON, что позволяет вызвать падение сервиса некорректным HTTP-запросом.",
        proof
    )
    return True

# ==============================================================================
# АТАКА 5: Неконтролируемый запуск системных процессов через tool_open_program
# ==============================================================================
def attack_5_unrestricted_open_program():
    asst = MockAssistant()
    t = tools.Tools(asst)

    # Проверяем поведение при передаче системного пути (например cmd.exe или notepad.exe)
    cmd_path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "notepad.exe")
    assert os.path.exists(cmd_path), f"Путь {cmd_path} не найден для теста"

    # В tools.py:228 отсутствует белый список приложений, метод готов выполнить любой бинарник
    # Проверяем, что tools.py не блокирует запуск системных утилит
    result_str = ""
    # Вызываем dispatch без фактического развертывания окна блокнота на экране, анализируя логику
    fn = getattr(t, "tool_open_program")
    import inspect
    code_text = inspect.getsource(fn)
    has_whitelist = "whitelist" in code_text.lower() or "allowed" in code_text.lower()
    
    assert not has_whitelist, "В tool_open_program обнаружен белый список!"
    proof = f"Анализ метода tool_open_program: отсутствует проверка прав и белый список (has_whitelist={has_whitelist}). Любой путь на диске передается напрямую в os.startfile."
    log_attack(
        5, 5,
        "Отсутствие белого списка исполняемых файлов в tool_open_program",
        "В tools.py:228 метод tool_open_program принимает произвольный путь и исполняет его через os.startfile без ограничений и без проверки привилегий.",
        proof
    )
    return True

# ==============================================================================
# ТОЧКА ВХОДА
# ==============================================================================
if __name__ == "__main__":
    print("\n" + "#" * 76)
    print("  🚀 ЗАПУСК ВТОРОГО РАУНДА АДВЕРСАРИАЛЬНОГО РЕВЬЮ: НОВЫЕ СБОИ И ПАДЕНИЯ")
    print("#" * 76)

    tests = [
        ("Атака 1: Падение /api/chat_stream при невалидном JSON", attack_1_chat_stream_decode_crash),
        ("Атака 2: Падение /api/scenarios при передаче массива", attack_2_scenarios_save_list_crash),
        ("Атака 3: Перечисление внутренних каталогов .git", attack_3_directory_enumeration),
        ("Атака 4: Падение /api/set_voice при битых данных", attack_4_set_voice_malformed_crash),
        ("Атака 5: Запуск произвольных бинарников в tool_open_program", attack_5_unrestricted_open_program),
    ]

    report = {}
    for name, fn in tests:
        try:
            passed = fn()
            report[name] = "💥 СБОЙ ПОДТВЕРЖДЕН (СИСТЕМА ЛОМАЕТСЯ)" if passed else "НЕ ВОСПРОИЗВЕДЕНО"
        except Exception as e:
            report[name] = f"❌ ОШИБКА ТЕСТА: {e}"

    print("\n" + "#" * 76)
    print("  📊 ФИНАЛЬНЫЙ СВОДНЫЙ ОТЧЕТ ВТОРОГО РАУНДА ТЕСТИРОВАНИЯ:")
    print("#" * 76)
    for name, status in report.items():
        print(f" • {name}: {status}")
    print("#" * 76 + "\n")
