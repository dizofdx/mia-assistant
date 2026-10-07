# visual_commands.py — Движок визуального редактора команд Мии (как в Astra на knice.tech)
import os, sys, json, asyncio, subprocess, webbrowser
from typing import List, Dict, Any

VISUAL_FLOWS_FILE = os.path.join(os.path.dirname(__file__), "scenarios", "visual_flows.json")

DEFAULT_FLOWS = [
    {
        "id": "youtube_lofi",
        "name": "Открыть YouTube и включить lo-fi",
        "category": "Медиа",
        "icon": "youtube",
        "description": "Открывает YouTube в браузере, вводит поиск lofi и запускает музыку",
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger",
                "subType": "hotkey",
                "title": "Хоткей",
                "value": "Alt + Y",
                "voicePhrase": "открой ютуб",
                "x": 60,
                "y": 140
            },
            {
                "id": "node_2",
                "type": "action",
                "subType": "open_url",
                "title": "Открыть URL",
                "value": "https://www.youtube.com/results?search_query=lofi+hip+hop",
                "x": 340,
                "y": 140
            },
            {
                "id": "node_3",
                "type": "action",
                "subType": "speak",
                "title": "Голос Мии",
                "value": "Открываю YouTube с расслабляющей музыкой lo-fi!",
                "x": 620,
                "y": 140
            }
        ],
        "edges": [
            {"from": "node_1", "to": "node_2"},
            {"from": "node_2", "to": "node_3"}
        ]
    },
    {
        "id": "yandex_wave",
        "name": "Включить Мою Волну",
        "category": "Медиа",
        "icon": "music",
        "description": "Запускает Яндекс Музыку и активирует персональную Мою Волну",
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger",
                "subType": "voice",
                "title": "Голос",
                "value": "моя волна",
                "voicePhrase": "включи мою волну",
                "x": 60,
                "y": 140
            },
            {
                "id": "node_2",
                "type": "action",
                "subType": "yandex_wave",
                "title": "Моя Волна",
                "value": "play_wave",
                "x": 340,
                "y": 140
            },
            {
                "id": "node_3",
                "type": "action",
                "subType": "speak",
                "title": "Голос Мии",
                "value": "Включаю твою любимую Мою Волну!",
                "x": 620,
                "y": 140
            }
        ],
        "edges": [
            {"from": "node_1", "to": "node_2"},
            {"from": "node_2", "to": "node_3"}
        ]
    },
    {
        "id": "focus_mode",
        "name": "Режим фокуса (Pomodoro)",
        "category": "Фокус",
        "icon": "zap",
        "description": "Сворачивает лишние окна, включает тишину и сообщает о старте работы",
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger",
                "subType": "hotkey",
                "title": "Хоткей",
                "value": "Ctrl + Shift + F",
                "voicePhrase": "режим фокуса",
                "x": 60,
                "y": 140
            },
            {
                "id": "node_2",
                "type": "action",
                "subType": "minimize_all",
                "title": "Свернуть все окна",
                "value": "minimize",
                "x": 340,
                "y": 80
            },
            {
                "id": "node_3",
                "type": "action",
                "subType": "speak",
                "title": "Голос Мии",
                "value": "Режим фокуса активирован. Никаких отвлечений на двадцать пять минут!",
                "x": 620,
                "y": 140
            }
        ],
        "edges": [
            {"from": "node_1", "to": "node_2"},
            {"from": "node_2", "to": "node_3"}
        ]
    },
    {
        "id": "lock_pc",
        "name": "Заблокировать компьютер",
        "category": "Система",
        "icon": "lock",
        "description": "Быстро блокирует экран рабочего стола Windows",
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger",
                "subType": "voice",
                "title": "Голос",
                "value": "заблокируй пк",
                "voicePhrase": "заблокируй пк",
                "x": 60,
                "y": 140
            },
            {
                "id": "node_2",
                "type": "action",
                "subType": "lock_screen",
                "title": "Блокировка",
                "value": "lock",
                "x": 340,
                "y": 140
            },
            {
                "id": "node_3",
                "type": "action",
                "subType": "speak",
                "title": "Голос Мии",
                "value": "Компьютер заблокирован.",
                "x": 620,
                "y": 140
            }
        ],
        "edges": [
            {"from": "node_1", "to": "node_2"},
            {"from": "node_2", "to": "node_3"}
        ]
    }
]

