# tray.py — системный трей Windows (иконка, меню, автозагрузка)
import os, sys, threading, webbrowser, subprocess
import pystray
from PIL import Image, ImageDraw

STARTUP_DIR = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
VBS_NAME = "MiaAssistant.vbs"

def get_startup_vbs_path():
    return os.path.join(STARTUP_DIR, VBS_NAME)

def is_autostart_enabled():
    return os.path.exists(get_startup_vbs_path())

def set_autostart(enable: bool, project_dir=None):
    vbs_path = get_startup_vbs_path()
    if enable:
        if not project_dir:
            project_dir = os.path.abspath(os.path.dirname(__file__))
        pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw_path):
            pythonw_path = sys.executable

        vbs_content = (
            'Set WshShell = CreateObject("WScript.Shell")\r\n'
            f'WshShell.CurrentDirectory = "{project_dir}"\r\n'
            f'WshShell.Run """{pythonw_path}"" main.py", 0, False\r\n'
        )
        os.makedirs(STARTUP_DIR, exist_ok=True)
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        return True
    else:
        if os.path.exists(vbs_path):
            try:
                os.remove(vbs_path)
            except Exception:
                pass
        return False

def get_or_create_icon_image():
    icon_path = "memory/icon.png"
    if os.path.exists(icon_path):
        try:
            return Image.open(icon_path)
        except Exception:
            pass
    # Если иконки нет, рисуем красивый значок "M"
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill="#f38ba8", outline="#cba6f7", width=3)
    d.text((20, 14), "M", fill="#181825", font_size=36)
    os.makedirs("memory", exist_ok=True)
    img.save(icon_path)
    return img

class SystemTray:
    def __init__(self, assistant):
        self.a = assistant
        self.icon = None

    def start(self):
        img = get_or_create_icon_image()

        def on_open_web(icon, item):
            webbrowser.open("http://127.0.0.1:8000")

        def on_toggle_wake(icon, item):
            if hasattr(self.a, "hotword"):
                self.a.hotword.toggle()

        def is_wake_checked(item):
            return getattr(getattr(self.a, "hotword", None), "enabled", False)

        def on_toggle_mute(icon, item):
            self.a.toggle_muted()

        def is_mute_checked(item):
            return getattr(self.a, "is_muted", False)

        def on_open_projects(icon, item):
            path = os.path.abspath(getattr(self.a.cfg, "PROJECTS_DIR", "projects"))
            os.makedirs(path, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(path)

        def on_toggle_autostart(icon, item):
            current = is_autostart_enabled()
            set_autostart(not current, os.path.abspath(os.path.dirname(__file__)))

        def is_autostart_checked(item):
            return is_autostart_enabled()

        def on_exit(icon, item):
            icon.stop()
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("💬 Открыть панель", on_open_web, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🎤 Слушать имя ('Мия')", on_toggle_wake, checked=is_wake_checked),
            pystray.MenuItem("🔇 Без звука (Мьют)", on_toggle_mute, checked=is_mute_checked),
            pystray.MenuItem("🚀 Запуск вместе с Windows", on_toggle_autostart, checked=is_autostart_checked),
            pystray.MenuItem("📁 Папка проектов", on_open_projects),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Выход", on_exit)
        )

        self.icon = pystray.Icon("MiaAssistant", img, "Мия — ИИ помощник", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()
        print("[Tray] Значок Мии добавлен в системный трей Windows (рядом с часами)")
