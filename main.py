# main.py — запускает всё сразу
import os, sys
os.environ["FOR_DISABLE_CONSOLE_CTRL_HANDLER"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

if sys.platform == "win32":
    if sys.stdout is None:
        try:
            sys.stdout = open(os.path.join(os.path.dirname(__file__), "mia_stdout.log"), "a", encoding="utf-8", buffering=1)
        except Exception:
            class DummyWriter:
                def write(self, s): pass
                def flush(self): pass
            sys.stdout = DummyWriter()
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if sys.stderr is None:
        try:
            sys.stderr = open(os.path.join(os.path.dirname(__file__), "mia_stderr.log"), "a", encoding="utf-8", buffering=1)
        except Exception:
            class DummyWriter:
                def write(self, s): pass
                def flush(self): pass
            sys.stderr = DummyWriter()
    else:
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    import ctypes
    try:
        _u32 = ctypes.windll.user32
        _hwinsta = _u32.OpenWindowStationW("WinSta0", False, 0x037F)
        if _hwinsta:
            _u32.SetProcessWindowStation(_hwinsta)
        _hdesk = _u32.OpenDesktopW("Default", 0, False, 0x01FF)
        if _hdesk:
            _u32.SetThreadDesktop(_hdesk)
    except Exception:
        pass

import asyncio
import config as cfg
from memory import Memory
from tools import Tools
from brain import Brain
from voice import Voice
from voice_input import Ears
from avatar import Avatar
from scenarios import ScenarioEngine
from tg_bot import TGBot
from web_panel import start_web
from hotword import HotwordListener
from tray import SystemTray

class Assistant:
    def __init__(self):
        self.cfg = cfg
        self.last_chat_id = None
        self.loop = None
        self.memory = Memory()
        self.tools = Tools(self)
        self.brain = Brain(cfg, self.memory, self.tools)
        self.voice = Voice(cfg)
        self.ears = Ears(cfg)
        self.avatar = Avatar(cfg)
        self.scenarios = ScenarioEngine(self)
        self.tg = TGBot(self)
        self.hotword = HotwordListener(self)
        self.tray = SystemTray(self)
        self.ducker = self.tools.ducker
        self.is_muted = False
        self._ensure_ollama()

    def _ensure_ollama(self):
        def _check():
            import urllib.request, subprocess
            try:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5) as resp:
                    if resp.status == 200:
                        return
            except Exception:
                pass
            try:
                subprocess.Popen(["ollama", "serve"], creationflags=0x08000000)
            except Exception:
                pass
        import threading
        threading.Thread(target=_check, daemon=True).start()

    def set_muted(self, muted: bool):
        self.is_muted = muted
        return self.is_muted

    def toggle_muted(self):
        self.is_muted = not self.is_muted
        return self.is_muted

    def set_voice_profile(self, profile: str):
        if hasattr(self, "voice") and hasattr(self.voice, "set_profile"):
            return self.voice.set_profile(profile)
        return profile

    async def handle_user_message(self, text, speak=True, source="other"):
        if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and source == "voice":
            self.ducker.duck()
        try:
            self.memory.add_message("user", text, source=source)
            emotion, clean, raw = await asyncio.to_thread(self.brain.think)
            self.memory.add_message("assistant", clean, source=source, emotion=emotion)
            await self.avatar.set_emotion(emotion)
            if speak and not self.is_muted:
                await self.voice.speak(clean, emotion=emotion)
            if source == "voice":
                try:
                    tg_msg = f"🎤 <b>[Голосовой разговор на ПК]</b>\n👤 <b>Ты:</b> {text}\n🎀 <b>Мия:</b> {clean}"
                    self.notify_admin_sync(tg_msg)
                except Exception as e:
                    print(f"[Main] Ошибка дублирования в TG: {e}")
            return emotion, clean, raw
        finally:
            if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and source == "voice":
                self.ducker.unduck()

    async def handle_user_message_stream(self, text, on_token=None, speak=True, source="other"):
        if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and source == "voice":
            self.ducker.duck()
        try:
            user_id = self.memory.add_message("user", text, source=source)
            loop = asyncio.get_running_loop()

            def _sync_on_token(token):
                if on_token:
                    loop.call_soon_threadsafe(on_token, token)

            emotion, clean, raw = await asyncio.to_thread(self.brain.think_stream, on_token=_sync_on_token)
            asst_id = self.memory.add_message("assistant", clean, source=source, emotion=emotion)
            await self.avatar.set_emotion(emotion)
            if speak and not self.is_muted:
                await self.voice.speak(clean, emotion=emotion)
            if source == "voice":
                try:
                    tg_msg = f"🎤 <b>[Голосовой разговор на ПК]</b>\n👤 <b>Ты:</b> {text}\n🎀 <b>Мия:</b> {clean}"
                    self.notify_admin_sync(tg_msg)
                except Exception as e:
                    print(f"[Main] Ошибка дублирования в TG: {e}")
            return emotion, clean, raw, user_id, asst_id
        finally:
            if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and source == "voice":
                self.ducker.unduck()

    # Мостики из потоков в главный цикл (для уведомлений из инструментов)
    def _spawn(self, coro):
        if self.loop:
            asyncio.run_coroutine_threadsafe(coro, self.loop)

    def notify_admin_sync(self, text): self._spawn(self.tg.notify(text))
    def send_photo_sync(self, path):   self._spawn(self.tg.send_photo(path))
    def run_scenario_async(self, name): self._spawn(self.scenarios.run(name))

    async def start(self):
        self.loop = asyncio.get_running_loop()
        await self.avatar.connect()
        for s in self.scenarios.list_all():
            if isinstance(s, dict) and s.get("enabled") and s.get("trigger", {}).get("type") == "startup":
                asyncio.create_task(self.scenarios.run(s["name"]))
        self.tray.start()
        self.hotword.start()
        print("✅ Мия запущена! Панель: http://localhost:8000")
        await asyncio.gather(
            self.tg.run(),
            start_web(self),
            self.scenarios.scheduler_loop(),
        )

if __name__ == "__main__":
    asyncio.run(Assistant().start())