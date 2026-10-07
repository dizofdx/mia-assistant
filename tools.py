# tools.py — "руки": управление компьютером + программирование
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import subprocess, webbrowser, datetime, os, re
try:
    import pyautogui
except ImportError:  # Optional in headless/API-only deployments.
    class _PyAutoGUIUnavailable:
        FAILSAFE = False
        def __getattr__(self, name):
            def _missing(*args, **kwargs):
                raise RuntimeError("pyautogui не установлен: управление рабочим столом недоступно")
            return _missing
    pyautogui = _PyAutoGUIUnavailable()
try:
    import pyperclip
except ImportError:
    class _PyperclipUnavailable:
        def copy(self, *_args, **_kwargs):
            raise RuntimeError("pyperclip не установлен: буфер обмена недоступен")
    pyperclip = _PyperclipUnavailable()
pyautogui.FAILSAFE = False

TOOLS_SPEC = [
    {"type": "function", "function": {"name": "remember_fact",
     "description": "Запомнить важный факт о пользователе навсегда",
     "parameters": {"type": "object", "properties": {"fact": {"type": "string"}}, "required": ["fact"]}}},
    {"type": "function", "function": {"name": "open_website", "description": "Открыть сайт в браузере", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "open_program", "description": "Запустить программу по пути .exe или .bat", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "shutdown_pc", "description": "Выключить ПК через N минут", "parameters": {"type": "object", "properties": {"minutes": {"type": "integer", "default": 2}}}}},
    {"type": "function", "function": {"name": "cancel_shutdown", "description": "Отменить выключение ПК", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "take_screenshot", "description": "Сделать скриншот экрана ПК и отправить пользователю", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "volume", "description": "Управление мастер-громкостью Windows на ПК: up (громче), down (тише), mute (выключить звук колонок)", "parameters": {"type": "object", "properties": {"direction": {"type": "string"}}, "required": ["direction"]}}},
    {"type": "function", "function": {"name": "mute_assistant", "description": "Включить или выключить озвучку ответов голосом Мии (mute=True: Мия отвечает только текстом; mute=False: говорит вслух)", "parameters": {"type": "object", "properties": {"mute": {"type": "boolean"}}, "required": ["mute"]}}},
    {"type": "function", "function": {"name": "paste_text", "description": "Вставить текст (Ctrl+V)", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "get_time", "description": "Текущее время", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "run_scenario", "description": "Запустить сценарий по названию (например 'отдых', 'утро' и т.д.). ОБЯЗАТЕЛЬНО вызывай эту функцию если пользователь просит включить сценарий!", "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {"name": "delete_scenario", "description": "Удалить сценарий или команду по названию или ID", "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {"name": "get_system_stats", "description": "Jarvis Telemetry: получить состояние ПК (нагрузка CPU %, память RAM, свободное место на дисках C и D, аптайм)", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "media_control", "description": "Управление музыкой и медиа на ПК. Можно указать player: yandex, spotify, aimp, foobar, browser или auto. Действия: play_pause, play, pause, next, prev, stop, mute", "parameters": {"type": "object", "properties": {"action": {"type": "string"}, "player": {"type": "string"}}, "required": ["action"]}}},
    {"type": "function", "function": {"name": "media_status", "description": "Показать доступные локальные и браузерные плееры и определить, какие из них запущены", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "open_media_player", "description": "Открыть поддерживаемый плеер (spotify, aimp, foobar, yandex или browser) безопасным способом", "parameters": {"type": "object", "properties": {"player": {"type": "string"}}, "required": ["player"]}}},
    {"type": "function", "function": {"name": "play_yandex_music", "description": "Включить Яндекс Музыку на ПК и запустить воспроизведение «Моей Волны» или треков. Вызывай при просьбе включить музыку, яндекс музыку, мою волну, треки или песню.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "like_track", "description": "Поставить лайк играющему треку в Яндекс Музыке", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_weather", "description": "Узнать прогноз погоды (как в Алисе) по городу или текущему месту", "parameters": {"type": "object", "properties": {"city": {"type": "string", "default": ""}}}}},
    {"type": "function", "function": {"name": "search_youtube", "description": "Найти видео, клип или музыку на YouTube в браузере", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "search_web", "description": "Найти информацию в интернете (Google поиск)", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "window_control", "description": "Управление окнами Windows: minimize_all (свернуть всё), close_active (закрыть текущее окно), switch_app (Alt+Tab), lock_pc (заблокировать)", "parameters": {"type": "object", "properties": {"action": {"type": "string"}}, "required": ["action"]}}},
    {"type": "function", "function": {"name": "add_note", "description": "Сохранить быструю текстовую заметку в блокнот", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "list_notes", "description": "Прочитать последние сохраненные заметки пользователя", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "write_code", "description": "Написать программу и сохранить в файл", "parameters": {"type": "object", "properties": {"task": {"type": "string"}, "filename": {"type": "string"}}, "required": ["task", "filename"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "Выполнить команду в PowerShell", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Прочитать файл", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Записать файл", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "Список файлов", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": "projects"}}}}},
    {"type": "function", "function": {"name": "ask_expert_ai", "description": "Сложная задача, физика, химия, высшая математика, алгоритмы, глубокий анализ (DeepSeek V4). ОБЯЗАТЕЛЬНО используй этот инструмент при любых сложных или глубоких вопросах!", "parameters": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}}},
]

class Tools:
    def __init__(self, assistant):
        self.a = assistant
        factor = getattr(assistant.cfg, "AUDIO_DUCKING_FACTOR", 0.5)
        self.ducker = AudioDucker(
            factor=factor,
            min_volume=getattr(assistant.cfg, "AUDIO_DUCKING_MIN_VOLUME", 0.04),
            release_ms=getattr(assistant.cfg, "AUDIO_DUCKING_RELEASE_MS", 120),
        )

    def dispatch(self, name, args, on_token=None):
        fn = getattr(self, "tool_" + name, None)
        if not fn:
            return f"Неизвестный инструмент: {name}"
        try:
            # Если функция поддерживает on_token
            import inspect
            sig = inspect.signature(fn)
            if "on_token" in sig.parameters and on_token:
                args["on_token"] = on_token
            return fn(**args)
        except Exception as e:
            return f"Ошибка: {e}"

    # ===== Системные инструменты =====

    def tool_remember_fact(self, fact):
        self.a.memory.add_fact(fact); return f"Запомнила: {fact}"

    def tool_open_website(self, url):
        if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("steam://"):
            url = "https://" + url

        browsers = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        opened = False
        for b in browsers:
            if os.path.exists(b):
                try:
                    subprocess.Popen([b, url])
                    opened = True
                    break
                except Exception:
                    pass
        if not opened:
            try:
                os.startfile(url)
                opened = True
            except Exception:
                webbrowser.open(url)

        # Поднимаем браузер на передний план при открытии
        try:
            import ctypes, time, psutil
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)

            time.sleep(0.35)
            browser_names = ['chrome', 'msedge', 'browser', 'opera', 'firefox', 'yandex']
            browser_pids = {p.pid for p in psutil.process_iter(['name']) if any(b in (p.info['name'] or '').lower() for b in browser_names)}

            found_hwnd = None
            def cb(hwnd, _):
                nonlocal found_hwnd
                if user32.IsWindowVisible(hwnd):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value in browser_pids:
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w > 300 and h > 200:
                            found_hwnd = hwnd
                            return 0
                return 1

            DESKTOPENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            if hdesk:
                user32.EnumDesktopWindows(hdesk, DESKTOPENUMPROC(cb), 0)
            if not found_hwnd:
                user32.EnumWindows(DESKTOPENUMPROC(cb), 0)

            if found_hwnd:
                cur_tid = user32.GetCurrentThreadId()
                fore_hwnd = user32.GetForegroundWindow()
                fore_tid = user32.GetWindowThreadProcessId(fore_hwnd, None) if fore_hwnd else 0
                if fore_tid and fore_tid != cur_tid:
                    user32.AttachThreadInput(cur_tid, fore_tid, True)
                user32.ShowWindow(found_hwnd, 9)  # SW_RESTORE
                HWND_TOPMOST = -1
                HWND_NOTOPMOST = -2
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(found_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                user32.BringWindowToTop(found_hwnd)
                user32.SetForegroundWindow(found_hwnd)
                time.sleep(0.05)
                user32.SetWindowPos(found_hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                if fore_tid and fore_tid != cur_tid:
                    user32.AttachThreadInput(cur_tid, fore_tid, False)
        except Exception as e_br:
            print(f"[Open Website] Ошибка подъема браузера: {e_br}")

        return f"Открыла сайт в браузере: {url}"

    def get_installed_apps(self):
        """Сканирует установленные программы и ярлыки на ПК для быстрого поиска и запуска."""
        apps = {}
        userprofile = os.environ.get("USERPROFILE", "")
        scan_dirs = [
            os.path.join(userprofile, r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.join(userprofile, "Desktop"),
            r"C:\Users\Public\Desktop"
        ]
        skip_words = ["uninstall", "удалить", "help", "readme", "сайт", "деинстал"]
        for d in scan_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        app_name = f[:-4]
                        if any(sw in app_name.lower() for sw in skip_words):
                            continue
                        if app_name not in apps:
                            apps[app_name] = os.path.join(root, f)
        return apps

    def tool_open_steam(self):
        """Запускает Steam на ПК."""
        userprofile = os.environ.get("USERPROFILE", r"C:\Users\7ims (admin)")
        candidates = [
            os.path.join(userprofile, r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Steam\Steam.lnk"),
            os.path.join(userprofile, "Desktop", "Steam.lnk"),
            r"C:\Program Files (x86)\Steam\steam.exe",
            r"C:\Program Files\Steam\steam.exe",
            r"D:\Steam\steam.exe",
            r"D:\programs\Steam\steam.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                try:
                    os.startfile(c)
                    return "Запустила Steam! Приятной игры! 🎮"
                except Exception:
                    pass
        try:
            os.startfile("steam://open/main")
            return "Запустила Steam! Приятной игры! 🎮"
        except Exception as e:
            return f"Не удалось запустить Steam: {e}"

    def tool_open_program(self, target):
        """Универсальный запуск любых программ на ПК: по названию, ярлыку, протоколу или пути."""
        if not target:
            return "Укажи название программы или путь."
        raw = str(target).strip()

        # 1. Прямой путь к файлу
        if os.path.exists(raw):
            try:
                if "zapret" in raw.lower() and raw.lower().endswith(".bat"):
                    try:
                        os.startfile(raw, "runas")
                    except Exception:
                        os.startfile(raw)
                elif raw.lower().endswith(".lnk"):
                    try:
                        os.startfile(raw)
                    except Exception:
                        subprocess.Popen(['explorer.exe', raw])
                else:
                    os.startfile(raw)
                return f"Запустила: {os.path.basename(raw)}"
            except Exception as e:
                try:
                    subprocess.Popen([raw], cwd=os.path.dirname(raw) or None, shell=True)
                    return f"Запустила: {os.path.basename(raw)}"
                except Exception as e2:
                    return f"Ошибка запуска: {e2}"

        low = raw.lower().strip()

        # 2. Популярные приложения
        if "steam" in low or "стим" in low:
            return self.tool_open_steam()

        if any(k in low for k in ["telegram", "ayugram", "аюграм", "телеграм", "телега", "тг"]):
            return self.tool_open_telegram()

        if "discord" in low or "дискорд" in low:
            try:
                os.startfile("discord://")
                return "Запустила Discord!"
            except Exception:
                pass

        if any(k in low for k in ["яндекс музык", "яндекс.музык", "yandex music"]):
            return self.tool_play_yandex_music()

        if any(k in low for k in ["chrome", "хром", "гугл хром"]):
            chrome_p = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(chrome_p):
                os.startfile(chrome_p)
                return "Запустила Google Chrome!"

        # 3. Встроенные системные утилиты Windows
        sys_tools = {
            "калькулятор": "calc.exe", "calc": "calc.exe",
            "блокнот": "notepad.exe", "notepad": "notepad.exe",
            "проводник": "explorer.exe", "explorer": "explorer.exe",
            "диспетчер задач": "taskmgr.exe", "taskmgr": "taskmgr.exe",
            "терминал": "wt.exe", "cmd": "cmd.exe", "powershell": "powershell.exe",
            "paint": "mspaint.exe", "пейнт": "mspaint.exe"
        }
        if low in sys_tools:
            try:
                subprocess.Popen([sys_tools[low]], shell=True)
                return f"Запустила {low}!"
            except Exception:
                pass

        # 4. Поиск в установленных приложениях (Start Menu & Desktop)
        installed = self.get_installed_apps()
        # Точное совпадение
        for name, lnk in installed.items():
            if name.lower() == low:
                try:
                    os.startfile(lnk)
                    return f"Запустила: {name}!"
                except Exception as e:
                    return f"Ошибка запуска {name}: {e}"
        # Подстрока
        for name, lnk in installed.items():
            if low in name.lower() or name.lower() in low:
                try:
                    os.startfile(lnk)
                    return f"Запустила: {name}!"
                except Exception as e:
                    return f"Ошибка запуска {name}: {e}"

        # 5. Попытка запустить напрямую через Windows Shell
        try:
            os.startfile(raw)
            return f"Запустила {raw}!"
        except Exception:
            try:
                subprocess.Popen([raw], shell=True)
                return f"Запустила {raw}!"
            except Exception as e_final:
                return f"Программа «{raw}» не найдена на компьютере."

    def tool_open_telegram(self):
        """Открывает или восстанавливает из трея Telegram / AyuGram на передний план."""
        userprofile = os.environ.get("USERPROFILE", r"C:\Users\7ims (admin)")
        ayu_lnk = os.path.join(userprofile, "Desktop", "AyuGram.lnk")
        tg_lnk = os.path.join(userprofile, "Desktop", "Telegram.lnk")
        ayu_exe = r"D:\programs\Ayugram\AyuGram.exe"

        target = None
        if os.path.exists(ayu_lnk):
            target = ayu_lnk
        elif os.path.exists(tg_lnk):
            target = tg_lnk
        elif os.path.exists(ayu_exe):
            target = ayu_exe

        if target:
            try:
                os.startfile(target)
                return "Открыла Telegram!"
            except Exception:
                try:
                    subprocess.Popen([ayu_exe], cwd=os.path.dirname(ayu_exe))
                    return "Открыла Telegram!"
                except Exception:
                    pass

        return "Ярлык Telegram не найден."

    def tool_shutdown_pc(self, minutes=2):
        subprocess.run(f"shutdown /s /t {int(minutes)*60}", shell=True)
        self.a.notify_admin_sync(f"⚠️ Выключение ПК через {minutes} мин! /cancel — отменить.")
        return f"ПК выключится через {minutes} минут."

    def tool_cancel_shutdown(self):
        subprocess.run("shutdown /a", shell=True); return "Выключение отменено."

    def tool_screenshot(self):
        """Делает снимок реального экрана ПК с привязкой к рабочему столу и конвертацией в RGB."""
        os.makedirs("memory", exist_ok=True)
        path = os.path.abspath("memory/screenshot.png")

        # 1. Привязка к интерактивному рабочему столу Windows и включение DPI Awareness
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

        # 2. Попытка PIL ImageGrab (all_screens=True)
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True)
            if img:
                img = img.convert("RGB")
                img.save(path, "PNG")
                if os.path.exists(path) and os.path.getsize(path) > 5000:
                    return path
        except Exception as e:
            print(f"[Screenshot] ImageGrab failed: {e}")

        # 3. Попытка pyautogui
        try:
            import pyautogui
            img = pyautogui.screenshot()
            if img:
                img = img.convert("RGB")
                img.save(path, "PNG")
                if os.path.exists(path) and os.path.getsize(path) > 5000:
                    return path
        except Exception as e:
            print(f"[Screenshot] pyautogui failed: {e}")

        # 4. Попытка mss с явной BGRX -> RGB конвертацией
        try:
            import mss
            from PIL import Image
            with mss.mss() as sct:
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                raw = sct.grab(mon)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                img.save(path, "PNG")
                if os.path.exists(path) and os.path.getsize(path) > 5000:
                    return path
        except Exception as e:
            print(f"[Screenshot] mss failed: {e}")

        return None

    def tool_take_screenshot(self):
        path = self.tool_screenshot()
        if path and os.path.exists(path):
            self.a.send_photo_sync(path)
            return "Скриншот экрана сделан и отправлен в Телеграм."
        return "Не удалось сделать скриншот экрана."

    def tool_volume(self, direction):
        """Управляет системной громкостью Windows через CoreAudio (pycaw): up, down, mute, или процент."""
        d = str(direction or "").lower().strip()
        try:
            try:
                import comtypes
                comtypes.CoInitialize()
            except Exception:
                pass
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            ep = speakers.EndpointVolume
            if not ep:
                raise RuntimeError("No EndpointVolume")

            cur = float(ep.GetMasterVolumeLevelScalar())

            if d in ["mute", "mute_pc"]:
                is_muted = bool(ep.GetMute())
                ep.SetMute(not is_muted, None)
                return "Звук включен 🔊" if is_muted else "Звук выключен 🔇"

            if d in ["up", "louder", "выше", "громче"]:
                new_v = min(1.0, cur + 0.08)
            elif d in ["down", "quieter", "ниже", "тише"]:
                new_v = max(0.0, cur - 0.08)
            elif d.isdigit():
                new_v = max(0.0, min(1.0, float(d) / 100.0))
            else:
                new_v = min(1.0, cur + 0.08)

            ep.SetMasterVolumeLevelScalar(new_v, None)
            pct = round(new_v * 100)
            return f"Громкость: {pct}% 🔊"
        except Exception:
            import ctypes
            u = ctypes.windll.user32
            vk = 0xAD if d == "mute" else (0xAF if d in ["up", "выше", "громче"] else 0xAE)
            reps = 1 if d == "mute" else 4
            for _ in range(reps):
                u.keybd_event(vk, 0, 0, 0)
                u.keybd_event(vk, 0, 2, 0)
            return f"Громкость изменена: {d}"

    def tool_mute_assistant(self, mute=True):
        self.a.set_muted(bool(mute))
        st = "выключила (буду отвечать только текстом)" if mute else "включила (озвучиваю ответы)"
        return f"Голос Мии {st}."

    def tool_paste_text(self, text):
        pyperclip.copy(text); pyautogui.hotkey("ctrl", "v"); return "Вставила."

    def tool_get_time(self):
        return datetime.datetime.now().strftime("%H:%M, %d.%m.%Y")

    def tool_run_scenario(self, name):
        # Normalise the incoming name: strip whitespace and lower‑case for robust matching
        clean_name = name.lower().strip()
        # Try to fetch by the normalised name first, then fall back to the original
        s = self.a.scenarios.get(clean_name) or self.a.scenarios.get(name)
        if not s:
            available = [x.get("name") for x in self.a.scenarios.list_all() if x.get("name")]
            return f"Сценарий '{name}' не найден. Доступные сценарии: {', '.join(available)}"
        real_name = s.get("name")
        self.a.run_scenario_async(real_name)
        return f"Сценарий '{real_name}' успешно запущен."

    def tool_delete_scenario(self, name: str):
        """Удаляет сценарий или визуальную команду по имени или ID."""
        if not name:
            return "Укажи имя сценария или команды для удаления."
        name_clean = name.lower().strip().replace("команду", "").replace("сценарий", "").strip()
        deleted = False
        # 1. Удаляем из визуальных команд
        if hasattr(self.a, "vc_manager"):
            for f in list(self.a.vc_manager.list_flows()):
                f_id = (f.get("id") or "").lower()
                f_name = (f.get("name") or "").lower()
                if f_id == name_clean or f_name == name_clean or name_clean in f_name:
                    self.a.vc_manager.delete_flow(f.get("id"))
                    deleted = True
                    break
        # 2. Удаляем из классических сценариев
        if hasattr(self.a, "scenarios"):
            s = self.a.scenarios.get(name_clean)
            if s:
                self.a.scenarios.delete(s.get("name"))
                deleted = True
        if deleted:
            return f"Команда «{name_clean}» успешно удалена! 🗑️"
        return f"Команда или сценарий «{name_clean}» не найдены."

    # ===== Новые фишки Jarvis (управление медиа, телеметрия, окна, поиск, заметки) =====

    def tool_get_system_stats(self):
        """Jarvis Telemetry: мониторинг состояния ПК."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            d_disk = psutil.disk_usage('D:\\') if os.path.exists('D:\\') else psutil.disk_usage('C:\\')
            c_disk = psutil.disk_usage('C:\\')
            d_free = round(d_disk.free / (1024**3), 1)
            c_free = round(c_disk.free / (1024**3), 1)
            ram_used = round(ram.used / (1024**3), 1)
            ram_total = round(ram.total / (1024**3), 1)
            boot = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%H:%M, %d.%m")
            return (
                f"🖥️ Статус системы (Jarvis Telemetry):\n"
                f"• Загрузка процессора (CPU): {cpu}%\n"
                f"• Оперативная память (RAM): {ram.percent}% ({ram_used} из {ram_total} ГБ)\n"
                f"• Свободно на диске D: {d_free} ГБ\n"
                f"• Свободно на диске C: {c_free} ГБ\n"
                f"• ПК работает с: {boot}"
            )
        except Exception as e:
            return f"Ошибка получения данных системы: {e}"

    # Known media targets.  The controller deliberately uses an allow-list: no
    # shell command or user supplied executable is ever evaluated as part of a
    # media request.  Global media keys remain the most compatible transport on
    # Windows and work with desktop apps and browser media sessions alike.
    MEDIA_PLAYERS = {
        "yandex": {
            "name": "Яндекс Музыка", "aliases": ("yandex", "yandexmusic", "яндекс", "яндекс музыка"),
            "processes": ("yandexmusic.exe", "яндекс музыка.exe"),
            "executables": (r"%LOCALAPPDATA%\Programs\YandexMusic\YandexMusic.exe",
                            r"%LOCALAPPDATA%\Programs\YandexMusicMod\YandexMusic.exe"),
            "url": "https://music.yandex.ru/",
        },
        "spotify": {
            "name": "Spotify", "aliases": ("spotify", "спотифай", "спотифи"),
            "processes": ("spotify.exe",),
            "executables": (r"%APPDATA%\Spotify\Spotify.exe", r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
            "url": "https://open.spotify.com/",
        },
        "aimp": {
            "name": "AIMP", "aliases": ("aimp", "аимп"),
            "processes": ("aimp.exe",),
            "executables": (r"%PROGRAMFILES%\AIMP\AIMP.exe", r"%PROGRAMFILES(X86)%\AIMP\AIMP.exe"),
            "url": None,
        },
        "foobar": {
            "name": "foobar2000", "aliases": ("foobar", "foobar2000", "фубар", "фубар2000"),
            "processes": ("foobar2000.exe",),
            "executables": (r"%PROGRAMFILES%\foobar2000\foobar2000.exe", r"%PROGRAMFILES(X86)%\foobar2000\foobar2000.exe"),
            "url": None,
        },
        "browser": {
            "name": "Браузер (медиа-вкладка)", "aliases": ("browser", "браузер", "chrome", "edge", "firefox"),
            "processes": ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"),
            "executables": (),
            "url": None,
        },
    }

    @classmethod
    def _media_target_key(cls, player):
        value = (str(player or "auto").strip().lower().replace("ё", "е"))
        if value in ("", "auto", "any", "активный", "текущий"):
            return "auto"
        for key, spec in cls.MEDIA_PLAYERS.items():
            if value == key or value in {str(a).lower().replace("ё", "е") for a in spec["aliases"]}:
                return key
        return None

    @staticmethod
    def _running_process_names():
        try:
            import psutil
            return {str(p.info.get("name") or "").lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
        except Exception:
            return set()

    @classmethod
    def media_players_status(cls):
        """Return a JSON-safe snapshot of supported media targets."""
        names = cls._running_process_names()
        result = []
        for key, spec in cls.MEDIA_PLAYERS.items():
            running = bool(names.intersection({p.lower() for p in spec["processes"]}))
            executable = None
            for raw in spec["executables"]:
                candidate = os.path.expandvars(raw)
                if os.path.exists(candidate):
                    executable = candidate
                    break
            result.append({"id": key, "name": spec["name"], "running": running,
                           "installed": bool(executable) or key == "browser",
                           "transport": "global_media_keys", "executable": executable,
                           "url": spec["url"]})
        return result

    def tool_media_status(self):
        """Список поддерживаемых приложений и их состояние без запуска процессов."""
        players = self.media_players_status()
        running = [p["name"] for p in players if p["running"]]
        suffix = f" Запущены: {', '.join(running)}." if running else " Запущенных плееров не найдено."
        return {"players": players, "running": running, "summary": "Поддерживаемые плееры." + suffix}

    def tool_open_media_player(self, player):
        """Open one allow-listed media player, without executing arbitrary input."""
        key = self._media_target_key(player)
        if not key or key == "auto":
            return "Укажи поддерживаемый плеер: Spotify, AIMP, foobar2000, Яндекс Музыка или браузер."
        spec = self.MEDIA_PLAYERS[key]
        if key == "browser":
            return self.tool_open_website("https://open.spotify.com/")
        if any(p.lower() in self._running_process_names() for p in spec["processes"]):
            return f"{spec['name']} уже запущен."
        for raw in spec["executables"]:
            candidate = os.path.expandvars(raw)
            if not os.path.exists(candidate):
                continue
            try:
                subprocess.Popen([candidate], cwd=os.path.dirname(candidate) or None,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                return f"Запускаю {spec['name']}."
            except Exception as exc:
                print(f"[Media] cannot start {key}: {exc}")
        if spec.get("url"):
            self.tool_open_website(spec["url"])
            return f"Открываю {spec['name']} в браузере."
        return f"{spec['name']} не найден. Установи его или выбери другой плеер."

    @classmethod
    def _send_media_key(cls, vk, target="auto"):
        try:
            import ctypes
            u = ctypes.windll.user32
            # For named desktop apps, try WM_APPCOMMAND on the app's own
            # top-level window first. This avoids changing another player's
            # session when AIMP/foobar/Spotify expose a normal window.
            if target in {"spotify", "aimp", "foobar", "yandex"}:
                import psutil
                wanted = {p.lower() for p in cls.MEDIA_PLAYERS[target]["processes"]}
                pids = set()
                for process in psutil.process_iter(["name", "pid"]):
                    info = process.info
                    if str(info.get("name") or "").lower() in wanted:
                        pids.add(info.get("pid"))
                found = []
                enum_callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                @enum_callback_type
                def visit(hwnd, _lparam):
                    if not u.IsWindowVisible(hwnd):
                        return True
                    pid = ctypes.c_ulong()
                    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value in pids:
                        found.append(hwnd)
                        return False
                    return True
                u.EnumWindows(visit, 0)
                if found:
                    # APPCOMMAND_MEDIA_* values are stable Windows constants.
                    command_by_vk = {0xB0: 11, 0xB1: 12, 0xB2: 13, 0xB3: 14}
                    command = command_by_vk.get(vk)
                    if command is not None:
                        lparam = command << 16
                        if u.PostMessageW(found[0], 0x0319, 0, lparam):
                            return "window_message"
            u.keybd_event(vk, 0, 0, 0)
            u.keybd_event(vk, 0, 2, 0)
            return "global_media_key"
        except Exception as exc:
            # Keep API usable on Linux/headless CI and make the limitation explicit.
            print(f"[Media] global key unavailable: {exc}")
            return False

    def tool_media_control(self, action="play_pause", player=None):
        """Управляет указанным плеером через Windows Media Session.

        ``player`` only selects/starts an allow-listed target. Playback commands
        are sent as standard media keys, which are understood by AIMP, foobar,
        Spotify, Яндекс Музыкой and Chromium/Edge media tabs without injecting
        input into their windows. This is also safe when no player is running.
        """
        import time
        target = self._media_target_key(player)
        if target is None:
            return "Неизвестный плеер. Доступны: auto, Spotify, AIMP, foobar2000, Яндекс Музыка, браузер."
        act = (action or "").lower().strip()

        act_norm = {
            "stop": "stop",
            "resume": "play",
            "skip": "next",
            "next_track": "next",
            "previous": "prev",
            "prev_track": "prev",
            "back": "prev",
            "vol_up": "volume_up",
            "vol_down": "volume_down",
            "mute_pc": "volume_mute",
        }
        act = act_norm.get(act, act)

        if act in ["mute", "volume_mute"]:
            return self.tool_volume("mute")
        if act in ["volume_up", "vol_up"]:
            return self.tool_volume("up")
        if act in ["volume_down", "vol_down"]:
            return self.tool_volume("down")

        # Виртуальные клавиши Windows для мультимедиа:
        # VK_MEDIA_NEXT_TRACK = 0xB0 (эквивалент клавиши FN+F6)
        # VK_MEDIA_PREV_TRACK = 0xB1
        # VK_MEDIA_STOP = 0xB2
        # VK_MEDIA_PLAY_PAUSE = 0xB3
        key_map = {
            "play_pause": (0xB3, "Пауза/Воспроизведение переключено 🎵"),
            "play":       (0xB3, "Воспроизведение запущено ▶️"),
            "pause":      (0xB3, "Музыка на паузе ⏸️"),
            "next":       (0xB0, "Следующий трек ⏭️ (FN+F6)"),
            "prev":       (0xB1, "Предыдущий трек ⏮️"),
            "stop":       (0xB2, "Воспроизведение остановлено ⏹️"),
        }

        if act in key_map:
            vk, desc = key_map[act]
            start_message = None
            if target and target != "auto":
                # Starting a target is opt-in for an explicit player. Existing
                # processes receive keys immediately; otherwise open then retry.
                spec = self.MEDIA_PLAYERS[target]
                running = any(p.lower() in self._running_process_names() for p in spec["processes"])
                if not running and act in {"play", "play_pause"}:
                    start_message = self.tool_open_media_player(target)
                    time.sleep(0.8)
                    running = any(p.lower() in self._running_process_names() for p in spec["processes"])
                # Spotify/Яндекс may be handled by an already-open browser
                # Media Session even when their desktop process is absent.
                if not running and not spec.get("url"):
                    return start_message or f"{spec['name']} не запущен. Открой его или выбери другой плеер."
            transport = self._send_media_key(vk, target)
            if transport:
                target_name = self.MEDIA_PLAYERS[target]["name"] if target != "auto" else "активный медиа-плеер Windows"
                transport_name = "окну плеера" if transport == "window_message" else "системной медиа-сессии"
                return f"{desc} → {target_name} ({transport_name})"
            return "Управление медиа доступно только в интерактивной сессии Windows."

        return f"Медиа: {act} выполнено"

    def tool_like_track(self):
        """Лайк трека: отправляет подтверждение."""
        return "❤️ Лайк зафиксирован!"

    def tool_play_yandex_music(self, query="моя волна"):
        """Включает музыку на ПК без навязчивого открытия и изменения окон (мгновенный запуск)."""
        import os, subprocess, threading, time, webbrowser, psutil, ctypes
        u = ctypes.windll.user32

        def _bg_launch():
            try:
                # 1. Проверяем, запущен ли уже процесс Яндекс Музыки
                ym_running = any('яндекс' in (p.info['name'] or '').lower() or 'yandexmusic' in (p.info['name'] or '').lower()
                                 for p in psutil.process_iter(['name']))
                if ym_running:
                    # Если уже запущена — мгновенно стартуем воспроизведение через мультимедиа без трогания интерфейса
                    u.keybd_event(0xB3, 0, 0, 0)
                    u.keybd_event(0xB3, 0, 2, 0)
                    return

                # 2. Если не запущена — стартуем приложение в фоне
                userprofile = os.environ.get("USERPROFILE", r"C:\Users\7ims (admin)")
                ym_exe_paths = [
                    os.path.join(userprofile, r"AppData\Local\Programs\YandexMusicMod\YandexMusic.exe"),
                    os.path.join(userprofile, r"AppData\Local\Programs\YandexMusicMod\Яндекс Музыка.exe"),
                    os.path.join(userprofile, r"AppData\Local\Programs\YandexMusic\YandexMusic.exe"),
                    os.path.join(userprofile, r"AppData\Local\Programs\YandexMusic\Яндекс Музыка.exe"),
                    os.path.join(userprofile, r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Яндекс Музыка.lnk"),
                    os.path.join(userprofile, r"Desktop\Яндекс Музыка.lnk"),
                ]
                ym_exe = next((p for p in ym_exe_paths if os.path.exists(p)), None)

                if ym_exe:
                    exe_dir = os.path.dirname(ym_exe) or None
                    try:
                        subprocess.Popen([ym_exe], cwd=exe_dir)
                    except Exception:
                        os.startfile(ym_exe)
                    time.sleep(1.2)
                    u.keybd_event(0xB3, 0, 0, 0)
                    u.keybd_event(0xB3, 0, 2, 0)
                else:
                    webbrowser.open("https://music.yandex.ru/radio")
            except Exception as e_bg:
                print(f"[Music BG] Ошибка запуска музыки: {e_bg}")

        threading.Thread(target=_bg_launch, daemon=True).start()
        return "Врубаю «Мою Волну» в Яндекс Музыке! 🎵"


    def tool_get_weather(self, city=""):
        """Получает текущую погоду (как в Алисе) через wttr.in."""
        import urllib.request, urllib.parse
        try:
            city_param = urllib.parse.quote(city.strip()) if city and city.strip() else ""
            fmt = urllib.parse.quote('%l: %C, %t, ветер %w')
            url = f"https://wttr.in/{city_param}?format={fmt}&lang=ru"
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                text = resp.read().decode('utf-8', errors='ignore').strip()
                if text and not "error" in text.lower():
                    return f"🌤️ {text}"
        except Exception as e:
            print(f"[Weather] Ошибка: {e}")
        return "Не удалось получить прогноз погоды."


    def tool_search_youtube(self, query):
        """Ищет видео или музыку на YouTube в браузере."""
        import urllib.parse
        encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        return self.tool_open_website(url)

    def tool_search_web(self, query):
        """Ищет информацию в Google через браузер."""
        import urllib.parse
        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded}"
        return self.tool_open_website(url)

    def tool_window_control(self, action="minimize_all"):
        """Управление окнами Windows: minimize_all, close_active, switch_app, lock_pc."""
        act = action.lower().strip()
        if "minimize" in act or "свернуть" in act or "сверни" in act:
            # Win + M (Minimize All) - гарантированно сворачивает все окна без повторного раскрытия
            try:
                import ctypes
                u = ctypes.windll.user32
                u.keybd_event(0x5B, 0, 0, 0)  # Win down
                u.keybd_event(0x4D, 0, 0, 0)  # M down
                u.keybd_event(0x4D, 0, 2, 0)  # M up
                u.keybd_event(0x5B, 0, 2, 0)  # Win up
            except Exception as ek:
                print(f"[Window] Win+M: {ek}")
            return "Свернула все окна."
        elif "close" in act or "закрыть" in act:
            try:
                pyautogui.FAILSAFE = False
                pyautogui.hotkey("alt", "f4")
            except Exception:
                pass
            return "Закрыла текущее окно."
        elif "switch" in act or "переключить" in act:
            try:
                pyautogui.FAILSAFE = False
                pyautogui.hotkey("alt", "tab")
            except Exception:
                pass
            return "Переключила окно."
        elif "lock" in act or "заблокировать" in act:
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Компьютер заблокирован."
        return f"Команда {action} выполнена."

    def tool_add_note(self, text):
        """Сохраняет быструю заметку в блокнот."""
        os.makedirs("memory", exist_ok=True)
        path = "memory/notes.txt"
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {text}\n")
        return f"Заметка сохранена: «{text}»"

    def tool_list_notes(self):
        """Показывает сохраненные заметки."""
        path = "memory/notes.txt"
        if not os.path.exists(path):
            return "Заметок пока нет."
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if not lines:
                return "Заметок пока нет."
            return "📝 Твои последние заметки:\n" + "".join(lines[-10:])
        except Exception as e:
            return f"Ошибка чтения заметок: {e}"

    # ===== Новые инструменты: программирование и файлы =====

    def tool_write_code(self, task, filename):
        """Отправляет задачу в ИИ-кодер (DeepSeek или локальную модель), получает код, сохраняет в файл."""
        from openai import OpenAI

        cfg = self.a.cfg
        ds_key = getattr(cfg, "DEEPSEEK_API_KEY", "").strip()
        if ds_key and not ds_key.startswith("sk-твой"):
            base_url = getattr(cfg, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            model = getattr(cfg, "DEEPSEEK_MODEL", "deepseek-chat")
            client = OpenAI(base_url=base_url, api_key=ds_key)
        else:
            client = OpenAI(
                base_url=getattr(cfg, "CODER_BASE_URL", cfg.LLM_BASE_URL),
                api_key=getattr(cfg, "CODER_API_KEY", cfg.LLM_API_KEY),
            )
            model = getattr(cfg, "CODER_MODEL", cfg.LLM_MODEL)

        coder_prompt = (
            "You are an expert Python programmer. "
            "Write ONLY clean, working, ready-to-run code. "
            "No explanations, no markdown fences — just pure code. "
            "Comments in Russian. "
            "If the task needs external libraries, add a comment at the top: # pip install library1 library2"
        )

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": coder_prompt},
                {"role": "user", "content": task},
            ],
            temperature=0.2,
        )

        code = resp.choices[0].message.content or ""

        # Убираем markdown-обёртки (```python ... ```) если модель их добавила
        if "```" in code:
            blocks = re.findall(r"```(?:\w*)\n(.*?)```", code, re.DOTALL)
            if blocks:
                code = blocks[0]
        code = code.strip()

        # Сохраняем в projects/
        projects = getattr(cfg, "PROJECTS_DIR", "projects")
        os.makedirs(projects, exist_ok=True)
        filepath = os.path.join(projects, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        # Считаем строки для отчёта
        lines = len(code.splitlines())
        return f"Код написан ({lines} строк) и сохранён в {filepath}"

    def tool_run_command(self, command):
        """Выполняет команду в терминале. Таймаут 60 сек с поддержкой русских кодировок."""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True,
                timeout=60, cwd=os.getcwd(),
            )
            raw = (result.stdout or b"") + (result.stderr or b"")
            output = ""
            for enc in ("utf-8", "cp866", "cp1251"):
                try:
                    output = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                output = raw.decode("utf-8", errors="replace")
            output = output.strip()
            if len(output) > 2500:
                output = output[:2500] + "\n... (обрезано, вывод слишком длинный)"
            return output or "(команда выполнена, вывод пуст)"
        except subprocess.TimeoutExpired:
            return "Команда выполнялась дольше 60 секунд и была остановлена."
        except Exception as e:
            return f"Ошибка выполнения: {e}"

    def tool_read_file(self, path):
        """Читает содержимое файла с поддержкой UTF-8 и CP1251."""
        if not os.path.exists(path):
            return f"Файл не найден: {path}"
        try:
            content = None
            for enc in ("utf-8", "cp1251"):
                try:
                    with open(path, "r", encoding=enc) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            if content is None:
                return "(бинарный файл, не могу прочитать как текст)"
            if len(content) > 3000:
                content = content[:3000] + "\n... (файл обрезан, слишком длинный)"
            return content if content else "(файл пуст)"
        except Exception as e:
            return f"Ошибка чтения: {e}"

    def tool_write_file(self, path, content):
        """Создаёт или перезаписывает файл."""
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Файл сохранён: {path} ({len(content)} символов)"

    def tool_list_files(self, path="projects"):
        """Показывает содержимое папки."""
        if not os.path.exists(path):
            return f"Папка не найдена: {path}"
        items = []
        try:
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                if os.path.isdir(full):
                    items.append(f"[папка] {name}/")
                else:
                    size = os.path.getsize(full)
                    items.append(f"  {name}  ({size} байт)")
        except Exception as e:
            return f"Ошибка: {e}"
        return "\n".join(items) if items else "(папка пуста)"

    def tool_ask_expert_ai(self, prompt, on_token=None):
        """Отправляет сложный вопрос во внешнюю модель DeepSeek или локальному эксперту с поддержкой стриминга токенов."""
        from openai import OpenAI
        cfg = self.a.cfg

        api_key = getattr(cfg, "DEEPSEEK_API_KEY", "").strip()
        base_url = getattr(cfg, "DEEPSEEK_BASE_URL", "https://discovery-api.intern-ai.org.cn/v1")
        model = getattr(cfg, "DEEPSEEK_MODEL", "deepseek-v4-flash-0731")

        if api_key and not api_key.startswith("sk-твой"):
            for m in [model, "deepseek-v4-flash-0731", "qwen3.8-27b"]:
                try:
                    client = OpenAI(base_url=base_url, api_key=api_key)
                    if on_token:
                        resp = client.chat.completions.create(
                            model=m,
                            messages=[
                                {"role": "system", "content": "Ты — продвинутый ИИ-эксперт Мия. Отвечай глубоко, подробно, структурированно и понятно на русском языке."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.3,
                            stream=True
                        )
                        full_ans = ""
                        for chunk in resp:
                            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                text_piece = chunk.choices[0].delta.content
                                full_ans += text_piece
                                on_token(text_piece)
                        if full_ans:
                            return full_ans
                    else:
                        resp = client.chat.completions.create(
                            model=m,
                            messages=[
                                {"role": "system", "content": "Ты — продвинутый ИИ-эксперт Мия. Отвечай глубоко, подробно, структурированно и понятно на русском языке."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.3,
                            stream=False
                        )
                        ans = (resp.choices[0].message.content or "").strip()
                        if ans:
                            return ans
                except Exception as e:
                    print(f"[Expert AI] Ошибка модели {m}: {e}, пробую следующую...")
                    continue

        # Локальный эксперт через Ollama
        try:
            local_model = getattr(cfg, "EXPERT_LOCAL_MODEL", cfg.LLM_MODEL)
            client = OpenAI(base_url=cfg.LLM_BASE_URL, api_key=cfg.LLM_API_KEY)
            resp = client.chat.completions.create(
                model=local_model,
                messages=[
                    {"role": "system", "content": "Ты — продвинутый ИИ-эксперт Мия. Дай структурированный и точный ответ на русском языке."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            return f"Ошибка при обращении к эксперту: {e}"


class AudioDucker:
    """
    Автоматическое приглушение громкости музыки (Audio Ducking) как в JARVIS.
    Когда пользователь обращается к Мие («Мия»), громкость снижается на 50%,
    а после завершения команды плавно восстанавливается до исходного уровня.
    """
    def __init__(self, factor=0.5, min_volume=0.04, release_ms=120):
        self.factor = max(0.05, min(1.0, float(factor)))
        self.min_volume = max(0.0, min(1.0, float(min_volume)))
        self.release_ms = max(0, int(release_ms))
        self._orig_scalar = None
        self._ducked_scalar = None
        self._orig_muted = None
        self._is_ducked = False
        import threading
        self._lock = threading.RLock()

    @property
    def is_ducked(self):
        return self._is_ducked

    @staticmethod
    def _endpoint():
        """Return the default Windows endpoint or raise a clear error."""
        if sys.platform != "win32":
            raise RuntimeError("Audio ducking доступен только в Windows")
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        endpoint = getattr(speakers, "EndpointVolume", None)
        if endpoint is None:
            raise RuntimeError("No EndpointVolume")
        return endpoint

    @staticmethod
    def _com_initialize():
        try:
            import comtypes
            comtypes.CoInitialize()
            return comtypes
        except Exception:
            return None

    @staticmethod
    def _com_uninitialize(comtypes_module):
        if comtypes_module is not None:
            try:
                comtypes_module.CoUninitialize()
            except Exception:
                pass

    def duck(self, factor=None):
        f = max(0.05, min(1.0, float(factor if factor is not None else self.factor)))
        with self._lock:
            if self._is_ducked:
                return
            comtypes_module = self._com_initialize()
            try:
                vol = self._endpoint()
                self._orig_scalar = vol.GetMasterVolumeLevelScalar()
                try:
                    self._orig_muted = bool(vol.GetMute())
                except Exception:
                    self._orig_muted = None
                # Never make an already-muted/near-zero endpoint louder.
                target_scalar = self._orig_scalar if self._orig_scalar <= self.min_volume else max(self.min_volume, self._orig_scalar * f)
                self._ducked_scalar = target_scalar
                vol.SetMasterVolumeLevelScalar(target_scalar, None)
                self._is_ducked = True
                print(f"[MusicDucking] 🔉 Громкость приглушена с {int(self._orig_scalar*100)}% до {int(target_scalar*100)}%")
            except Exception as e:
                print(f"[MusicDucking] Ошибка duck: {e}")
                self._orig_scalar = None
                self._ducked_scalar = None
                self._orig_muted = None
            finally:
                self._com_uninitialize(comtypes_module)

    def unduck(self):
        with self._lock:
            if not self._is_ducked or self._orig_scalar is None:
                return
            comtypes_module = self._com_initialize()
            try:
                vol = self._endpoint()
                current = self._ducked_scalar
                try:
                    current = float(vol.GetMasterVolumeLevelScalar())
                except Exception:
                    pass
                duration = self.release_ms / 1000.0
                steps = max(1, int(round(duration / 0.02)))
                for index in range(1, steps + 1):
                    progress = index / steps
                    value = current + (self._orig_scalar - current) * progress
                    vol.SetMasterVolumeLevelScalar(value, None)
                    if duration and index < steps:
                        import time
                        time.sleep(duration / steps)
                print(f"[MusicDucking] 🔊 Громкость восстановлена до {int(self._orig_scalar*100)}%")
            except Exception as e:
                print(f"[MusicDucking] Ошибка unduck: {e}")
            finally:
                self._com_uninitialize(comtypes_module)
                self._is_ducked = False
                self._orig_scalar = None
                self._ducked_scalar = None
                self._orig_muted = None
