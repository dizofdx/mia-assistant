# avatar.py — эмоции 2D-аватара в VTube Studio (включим на Этапе 7)
try:
    import pyvts
except ImportError:
    pyvts = None

EMOTE_MAP = {
    "РАДОСТЬ": "joy", "СМЕХ": "joy", "ГРУСТЬ": "sad", "ЗЛОСТЬ": "angry",
    "УДИВЛЕНИЕ": "surprised", "СМУЩЕНИЕ": "blush",
    "СПОКОЙСТВИЕ": "neutral", "ЗАДУМЧИВОСТЬ": "think",
}

class Avatar:
    def __init__(self, cfg):
        self.cfg = cfg
        self.ready = False

    async def connect(self):
        if not self.cfg.VTUBE_STUDIO_ENABLED or pyvts is None:
            return
        try:
            self.vts = pyvts.vts(plugin_info={
                "plugin_name": "Mia Assistant", "developer": "You",
                "authentication_token_path": "memory/vts_token.txt"})
            await self.vts.connect()
            await self.vts.request_authenticate_token()  # 1-й раз подтверди в окне VTS!
            await self.vts.request_authenticate()
            self.ready = True
            print("✅ Аватар подключён")
        except Exception as e:
            print(f"⚠️ VTube Studio недоступен, работаю без аватара: {e}")

    async def set_emotion(self, emotion):
        if not self.ready:
            return
        hotkey = EMOTE_MAP.get(emotion)
        if hotkey:
            try:
                await self.vts.request(self.vts.vts_request.requestHotKeyTrigger(hotkeyID=hotkey))
            except Exception:
                pass
