# scenarios.py — движок сценариев (JSON: триггер + действия)
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json, os, asyncio, datetime, webbrowser, subprocess

class ScenarioEngine:
    def __init__(self, assistant, folder="scenarios"):
        self.a, self.folder = assistant, folder
        self.last_run = {}
        os.makedirs(folder, exist_ok=True)

    def list_all(self):
        out = []
        if not os.path.exists(self.folder):
            return out
        for f in sorted(os.listdir(self.folder)):
            if f == "visual_flows.json":
                continue
            if f.endswith(".json"):
                p = os.path.join(self.folder, f)
                try:
                    with open(p, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if isinstance(data, dict) and "name" in data:
                            out.append(data)
                except Exception:
                    pass
        return out

    def get(self, name):
        if not name or not isinstance(name, str):
            return None
        target = name.lower().strip().replace(".json", "")
        # 1. Точное совпадение (без учёта регистра)
        for s in self.list_all():
            s_name = (s.get("name") or "").lower().strip().replace(".json", "")
            if s_name == target:
                return s
        # 2. Поиск по подстроке (например "запусти отдых" или "сценарий отдых" -> найдет "отдых")
        for s in self.list_all():
            s_name = (s.get("name") or "").lower().strip()
            if s_name and (s_name in target or target in s_name):
                return s
        return None

    def save(self, data):
        safe = "".join(c for c in data.get("name", "scenario") if c.isalnum() or c in " _-").strip() or "scenario"
        target_path = os.path.join(self.folder, safe + ".json")
        with open(target_path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

    def delete(self, name):
        if not os.path.exists(self.folder):
            return
        target = (name or "").lower().strip().replace(".json", "")
        for f in list(os.listdir(self.folder)):
            if f.endswith(".json"):
                p = os.path.join(self.folder, f)
                should_remove = False
                try:
                    with open(p, "r", encoding="utf-8") as fp:
                        sc_data = json.load(fp)
                    sc_name = (sc_data.get("name") or "").lower().strip().replace(".json", "")
                    if sc_name == target:
                        should_remove = True
                except Exception:
                    pass
                if should_remove:
                    try:
                        os.remove(p)
                    except Exception as e:
                        print(f"[Scenarios] Ошибка удаления {p}: {e}")

    async def run(self, name):
        s = self.get(name)
        if not s:
            available = [x.get("name") for x in self.list_all() if x.get("name")]
            msg = f"Сценарий '{name}' не найден. Доступные: {', '.join(available)}"
            print(f"[Scenarios] {msg}")
            if hasattr(self.a, "notify_admin_sync"):
                self.a.notify_admin_sync(f"[Внимание] {msg}")
            return msg
        real_name = s.get("name", name)
        print(f"[Scenarios] Запуск сценария: {real_name}")
        for act in s.get("actions", []):
            try:
                await self.do_action(act)
            except Exception as e:
                print(f"[Scenarios] Ошибка действия {act.get('type')}: {e}")
        return f"Сценарий '{real_name}' успешно выполнен."

    async def do_action(self, act):
        t = act.get("type")
        if t == "speak":
            try:
                await self.a.voice.speak(act["text"])                      # сказать дословно
            except Exception as e:
                print(f"[Scenarios] Ошибка озвучки: {e}")
        elif t == "say":
            await self.a.handle_user_message(act["text"])              # ответить "живо" через LLM
        elif t == "open_website":
            url = act.get("url", "")
            if not url.startswith("http"):
                url = "https://" + url
            if hasattr(self.a, "tools"):
                self.a.tools.tool_open_website(url)
            else:
                try:
                    os.startfile(url)
                except Exception:
                    webbrowser.open(url)

        elif t == "open_program":
            p = act.get("path", "")
            if not os.path.exists(p):
                print(f"[Scenarios] Файл программы не найден: {p}")
                return
            d = os.path.dirname(p) or None

            # Если запускаем Zapret:
            if "zapret" in p.lower():
                try:
                    out = subprocess.run('tasklist /FI "IMAGENAME eq winws.exe"', shell=True, capture_output=True, text=True).stdout
                    if "winws.exe" in out:
                        print("[Scenarios] Zapret (winws.exe) уже запущен и работает!")
                        return
                except Exception:
                    pass

                # Запуск с повышением прав через ShellExecute runas
                try:
                    os.startfile(p, "runas")
                    print(f"[Scenarios] Запущен Zapret (RunAs): {p}")
                    return
                except Exception as e:
                    print(f"[Scenarios] os.startfile RunAs: {e}, запуск через subprocess")
                    try:
                        subprocess.Popen([p], cwd=d, shell=True)
                        return
                    except Exception as e2:
                        print(f"[Scenarios] Ошибка запуска Zapret: {e2}")

            # Ярлыки (.lnk)
            if p.lower().endswith(".lnk"):
                try:
                    os.startfile(p)
                    print(f"[Scenarios] Ярлык запущен (startfile): {p}")
                    return
                except Exception as e_lnk:
                    try:
                        subprocess.Popen(['explorer.exe', p])
                        print(f"[Scenarios] Ярлык запущен (explorer): {p}")
                        return
                    except Exception as e_exp:
                        print(f"[Scenarios] Ошибка запуска ярлыка {p}: {e_exp}")

            # Обычные программы (.exe / .bat)
            try:
                os.startfile(p)
            except Exception as e:
                print(f"[Scenarios] os.startfile ({e}), пробуем запуск через Shell/cmd start...")
                env = os.environ.copy()
                env["__COMPAT_LAYER"] = "RunAsInvoker"
                try:
                    subprocess.Popen(f'cmd.exe /c start "" "{p}"', cwd=d, shell=True, env=env)
                except Exception as e_cmd:
                    try:
                        os.startfile(p, "runas")
                    except Exception as e_runas:
                        try:
                            subprocess.Popen(f'"{p}"', cwd=d, shell=True, env=env)
                        except Exception as e2:
                            print(f"[Scenarios] Ошибка запуска {p}: {e2}")

        elif t == "play_music" or t == "yandex_music":
            try:
                if hasattr(self.a, "tools"):
                    self.a.tools.tool_play_yandex_music()
                else:
                    userprofile = os.environ.get("USERPROFILE", r"C:\Users\7ims (admin)")
                    lnk = os.path.join(userprofile, "Desktop", "Яндекс Музыка.lnk")
                    if os.path.exists(lnk):
                        subprocess.Popen(['explorer.exe', lnk])
            except Exception as e:
                print(f"[Scenarios] Ошибка запуска музыки: {e}")
        elif t == "emote":
            await self.a.avatar.set_emotion(act["name"])
        elif t == "wait":
            await asyncio.sleep(act.get("seconds", 1))

    async def scheduler_loop(self):
        while True:
            now = datetime.datetime.now().strftime("%H:%M")
            for s in self.list_all():
                tr = s.get("trigger", {})
                if (s.get("enabled") and tr.get("type") == "schedule"
                        and tr.get("time") == now and self.last_run.get(s["name"]) != now):
                    self.last_run[s["name"]] = now
                    asyncio.create_task(self.run(s["name"]))
            await asyncio.sleep(20)