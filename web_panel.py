# web_panel.py — FastAPI панель управления Мии (http://localhost:8000)
import os, sys, asyncio, json, socket
from fastapi import FastAPI, Request, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn
from visual_commands import VisualCommandManager

_UI_CACHE = None
_UI_MTIME = 0

def get_web_ui() -> str:
    """Загружает web_ui.html с диска с кэшированием в памяти."""
    global _UI_CACHE, _UI_MTIME
    p = os.path.join(os.path.dirname(__file__), "web_ui.html")
    if os.path.exists(p):
        try:
            mtime = os.path.getmtime(p)
            if _UI_CACHE is None or mtime > _UI_MTIME:
                with open(p, "r", encoding="utf-8") as f:
                    _UI_CACHE = f.read()
                _UI_MTIME = mtime
            return _UI_CACHE
        except Exception:
            pass
    return "<h1>Мия: файл web_ui.html не найден</h1>"

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()

def create_app(assistant):
    app = FastAPI(title="Mia Web Panel")
    eng = assistant.scenarios
    vc_manager = VisualCommandManager(assistant)
    assistant.vc_manager = vc_manager

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return get_web_ui()

    @app.get("/manifest.json")
    def manifest():
        return {
            "id": "/?source=pwa",
            "name": "Мия Connect — ИИ-Ассистент",
            "short_name": "Мия",
            "description": "Голосовой ИИ-компаньон и пульт ПК для Android",
            "start_url": "/?source=pwa",
            "scope": "/",
            "display": "standalone",
            "background_color": "#0a0a0a",
            "theme_color": "#0a0a0a",
            "orientation": "portrait-primary",
            "icons": [
                {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
                {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
            ]
        }

    @app.get("/sw.js")
    def service_worker():
        js = """
        const CACHE_NAME = 'mia-pwa-v1';
        self.addEventListener('install', (e) => {
            self.skipWaiting();
        });
        self.addEventListener('activate', (e) => {
            e.waitUntil(clients.claim());
        });
        self.addEventListener('fetch', (e) => {
            e.respondWith(
                fetch(e.request).catch(() => caches.match(e.request))
            );
        });
        """
        return Response(content=js, media_type="application/javascript")

    @app.get("/api/status")
    def get_status():
        return {
            "muted": assistant.is_muted,
            "model": getattr(assistant.cfg, "LLM_MODEL", "qwen2.5:3b-instruct"),
            "voice_engine": getattr(assistant.cfg, "TTS_ENGINE", "silero"),
            "voice": assistant.voice.get_speaker() if hasattr(assistant, "voice") else getattr(assistant.cfg, "SILERO_SPEAKER", "baya"),
            "voice_profile": getattr(getattr(assistant, "voice", None), "profile", "anime"),
            "hotword": getattr(getattr(assistant, "hotword", None), "enabled", False),
            "local_ip": get_local_ip(),
            "port": 8000
        }

    @app.get("/api/history")
    def get_history(limit: int = 50, since_id: int = 0):
        return assistant.memory.recent_dialog(limit=limit, since_id=since_id)

    @app.get("/api/system_stats")
    def get_system_stats():
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            d_disk = psutil.disk_usage('D:\\') if os.path.exists('D:\\') else psutil.disk_usage('C:\\')
            c_disk = psutil.disk_usage('C:\\')
            return {
                "cpu": cpu,
                "ram_percent": ram.percent,
                "ram_used_gb": round(ram.used / (1024**3), 1),
                "ram_total_gb": round(ram.total / (1024**3), 1),
                "disk_c_free_gb": round(c_disk.free / (1024**3), 1),
                "disk_d_free_gb": round(d_disk.free / (1024**3), 1),
            }
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/weather")
    def get_weather():
        return {
            "temp": "+18°",
            "desc": "Ясно",
            "city": "Москва",
            "humidity": "45%",
            "wind": "3 м/с"
        }

    @app.get("/api/currency")
    def get_currency():
        return {
            "pair": "USD / EUR",
            "rate": "0.92 €",
            "change": "▲ 0.42%",
            "is_up": True
        }

    @app.get("/api/avatar_status")
    def avatar_status():
        return {
            "speaking": getattr(assistant.voice, "is_speaking", False),
            "emotion": getattr(assistant, "current_emotion", "СПОКОЙСТВИЕ"),
            "muted": assistant.is_muted
        }

    @app.post("/api/upload_mascot_2d")
    async def upload_mascot_2d(file: UploadFile = File(...)):
        os.makedirs("static", exist_ok=True)
        ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
        path = os.path.join("static", f"custom_mascot_2d{ext}")
        content = await file.read()
        with open(path, "wb") as f:
            f.write(content)
        import time
        return {"ok": True, "url": f"/static/custom_mascot_2d{ext}?t={int(time.time())}"}

    @app.post("/api/upload_mascot_3d")
    async def upload_mascot_3d(file: UploadFile = File(...)):
        """Store a self-contained 3D asset for the browser avatar.

        A standalone .gltf commonly references external .bin/textures which
        cannot be uploaded through this single-file endpoint. Accept .glb by
        default and reject unsupported/malformed uploads early.
        """
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in {".glb", ".gltf"}:
            raise HTTPException(status_code=415, detail="Поддерживаются только .glb и .gltf")
        content = await file.read()
        if not content or len(content) > 100 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Файл пустой или больше 100 МБ")
        if ext == ".glb" and (len(content) < 12 or content[:4] != b"glTF"):
            raise HTTPException(status_code=400, detail="Некорректный GLB-файл")
        if ext == ".gltf":
            try:
                document = json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise HTTPException(status_code=400, detail="Некорректный JSON glTF")
            # A single-file upload cannot carry a sibling .bin or texture.
            # Embedded data URIs remain valid and can be loaded directly.
            external = []
            for section in ("buffers", "images"):
                for item in document.get(section, []) or []:
                    uri = item.get("uri") if isinstance(item, dict) else None
                    if uri and not str(uri).startswith("data:"):
                        external.append(str(uri))
            if external:
                raise HTTPException(
                    status_code=400,
                    detail="Этот glTF использует внешние .bin/текстуры. Загрузите самодостаточный .glb или glTF с data: URI.",
                )
        static_dir_abs = os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(static_dir_abs, exist_ok=True)
        path = os.path.join(static_dir_abs, f"custom_model_3d{ext}")
        with open(path, "wb") as f:
            f.write(content)
        import time
        return {"ok": True, "url": f"/static/custom_model_3d{ext}?t={int(time.time())}"}

    @app.websocket("/ws")
    async def telemetry_socket(websocket: WebSocket):
        """Push avatar/system state without repeated HTTP polling."""
        await websocket.accept()
        try:
            while True:
                await websocket.send_json({
                    "type": "avatar_status",
                    "speaking": getattr(assistant.voice, "is_speaking", False),
                    "emotion": getattr(assistant, "current_emotion", "СПОКОЙСТВИЕ"),
                    "muted": assistant.is_muted,
                })
                await asyncio.sleep(0.25)
        except (WebSocketDisconnect, RuntimeError):
            return

    @app.get("/api/mascot_info")
    def get_mascot_info():
        has_custom_2d = None
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
            p = os.path.join("static", f"custom_mascot_2d{ext}")
            if os.path.exists(p):
                has_custom_2d = f"/static/custom_mascot_2d{ext}"
                break
        has_custom_3d = None
        for ext in [".glb", ".gltf"]:
            p = os.path.join("static", f"custom_model_3d{ext}")
            if os.path.exists(p):
                has_custom_3d = f"/static/custom_model_3d{ext}"
                break
        return {
            "default_2d": "/static/mascot.png",
            "custom_2d": has_custom_2d,
            "custom_3d": has_custom_3d
        }

    @app.get("/api/media/status")
    async def media_status_api():
        """Return the allow-listed media targets and running-state snapshot."""
        return await asyncio.to_thread(assistant.tools.tool_media_status)

    @app.post("/api/media")
    async def post_media(req: Request):
        try:
            data = await req.json()
        except Exception:
            data = {}
        act = data.get("action", "play_pause") if isinstance(data, dict) else "play_pause"
        player = data.get("player") if isinstance(data, dict) else None
        res = await asyncio.to_thread(assistant.tools.tool_media_control, act, player)
        return {"result": res, "player": player or "auto"}

    @app.post("/api/window")
    async def post_window(req: Request):
        try:
            data = await req.json()
        except Exception:
            data = {}
        act = data.get("action", "minimize_all") if isinstance(data, dict) else "minimize_all"
        res = assistant.tools.tool_window_control(act)
        return {"result": res}

    @app.post("/api/mute")
    async def set_mute(req: Request):
        try:
            data = await req.json()
        except Exception:
            data = {}
        new_val = data.get("muted", not assistant.is_muted) if isinstance(data, dict) else (not assistant.is_muted)
        assistant.set_muted(new_val)
        return {"muted": assistant.is_muted}

    @app.post("/api/remote_action")
    async def remote_action(req: Request):
        try:
            data = await req.json()
        except Exception:
            data = {}
        act = data.get("action", "") if isinstance(data, dict) else ""
        player = data.get("player") if isinstance(data, dict) else None
        if act == "lock":
            res = assistant.tools.tool_window_control("lock_pc")
            return {"ok": True, "msg": "ПК заблокирован"}
        elif act == "minimize":
            res = assistant.tools.tool_window_control("minimize_all")
            return {"ok": True, "msg": "Все окна свернуты"}
        elif act == "wave":
            res = await asyncio.to_thread(assistant.tools.tool_play_yandex_music, "моя волна")
            return {"ok": True, "msg": res or "Врубаю «Мою Волну» в Яндекс Музыке! 🎵"}
        elif act == "open_player":
            res = await asyncio.to_thread(assistant.tools.tool_open_media_player, player or "browser")
            return {"ok": True, "msg": res}
        elif act == "play_pause":
            res = assistant.tools.tool_media_control("play_pause", player)
            return {"ok": True, "msg": res or "Воспроизведение/Пауза"}
        elif act == "next_track":
            res = assistant.tools.tool_media_control("next_track", player)
            return {"ok": True, "msg": res or "Следующий трек"}
        elif act == "prev_track":
            res = assistant.tools.tool_media_control("prev_track", player)
            return {"ok": True, "msg": res or "Предыдущий трек"}
        elif act == "vol_up":
            res = assistant.tools.tool_media_control("volume_up")
            return {"ok": True, "msg": "Громкость +"}
        elif act == "vol_down":
            res = assistant.tools.tool_media_control("volume_down")
            return {"ok": True, "msg": "Громкость -"}
        elif act == "mute_pc":
            res = assistant.tools.tool_media_control("volume_mute")
            return {"ok": True, "msg": "Звук переключен"}
        elif act == "screenshot":
            path = await asyncio.to_thread(assistant.tools.tool_take_screenshot)
            return {"ok": True, "msg": "Скриншот сделан", "path": "/api/screenshot_file"}
        return {"ok": False, "error": f"Неизвестное действие: {act}"}

    @app.get("/api/screenshot")
    async def take_screenshot_api():
        try:
            path = await asyncio.to_thread(assistant.tools.tool_take_screenshot)
            if path and os.path.exists(path):
                return {"ok": True, "path": path}
            return {"ok": False, "error": "Не удалось создать скриншот"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.get("/api/screenshot_file")
    def get_screenshot_file():
        path = os.path.abspath("memory/screenshot.png")
        if os.path.exists(path):
            return FileResponse(path, media_type="image/png")
        return HTMLResponse("Скриншот ещё не сделан", status_code=404)

    # === ВИЗУАЛЬНЫЕ КОМАНДЫ (ASTRA COMMAND EDITOR) ===
    @app.get("/api/visual_commands")
    def list_visual_commands():
        return vc_manager.list_flows()

    @app.post("/api/visual_commands")
    async def save_visual_command(req: Request):
        data = await req.json()
        return vc_manager.save_flow(data)

    @app.delete("/api/visual_commands/{flow_id}")
    def delete_visual_command(flow_id: str):
        return {"ok": vc_manager.delete_flow(flow_id)}

    @app.post("/api/visual_commands/run/{flow_id}")
    async def run_visual_command(flow_id: str):
        return await vc_manager.execute_flow(flow_id)

    @app.post("/api/visual_commands/run")
    async def run_visual_command_body(req: Request):
        data = await req.json()
        flow_id = data.get("id") or data.get("flow_id")
        return await vc_manager.execute_flow(flow_id)

    # === СТАРЫЕ СЦЕНАРИИ ДЛЯ СОВМЕСТИМОСТИ ===
    @app.get("/api/scenarios")
    def list_scenarios():
        return eng.list_all()

    @app.post("/api/scenarios")
    async def create_scenario(req: Request):
        eng.save(await req.json())
        return {"ok": True}

    @app.delete("/api/scenarios/{name}")
    def delete_scenario(name: str):
        eng.delete(name)
        return {"ok": True}

    # === УСТАНОВЛЕННЫЕ ПРИЛОЖЕНИЯ ПК (ДЛЯ РЕДАКТОРА КОМАНД) ===
    @app.get("/api/installed_apps")
    def api_installed_apps():
        try:
            apps = assistant.tools.get_installed_apps()
            return [{"name": k, "path": v} for k, v in sorted(apps.items())]
        except Exception:
            return []

    # === ФАЙЛОВЫЙ МЕНЕДЖЕР (ПРОСМОТР ПАПОК, СКАЧИВАНИЕ, ОТКРЫТИЕ НА ПК) ===
    @app.get("/api/files/list")
    def list_files(path: str = ""):
        import string, os, datetime
        userprofile = os.environ.get("USERPROFILE", r"C:\Users\7ims (admin)")
        quick_access = [
            {"name": "Рабочий стол", "path": os.path.join(userprofile, "Desktop"), "icon": "desktop"},
            {"name": "Загрузки", "path": os.path.join(userprofile, "Downloads"), "icon": "download"},
            {"name": "Документы", "path": os.path.join(userprofile, "Documents"), "icon": "folder"},
            {"name": "Изображения", "path": os.path.join(userprofile, "Pictures"), "icon": "image"},
            {"name": "Музыка", "path": os.path.join(userprofile, "Music"), "icon": "music"},
            {"name": "Видео", "path": os.path.join(userprofile, "Videos"), "icon": "video"},
            {"name": "Папка ассистента", "path": os.path.abspath("."), "icon": "code"},
        ]

        drives = []
        for letter in string.ascii_uppercase:
            d = f"{letter}:\\"
            if os.path.exists(d):
                try:
                    import psutil
                    u = psutil.disk_usage(d)
                    free_gb = round(u.free / (1024**3), 1)
                    total_gb = round(u.total / (1024**3), 1)
                    pct = u.percent
                except Exception:
                    free_gb = 0; total_gb = 0; pct = 0
                drives.append({
                    "name": f"Диск {letter}:",
                    "path": d,
                    "free_gb": free_gb,
                    "total_gb": total_gb,
                    "percent": pct
                })

        if not path or path == "root":
            return {
                "current_path": "",
                "is_root": True,
                "drives": drives,
                "quick_access": [q for q in quick_access if os.path.exists(q["path"])],
                "folders": [],
                "files": [],
                "breadcrumbs": []
            }

        norm_p = os.path.abspath(path)
        if not os.path.exists(norm_p):
            return {"error": f"Путь не найден: {norm_p}"}

        folders = []
        files = []
        try:
            for entry in os.scandir(norm_p):
                try:
                    stat = entry.stat()
                    mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
                    if entry.is_dir():
                        folders.append({
                            "name": entry.name,
                            "path": entry.path,
                            "modified": mod_time
                        })
                    elif entry.is_file():
                        ext = os.path.splitext(entry.name)[1].lower()
                        sz = stat.st_size
                        if sz < 1024:
                            sz_str = f"{sz} B"
                        elif sz < 1024 * 1024:
                            sz_str = f"{sz / 1024:.1f} KB"
                        elif sz < 1024 * 1024 * 1024:
                            sz_str = f"{sz / (1024 * 1024):.1f} MB"
                        else:
                            sz_str = f"{sz / (1024 * 1024 * 1024):.2f} GB"

                        ftype = "file"
                        if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico"]:
                            ftype = "image"
                        elif ext in [".mp3", ".wav", ".ogg", ".flac", ".m4a"]:
                            ftype = "audio"
                        elif ext in [".mp4", ".mkv", ".webm", ".avi", ".mov"]:
                            ftype = "video"
                        elif ext in [".zip", ".rar", ".7z", ".tar", ".gz"]:
                            ftype = "archive"
                        elif ext in [".py", ".js", ".html", ".css", ".json", ".ts", ".bat", ".ps1"]:
                            ftype = "code"
                        elif ext in [".txt", ".md", ".pdf", ".docx", ".xlsx", ".log"]:
                            ftype = "document"
                        elif ext in [".exe", ".lnk", ".msi"]:
                            ftype = "app"

                        files.append({
                            "name": entry.name,
                            "path": entry.path,
                            "size_bytes": sz,
                            "size": sz_str,
                            "ext": ext,
                            "type": ftype,
                            "modified": mod_time
                        })
                except (PermissionError, OSError):
                    continue
        except Exception as e_ls:
            return {"error": f"Ошибка чтения папки: {e_ls}"}

        folders.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())

        parts = os.path.normpath(norm_p).split(os.sep)
        breadcrumbs = []
        acc = ""
        for i, pt in enumerate(parts):
            if i == 0 and pt.endswith(":"):
                acc = pt + "\\"
                breadcrumbs.append({"name": pt, "path": acc})
            else:
                acc = os.path.join(acc, pt)
                breadcrumbs.append({"name": pt, "path": acc})

        parent_p = os.path.dirname(norm_p)
        if parent_p == norm_p:
            parent_p = ""

        return {
            "current_path": norm_p,
            "parent": parent_p,
            "is_root": False,
            "drives": drives,
            "quick_access": [q for q in quick_access if os.path.exists(q["path"])],
            "folders": folders,
            "files": files,
            "breadcrumbs": breadcrumbs
        }

    @app.get("/api/files/download")
    def download_file(path: str):
        import zipfile
        if not path or not os.path.exists(path):
            return Response("Файл или папка не найдены", status_code=404)
        if os.path.isfile(path):
            filename = os.path.basename(path)
            return FileResponse(path, filename=filename)
        elif os.path.isdir(path):
            os.makedirs("memory/temp_zips", exist_ok=True)
            folder_name = os.path.basename(path.rstrip("\\/")) or "folder"
            zip_path = os.path.abspath(f"memory/temp_zips/{folder_name}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, fls in os.walk(path):
                    for f in fls:
                        fp = os.path.join(root, f)
                        arcname = os.path.relpath(fp, path)
                        try:
                            zf.write(fp, arcname)
                        except Exception:
                            pass
            return FileResponse(zip_path, filename=f"{folder_name}.zip")

    @app.post("/api/files/open")
    async def open_file_on_pc(req: Request):
        data = await req.json()
        target_path = data.get("path", "")
        if not target_path or not os.path.exists(target_path):
            return {"ok": False, "error": f"Путь не найден: {target_path}"}
        try:
            if os.path.isdir(target_path):
                os.startfile(target_path)
            else:
                subprocess.Popen(f'explorer.exe /select,"{target_path}"', shell=True)
            return {"ok": True, "message": f"Открыто на мониторе ПК: {os.path.basename(target_path)}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.post("/api/run/{name}")
    async def run_scenario(name: str):
        res = await eng.run(name)
        return {"ok": True, "result": res}

    @app.post("/api/set_voice")
    async def set_voice(req: Request):
        data = await req.json()
        voice = data.get("voice", "baya")
        assistant.cfg.SILERO_SPEAKER = voice
        return {"ok": True, "voice": voice}

    @app.post("/api/test_say")
    async def test_say(req: Request):
        data = await req.json()
        text = data.get("text", "")
        voice = data.get("voice", getattr(assistant.cfg, "SILERO_SPEAKER", "baya"))

        async def _speak_task():
            if voice == "edge":
                await assistant.voice.speak_edge(text)
            else:
                try:
                    await assistant.voice.speak_silero(text, speaker=voice)
                except Exception:
                    await assistant.voice.speak(text)

        asyncio.create_task(_speak_task())
        return {"ok": True}

    @app.post("/api/chat_stream")
    async def chat_stream(req: Request):
        data = await req.json()
        text = data.get("text", "")
        speak = data.get("speak", True)

        async def stream_generator():
            queue = asyncio.Queue()

            def on_token(token):
                queue.put_nowait({"type": "token", "content": token})

            async def worker():
                try:
                    emotion, clean, raw, user_id, asst_id = await assistant.handle_user_message_stream(
                        text, on_token=on_token, speak=speak, source="web"
                    )
                    try:
                        tg_msg = f"🌐 <b>[Веб-панель]</b>\n👤 <b>Ты:</b> {text}\n🎀 <b>Мия:</b> {clean}"
                        assistant.notify_admin_sync(tg_msg)
                    except Exception:
                        pass
                    await queue.put({
                        "type": "done",
                        "reply": clean,
                        "emotion": emotion,
                        "user_msg_id": user_id,
                        "asst_msg_id": asst_id
                    })
                except Exception as e:
                    await queue.put({"type": "error", "error": str(e)})

            worker_task = asyncio.create_task(worker())

            while True:
                item = await queue.get()
                yield (json.dumps(item, ensure_ascii=False) + "\n").encode("utf-8")
                if item.get("type") in ("done", "error"):
                    break
            await worker_task

        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

    @app.post("/api/chat")
    async def chat(req: Request):
        data = await req.json()
        speak = data.get("speak", True)
        emotion, clean, raw = await assistant.handle_user_message(data["text"], speak=speak, source="web")
        
        try:
            tg_msg = f"🌐 <b>[Веб-панель]</b>\n👤 <b>Ты:</b> {data['text']}\n🎀 <b>Мия:</b> {clean}"
            assistant.notify_admin_sync(tg_msg)
        except Exception:
            pass

        return {"reply": clean, "emotion": emotion, "muted": assistant.is_muted}

    @app.post("/api/transcribe_audio")
    async def transcribe_audio(file: UploadFile = File(...)):
        os.makedirs("memory", exist_ok=True)
        temp_path = "memory/web_voice.ogg"
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        text = await asyncio.to_thread(assistant.ears.transcribe, temp_path)
        return {"text": text}

    @app.get("/api/map/geocode")
    async def map_geocode(query: str):
        import urllib.request, urllib.parse
        if not query or not query.strip():
            return {"results": []}
        try:
            q = urllib.parse.quote(query.strip())
            url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=5&addressdetails=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'MiaAssistant/2.0 (Windows NT 10.0; Astra)'})
            def fetch():
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            data = await asyncio.to_thread(fetch)
            results = []
            for item in data:
                results.append({
                    "lat": float(item.get("lat", 0)),
                    "lon": float(item.get("lon", 0)),
                    "display_name": item.get("display_name", ""),
                    "type": item.get("type", "")
                })
            return {"results": results}
        except Exception as e:
            return {"error": str(e), "results": []}

    @app.get("/api/map/weather")
    async def map_weather(lat: float = None, lon: float = None, city: str = ""):
        import urllib.request, urllib.parse
        try:
            if city and city.strip():
                query = urllib.parse.quote(city.strip())
            elif lat is not None and lon is not None:
                query = f"{lat:.4f},{lon:.4f}"
            else:
                query = ""
            url = f"https://wttr.in/{query}?format=j1&lang=ru"
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
            def fetch():
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            data = await asyncio.to_thread(fetch)
            curr = data.get("current_condition", [{}])[0]
            temp = curr.get("temp_C", "--")
            desc = curr.get("lang_ru", [{}])[0].get("value", curr.get("weatherDesc", [{}])[0].get("value", ""))
            feels = curr.get("FeelsLikeC", "--")
            humidity = curr.get("humidity", "--")
            wind = curr.get("windspeedKmph", "--")
            area = data.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", city or "Текущее место")
            return {
                "ok": True,
                "city": area,
                "temp": f"{temp}°C",
                "desc": desc,
                "feels_like": f"{feels}°C",
                "humidity": f"{humidity}%",
                "wind": f"{wind} км/ч"
            }
        except Exception as e:
            try:
                txt = assistant.tools.tool_get_weather(city or "")
                return {"ok": True, "city": city or "Погода", "temp": "", "desc": txt}
            except Exception:
                return {"ok": False, "error": str(e)}

    return app

def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False

async def start_web(assistant):
    selected_port = None
    for port in [8000, 8001, 8080]:
        if is_port_available(port):
            selected_port = port
            break
    if not selected_port:
        print("[WebPanel] Все веб-порты (8000, 8001, 8080) заняты!")
        return

    try:
        config = uvicorn.Config(create_app(assistant), host="0.0.0.0", port=selected_port, log_level="warning")
        server = uvicorn.Server(config)
        await server.serve()
    except (Exception, SystemExit, BaseException) as e:
        print(f"[WebPanel] Ошибка работы веб-сервера на порту {selected_port}: {e}")