class VisualCommandManager:
    def __init__(self, assistant):
        self.assistant = assistant
        self.flows: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        os.makedirs(os.path.dirname(VISUAL_FLOWS_FILE), exist_ok=True)
        if os.path.exists(VISUAL_FLOWS_FILE):
            try:
                with open(VISUAL_FLOWS_FILE, "r", encoding="utf-8") as f:
                    self.flows = json.load(f)
                    return
            except Exception as e:
                print(f"[VisualCommands] Ошибка загрузки {VISUAL_FLOWS_FILE}: {e}")
        self.flows = list(DEFAULT_FLOWS)
        self._save()

    def _save(self):
        try:
            with open(VISUAL_FLOWS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.flows, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[VisualCommands] Ошибка сохранения {VISUAL_FLOWS_FILE}: {e}")

    def list_flows(self) -> List[Dict[str, Any]]:
        return self.flows

    def get_flow(self, flow_id: str):
        target = (flow_id or "").lower().strip()
        alias_map = {
            "фокус": "focus_mode",
            "отдых": "rest_mode",
            "игра": "game_mode",
            "игры": "game_mode",
            "стим": "game_mode",
            "steam": "game_mode",
            "гейминг": "game_mode",
            "лофай": "youtube_lofi",
            "волна": "yandex_wave",
        }
        target = alias_map.get(target, target)
        for f in self.flows:
            f_id = (f.get("id") or "").lower().strip()
            f_name = (f.get("name") or "").lower().strip()
            if f_id == target or f_name == target or target in f_id or target in f_name:
                return f
        return None

    def save_flow(self, flow_data: Dict[str, Any]):
        flow_id = flow_data.get("id")
        if not flow_id:
            import time
            flow_id = f"flow_{int(time.time())}"
            flow_data["id"] = flow_id
        
        updated = False
        for i, f in enumerate(self.flows):
            if f.get("id") == flow_id:
                self.flows[i] = flow_data
                updated = True
                break
        if not updated:
            self.flows.append(flow_data)
        self._save()
        return flow_data

    def delete_flow(self, flow_id: str):
        self.flows = [f for f in self.flows if f.get("id") != flow_id]
        self._save()
        return True

    async def execute_flow(self, flow_id: str) -> Dict[str, Any]:
        """Исполняет шаги визуальной команды по графу связей."""
        flow = self.get_flow(flow_id)
        if not flow:
            return {"ok": False, "error": f"Команда {flow_id} не найдена"}

        nodes_by_id = {n["id"]: n for n in flow.get("nodes", [])}
        edges = flow.get("edges", [])

        # Поиск стартовых узлов (у которых нет входящих ребер)
        dest_nodes = {e["to"] for e in edges}
        start_nodes = [n for n in flow.get("nodes", []) if n["id"] not in dest_nodes]
        if not start_nodes and flow.get("nodes"):
            start_nodes = [flow["nodes"][0]]

        executed_steps = []

        async def run_node(node):
            n_type = node.get("type", "")
            sub = node.get("subType", "")
            val = node.get("value", "")

            step_info = {"id": node["id"], "title": node.get("title", ""), "status": "running"}

            try:
                if n_type == "trigger":
                    step_info["result"] = f"Триггер сработал: {val}"

                elif n_type == "condition":
                    # Проверка процесса
                    if sub == "process_running":
                        import psutil
                        proc_name = val.lower().strip()
                        running = any(proc_name in (p.name().lower() if p.name() else "") for p in psutil.process_iter(['name']))
                        step_info["result"] = f"Процесс {val}: {'запущен' if running else 'не найден'}"
                        if not running and node.get("stopIfFalse", True):
                            step_info["status"] = "skipped"
                            executed_steps.append(step_info)
                            return False

                elif n_type == "action":
                    if sub == "open_url":
                        url = val if val.startswith("http") else "https://" + val
                        if hasattr(self.assistant, "tools"):
                            self.assistant.tools.tool_open_website(url)
                        else:
                            webbrowser.open(url)
                        step_info["result"] = f"Открыта ссылка: {url}"

                    elif sub == "open_app":
                        res = self.assistant.tools.tool_open_program(val)
                        step_info["result"] = str(res)

                    elif sub == "delay":
                        try:
                            secs = float(val or 1.0)
                            await asyncio.sleep(secs)
                            step_info["result"] = f"Пауза {secs} сек завершена"
                        except Exception:
                            pass

                    elif sub == "screenshot":
                        path = await asyncio.to_thread(self.assistant.tools.tool_screenshot)
                        step_info["result"] = f"Скриншот сохранен: {path}"

                    elif sub == "yandex_wave":
                        await asyncio.to_thread(self.assistant.tools.tool_play_yandex_music, "моя волна")
                        step_info["result"] = "Моя Волна запущена"

                    elif sub == "minimize_all":
                        self.assistant.tools.tool_window_control("minimize_all")
                        step_info["result"] = "Все окна свернуты"

                    elif sub == "lock_screen":
                        self.assistant.tools.tool_window_control("lock_pc")
                        step_info["result"] = "ПК заблокирован"

                    elif sub == "speak":
                        if not getattr(self.assistant, "is_muted", False):
                            asyncio.create_task(self.assistant.voice.speak(val))
                        step_info["result"] = f"Озвучено: {val}"

                    elif sub == "powershell":
                        res = subprocess.run(["powershell", "-NoProfile", "-Command", val], capture_output=True, text=True, timeout=10)
                        step_info["result"] = (res.stdout or res.stderr or "Выполнено").strip()[:200]

                    elif sub == "media_control":
                        # New values may be encoded as ``player:action`` while
                        # old saved flows contain only ``action``.
                        media_value = str(val or "play_pause")
                        media_player = None
                        media_action = media_value
                        if ":" in media_value:
                            media_player, media_action = media_value.split(":", 1)
                        res = self.assistant.tools.tool_media_control(media_action, media_player)
                        step_info["result"] = str(res)

                    elif sub == "volume":
                        res = self.assistant.tools.tool_volume(val)
                        step_info["result"] = str(res)

                elif n_type == "notification":
                    if sub == "chime":
                        if hasattr(self.assistant.voice, "play_cue_sync"):
                            self.assistant.voice.play_cue_sync("done", wait=False)
                        step_info["result"] = "Звуковой сигнал проигран"
                    elif sub == "telegram":
                        if hasattr(self.assistant, "notify_admin_sync"):
                            self.assistant.notify_admin_sync(f"🔔 <b>[Команда: {flow['name']}]</b>\n{val}")
                        step_info["result"] = "Уведомление отправлено в Telegram"

                step_info["status"] = "success"
                executed_steps.append(step_info)
                return True

            except Exception as e:
                step_info["status"] = "error"
                step_info["error"] = str(e)
                executed_steps.append(step_info)
                return False

        # Последовательный запуск от стартовых узлов по рёбрам
        current_node_ids = [n["id"] for n in start_nodes]
        visited = set()

        while current_node_ids:
            next_ids = []
            for nid in current_node_ids:
                if nid in visited or nid not in nodes_by_id:
                    continue
                visited.add(nid)
                node = nodes_by_id[nid]
                ok = await run_node(node)
                if ok:
                    # Ищем дочерние узлы
                    children = [e["to"] for e in edges if e["from"] == nid]
                    next_ids.extend(children)
            current_node_ids = next_ids

        return {"ok": True, "flow_id": flow_id, "name": flow.get("name", ""), "steps": executed_steps}
