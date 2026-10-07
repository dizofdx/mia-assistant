# tg_bot.py — Telegram: текст + голосовые + прокси + автопереподключение
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import asyncio, os, datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, FSInputFile, BotCommand, BotCommandScopeDefault,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

def make_bar(percent, total_blocks=10):
    try:
        val = float(percent)
        filled = int(round(val / (100 / total_blocks)))
        filled = max(0, min(total_blocks, filled))
        return "▓" * filled + "░" * (total_blocks - filled)
    except Exception:
        return "░" * total_blocks

class TGBot:
    def __init__(self, assistant):
        self.a = assistant
        self.proxy = getattr(assistant.cfg, "TG_PROXY", None)
        self.always_voice = False
        self.bot = self._create_bot(self.proxy)
        self.dp = Dispatcher()
        self.dp.message.register(self.cmd_jarvis, Command("jarvis", "panel"))
        self.dp.message.register(self.cmd_start, Command("start", "help"))
        self.dp.message.register(self.cmd_screen, Command("screen"))
        self.dp.message.register(self.cmd_status, Command("status"))
        self.dp.message.register(self.cmd_scenarios, Command("scenarios"))
        self.dp.message.register(self.cmd_cmd, Command("cmd"))
        self.dp.message.register(self.cmd_cancel, Command("cancel"))
        self.dp.message.register(self.cmd_run, Command("run"))
        self.dp.message.register(self.cmd_del, Command("del", "delete", "remove"))
        self.dp.message.register(self.cmd_mute, Command("mute"))
        self.dp.message.register(self.cmd_unmute, Command("unmute"))
        self.dp.message.register(self.cmd_voice, Command("voice"))
        self.dp.message.register(self.cmd_music, Command("music", "яндекс", "музыка"))
        self.dp.callback_query.register(self.on_callback, F.data.startswith("jb:"))
        self.dp.message.register(self.on_voice, F.voice | F.audio | F.video_note)
        self.dp.message.register(self.on_text, F.text)

    def is_admin(self, msg: Message) -> bool:
        if not getattr(self.a.cfg, "ADMIN_ID", None):
            return True
        sender_id = str(msg.from_user.id).strip()
        admin_id = str(self.a.cfg.ADMIN_ID).strip()
        is_ok = (sender_id == admin_id)
        if not is_ok:
            print(f"[TG Security] Запрос от пользователя {sender_id} (@{msg.from_user.username}). ADMIN_ID: {admin_id}")
        return is_ok

    async def _check_admin(self, msg: Message) -> bool:
        if self.is_admin(msg):
            return True
        await msg.answer(
            f"🔒 <b>Доступ ограничен.</b>\n"
            f"Твой Telegram ID: <code>{msg.from_user.id}</code>\n"
            f"Чтобы управлять Мией, укажи этот ID как <code>ADMIN_ID = {msg.from_user.id}</code> в файле <code>config.py</code>.",
            parse_mode="HTML"
        )
        return False

    def get_main_reply_keyboard(self):
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⚡ JARVIS Панель"), KeyboardButton(text="🎵 Моя Волна")],
                [KeyboardButton(text="🎯 Фокус"), KeyboardButton(text="🎮 Отдых")],
                [KeyboardButton(text="📸 Скриншот"), KeyboardButton(text="📊 Статус")],
            ],
            resize_keyboard=True,
            is_persistent=True
        )

    def build_jarvis_panel_data(self):
        import psutil, datetime
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        d_disk = psutil.disk_usage('D:\\') if os.path.exists('D:\\') else psutil.disk_usage('C:\\')
        c_disk = psutil.disk_usage('C:\\')
        d_free = round(d_disk.free / (1024**3), 1)
        c_free = round(c_disk.free / (1024**3), 1)
        ram_used = round(ram.used / (1024**3), 1)
        ram_total = round(ram.total / (1024**3), 1)
        boot = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%H:%M (%d.%m)")

        cpu_bar = make_bar(cpu)
        ram_bar = make_bar(ram.percent)

        cur_vol = 50
        try:
            import comtypes
            comtypes.CoInitialize()
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            if speakers and speakers.EndpointVolume:
                cur_vol = round(float(speakers.EndpointVolume.GetMasterVolumeLevelScalar()) * 100)
        except Exception:
            pass
        vol_bar = make_bar(cur_vol)

        voice_pc = "🔇 ВЫКЛ" if self.a.is_muted else "🔊 ВКЛ"
        voice_tg = "🎙️ ВКЛ" if getattr(self, "always_voice", False) else "💬 ТЕКСТ"
        profile = getattr(self.a.voice, "profile", "anime")
        profile_names = {"jarvis": "⚡ Джарвис", "anime": "🌸 Аниме-тянка", "mia": "🌺 Мия"}
        profile_label = profile_names.get(profile, profile)
        model = getattr(self.a.cfg, "DEEPSEEK_MODEL", "deepseek-v4-flash")
        now_time = datetime.datetime.now().strftime("%H:%M:%S")

        text = (
            "⚡ <b>JARVIS HUD • Панель управления ПК</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"💻 <b>CPU:</b> <code>[{cpu_bar}] {cpu:.1f}%</code>\n"
            f"🧠 <b>RAM:</b> <code>[{ram_bar}] {ram.percent:.1f}%</code> ({ram_used}/{ram_total} ГБ)\n"
            f"🔊 <b>Громкость:</b> <code>[{vol_bar}] {cur_vol}%</code>\n"
            f"💾 <b>Диск C:</b> <code>{c_free} ГБ своб.</code>\n"
            f"💾 <b>Диск D:</b> <code>{d_free} ГБ своб.</code>\n"
            f"⏱️ <b>Аптайм:</b> <code>с {boot}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎭 <b>Голос:</b> <code>{profile_label}</code>\n"
            f"🔊 <b>Звук Мии на ПК:</b> <code>{voice_pc}</code>\n"
            f"🎙️ <b>Ответы в ТГ:</b> <code>{voice_tg}</code>\n"
            f"🧠 <b>Модель:</b> <code>{model}</code>\n"
            f"🕒 <i>Время: {now_time}</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Управляй компьютером в один клик:</i>"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="jb:refresh"),
                InlineKeyboardButton(text="📸 Скриншот", callback_data="jb:screen")
            ],
            [
                InlineKeyboardButton(text="🗔 Свернуть окна", callback_data="jb:win:min"),
                InlineKeyboardButton(text="🔒 Заблокировать ПК", callback_data="jb:win:lock")
            ],
            [
                InlineKeyboardButton(text="🎵 Моя Волна (Яндекс Музыка)", callback_data="jb:music:play")
            ],
            [
                InlineKeyboardButton(text="⏮️", callback_data="jb:media:prev"),
                InlineKeyboardButton(text="⏯️ Плей/Пауза", callback_data="jb:media:play_pause"),
                InlineKeyboardButton(text="⏭️", callback_data="jb:media:next"),
                InlineKeyboardButton(text="🔇 Звук", callback_data="jb:media:mute")
            ],
            [
                InlineKeyboardButton(text=f"🔉 Тише ({cur_vol}%)", callback_data="jb:vol:down"),
                InlineKeyboardButton(text=f"🔊 Громче ({cur_vol}%)", callback_data="jb:vol:up")
            ],
            [
                InlineKeyboardButton(text="🎯 Режим «Фокус»", callback_data="jb:run:фокус"),
                InlineKeyboardButton(text="🎮 Режим «Отдых»", callback_data="jb:run:отдых")
            ],
            [
                InlineKeyboardButton(text="⚡ Голос: Джарвис", callback_data="jb:voice:jarvis"),
                InlineKeyboardButton(text="🌸 Голос: Аниме", callback_data="jb:voice:anime")
            ],
            [
                InlineKeyboardButton(text=f"Голос на ПК: {voice_pc}", callback_data="jb:toggle_mute"),
                InlineKeyboardButton(text=f"Войсы в ТГ: {voice_tg}", callback_data="jb:toggle_voice")
            ],
            [
                InlineKeyboardButton(text="📋 Все сценарии", callback_data="jb:scenarios")
            ]
        ])
        return text, kb

    async def cmd_jarvis(self, msg: Message):
        if not await self._check_admin(msg):
            return
        self.a.last_chat_id = msg.chat.id
        text, kb = self.build_jarvis_panel_data()
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")

    async def on_callback(self, cq: CallbackQuery):
        if not getattr(self.a.cfg, "ADMIN_ID", None) or str(cq.from_user.id).strip() == str(self.a.cfg.ADMIN_ID).strip():
            pass
        else:
            await cq.answer("🔒 Нет доступа", show_alert=True)
            return

        data = cq.data or ""
        self.a.last_chat_id = cq.message.chat.id

        if data == "jb:refresh":
            try:
                text, kb = self.build_jarvis_panel_data()
                await cq.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
                await cq.answer("⚡ Телеметрия обновлена!")
            except TelegramBadRequest:
                await cq.answer("⚡ Данные актуальны")
            except Exception as e:
                await cq.answer(f"Ошибка: {e}")

        elif data == "jb:screen":
            await cq.answer("📸 Делаю скриншот...")
            try:
                path = await asyncio.to_thread(self.a.tools.tool_screenshot)
                if path and os.path.exists(path):
                    await self.bot.send_photo(cq.message.chat.id, FSInputFile(path), caption="📸 Скриншот экрана твоего ПК")
                else:
                    await self.bot.send_message(cq.message.chat.id, "⚠️ Не удалось захватить экран ПК.")
            except Exception as e:
                await self.bot.send_message(cq.message.chat.id, f"⚠️ Ошибка скриншота: {e}")

        elif data == "jb:win:min":
            self.a.tools.tool_window_control("minimize_all")
            await cq.answer("🗔 Все окна свернуты")

        elif data == "jb:win:lock":
            self.a.tools.tool_window_control("lock_pc")
            await cq.answer("🔒 ПК заблокирован")

        elif data.startswith("jb:media:"):
            action = data.split(":")[-1]
            res = self.a.tools.tool_media_control(action)
            try:
                text, kb = self.build_jarvis_panel_data()
                await cq.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            await cq.answer(f"🎵 {res}")

        elif data.startswith("jb:vol:"):
            direction = data.split(":")[-1]
            res = self.a.tools.tool_volume(direction)
            try:
                text, kb = self.build_jarvis_panel_data()
                await cq.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            await cq.answer(f"{res}")

        elif data.startswith("jb:voice:"):
            profile = data.split(":")[-1]
            cur = self.a.set_voice_profile(profile)
            profile_names = {"jarvis": "⚡ Джарвис (мужской)", "anime": "🌸 Аниме-тянка (Ксения)", "mia": "🌺 Мия (Бая)"}
            name = profile_names.get(cur, cur)
            try:
                text, kb = self.build_jarvis_panel_data()
                await cq.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            await cq.answer(f"Голос: {name}")
            await self.bot.send_message(cq.message.chat.id, f"🎙️ <b>Голос Мии изменен на:</b> {name}", parse_mode="HTML")

        elif data == "jb:toggle_mute":
            self.a.toggle_muted()
            try:
                text, kb = self.build_jarvis_panel_data()
                await cq.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            st = "выключен 🔇" if self.a.is_muted else "включен 🔊"
            await cq.answer(f"Голос Мии на ПК: {st}")

        elif data == "jb:toggle_voice":
            self.always_voice = not self.always_voice
            try:
                text, kb = self.build_jarvis_panel_data()
                await cq.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            st = "включены 🎙️" if self.always_voice else "выключены 💬"
            await cq.answer(f"Голосовые ответы в ТГ: {st}")

        elif data == "jb:scenarios":
            buttons = []
            if hasattr(self.a, "vc_manager"):
                for vf in self.a.vc_manager.list_flows():
                    f_id = vf.get("id")
                    f_name = vf.get("name", f_id)
                    buttons.append([InlineKeyboardButton(text=f"⚡ {f_name}", callback_data=f"jb:run:{f_id}")])
            for s in self.a.scenarios.list_all():
                if isinstance(s, dict) and s.get("name"):
                    name = s["name"]
                    buttons.append([InlineKeyboardButton(text=f"▶️ {name}", callback_data=f"jb:run:{name}")])
            buttons.append([InlineKeyboardButton(text="⬅️ Назад в Jarvis", callback_data="jb:refresh")])
            await cq.message.edit_text("📋 <b>Выбери команду для выполнения на ПК:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
            await cq.answer()

        elif data == "jb:music:play":
            await cq.answer("🎵 Включаю Мою Волну...")
            res = self.a.tools.tool_play_yandex_music()
            await self.bot.send_message(cq.message.chat.id, f"🎵 <b>{res}</b>", parse_mode="HTML")

        elif data.startswith("jb:run:"):
            name = data.replace("jb:run:", "")
            await cq.answer(f"▶️ Выполняю на ПК...")
            try:
                if hasattr(self.a, "vc_manager"):
                    v_res = await self.a.vc_manager.execute_flow(name)
                    if v_res.get("ok"):
                        f_name = v_res.get("name", name)
                        await self.bot.send_message(cq.message.chat.id, f"✅ <b>Команда «{f_name}» выполнена на ПК!</b>", parse_mode="HTML")
                        return
                res = await self.a.scenarios.run(name)
                await self.bot.send_message(cq.message.chat.id, f"✅ <b>{res}</b>", parse_mode="HTML")
            except Exception as e:
                await self.bot.send_message(cq.message.chat.id, f"⚠️ Ошибка команды: {e}")

    async def cmd_music(self, msg: Message):
        if not await self._check_admin(msg):
            return
        await self.bot.send_chat_action(msg.chat.id, "typing")
        res = self.a.tools.tool_play_yandex_music()
        await msg.answer(f"🎵 <b>{res}</b>", parse_mode="HTML")

    async def cmd_start(self, msg: Message):
        if not await self._check_admin(msg):
            return
        text = (
            "🎀 <b>Привет! Я Мия — твоя напарница и голосовой помощник.</b>\n\n"
            "✨ <b>Главные возможности:</b>\n"
            "⚡ /jarvis — <b>Интерактивная панель JARVIS (HUD + телеметрия + медиа)</b>\n"
            "📸 /screen — Сделать скриншот экрана ПК\n"
            "📊 /status — Статус системы, звука и ИИ-модели\n"
            "🔇 /mute — Выключить голос Мии на ПК\n"
            "🔊 /unmute — Включить голос Мии на ПК\n"
            "🎙️ /voice — Вкл/выкл голосовые ответы в Телеграме\n"
            "📋 /scenarios — Список доступных сценариев\n"
            "▶️ /run <i>имя</i> — Запустить сценарий (напр. <code>/run отдых</code>)\n"
            "💻 /cmd <i>команда</i> — Выполнить команду на ПК (напр. <code>/cmd dir</code>)\n"
            "🛑 /cancel — Отменить выключение ПК\n\n"
            "💬 <i>Ты можешь писать мне любые вопросы или отправлять голосовые сообщения!</i>"
        )
        await msg.answer(text, reply_markup=self.get_main_reply_keyboard(), parse_mode="HTML")

    async def cmd_screen(self, msg: Message):
        if not await self._check_admin(msg):
            return
        self.a.last_chat_id = msg.chat.id
        await self.bot.send_chat_action(msg.chat.id, "upload_photo")
        try:
            path = await asyncio.to_thread(self.a.tools.tool_screenshot)
            if path and os.path.exists(path):
                await msg.answer_photo(FSInputFile(path), caption="📸 Скриншот экрана твоего ПК")
            else:
                await msg.answer("⚠️ Не удалось захватить экран ПК.")
        except Exception as e:
            print(f"[TG Screen Error] {e}")
            await msg.answer(f"⚠️ Ошибка создания скриншота: {e}")

    async def cmd_status(self, msg: Message):
        if not await self._check_admin(msg):
            return
        try:
            mute_st = "🔇 Выключен (Мия молчит)" if self.a.is_muted else "🔊 Включен (Мия озвучивает)"
            voice_tg_st = "ВКЛЮЧЕНЫ (голосовые на всё)" if getattr(self, "always_voice", False) else "ВЫКЛЮЧЕНЫ (только текст)"
            engine = getattr(self.a.cfg, "TTS_ENGINE", "edge_tts")
            model = getattr(self.a.cfg, "LLM_MODEL", "qwen2.5:3b-instruct")

            text = (
                "📊 <b>Статус Мии:</b>\n\n"
                f"🔊 <b>Голос Мии на ПК:</b> {mute_st}\n"
                f"🎙️ <b>Голосовые ответы в ТГ:</b> {voice_tg_st}\n"
                f"🧠 <b>LLM модель:</b> <code>{model}</code> (GPU)\n"
                f"🗣️ <b>Голосовой движок:</b> <code>{engine}</code>\n"
                f"🌐 <b>Веб-панель:</b> http://localhost:8000\n"
                f"💻 <b>ПК и агент:</b> Онлайн ✅"
            )
            await msg.answer(text, parse_mode="HTML")
        except Exception as e:
            print(f"[TG Status Error] {e}")
            await msg.answer(f"⚠️ Ошибка получения статуса: {e}")

    async def cmd_scenarios(self, msg: Message):
        if not await self._check_admin(msg):
            return
        scs = self.a.scenarios.list_all()
        if not scs:
            await msg.answer("📋 Сценариев пока нет. Создай их в веб-панели http://localhost:8000")
            return
        lines = ["📋 <b>Доступные сценарии:</b>\n"]
        for s in scs:
            name = s.get("name", "без имени")
            en = "✅" if s.get("enabled", True) else "⏸️"
            trig = s.get("trigger", {}).get("type", "ручной")
            lines.append(f"{en} <b>{name}</b> (триггер: {trig}) — запуск: <code>/run {name}</code>")
        await msg.answer("\n".join(lines), parse_mode="HTML")

    async def cmd_cmd(self, msg: Message):
        if not await self._check_admin(msg):
            return
        cmd_text = msg.text.replace("/cmd", "", 1).strip()
        if not cmd_text:
            await msg.answer("Использование: <code>/cmd dir</code> или <code>/cmd tasklist</code>", parse_mode="HTML")
            return
        await self.bot.send_chat_action(msg.chat.id, "typing")
        try:
            res = self.a.tools.tool_run_command(cmd_text)
            if len(res) > 3800:
                res = res[:3800] + "\n... (обрезано)"
            await msg.answer(f"<pre>{res}</pre>", parse_mode="HTML")
        except Exception as e:
            await msg.answer(f"⚠️ Ошибка выполнения команды: {e}")

    async def cmd_voice(self, msg: Message):
        if not await self._check_admin(msg):
            return
        self.always_voice = not self.always_voice
        st = "ВКЛЮЧЕНЫ (отвечаю голосовыми на любые сообщения)" if self.always_voice else "ВЫКЛЮЧЕНЫ (отвечаю текстом, голосовые только если ты прислал войс)"
        await msg.answer(f"🎙️ Голосовые ответы: {st}")

    async def cmd_mute(self, msg: Message):
        if not await self._check_admin(msg):
            return
        self.a.set_muted(True)
        await msg.answer("🔇 Мия теперь молчит и отвечает только текстом.")

    async def cmd_unmute(self, msg: Message):
        if not await self._check_admin(msg):
            return
        self.a.set_muted(False)
        await msg.answer("🔊 Звук включен! Мия снова озвучивает ответы вслух.")

    async def cmd_cancel(self, msg: Message):
        if not await self._check_admin(msg):
            return
        self.a.tools.tool_cancel_shutdown()
        await msg.answer("✅ Выключение отменено")

    async def cmd_run(self, msg: Message):
        if not await self._check_admin(msg):
            return
        name = msg.text.replace("/run", "", 1).strip()
        if not name:
            all_cmds = []
            for s in self.a.scenarios.list_all():
                if isinstance(s, dict) and s.get("name"): all_cmds.append(s["name"])
            if hasattr(self.a, "vc_manager"):
                for vf in self.a.vc_manager.list_flows():
                    if vf.get("id"): all_cmds.append(vf["id"])
            cmds_str = ", ".join(f"<code>{c}</code>" for c in all_cmds)
            await msg.answer(f"Укажи имя команды или сценария, например: <code>/run lock_pc</code>\n\n📋 <b>Доступные:</b> {cmds_str}", parse_mode="HTML")
            return

        # 1. Сначала проверяем визуальные команды
        if hasattr(self.a, "vc_manager"):
            v_res = await self.a.vc_manager.execute_flow(name)
            if v_res.get("ok"):
                flow_title = v_res.get("name", name)
                await msg.answer(f"✅ Команда <b>«{flow_title}»</b> успешно выполнена на ПК!", parse_mode="HTML")
                return

        # 2. Затем старые сценарии
        s = self.a.scenarios.get(name)
        if not s:
            await msg.answer(f"❌ Команда или сценарий <b>«{name}»</b> не найдены.", parse_mode="HTML")
            return
        real_name = s.get("name")
        await msg.answer(f"▶️ Запускаю сценарий: <b>{real_name}</b>...", parse_mode="HTML")
        try:
            res = await self.a.scenarios.run(real_name)
            await msg.answer(f"✅ {res}", parse_mode="HTML")
        except Exception as e:
            await msg.answer(f"⚠️ Ошибка выполнения сценария: {e}")

    async def cmd_del(self, msg: Message):
        if not await self._check_admin(msg):
            return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await msg.answer("Использование: <code>/del имя_команды</code>\nНапример: <code>/del lofi</code>", parse_mode="HTML")
            return
        name = parts[1].strip()
        res = self.a.tools.tool_delete_scenario(name)
        await msg.answer(f"🗑️ <b>{res}</b>", parse_mode="HTML")

    async def on_voice(self, msg: Message):
        if not await self._check_admin(msg):
            return
        self.a.last_chat_id = msg.chat.id
        await self.bot.send_chat_action(msg.chat.id, "typing")
        try:
            file_obj = msg.voice or msg.audio or msg.video_note
            file = await self.bot.get_file(file_obj.file_id)
            os.makedirs("memory", exist_ok=True)
            path = "memory/voice.ogg"
            await self.bot.download_file(file.file_path, path)
            text = await asyncio.to_thread(self.a.ears.transcribe, path)
            if not text:
                await msg.answer("🤔 Не смогла разобрать речь в сообщении, скажи ещё раз четче?")
                return
            await msg.answer(f"🎤 «{text}»")
            low_voice = text.lower().strip()

            low_voice = text.lower().strip()
            emotion, clean, raw = await self.a.handle_user_message(text, speak=False, source="telegram")
            await msg.answer(clean)

            # Если команда была на скриншот — прикрепляем фото экрана в ТГ
            if any(kw in low_voice for kw in ["скриншот", "скрин", "снимок", "сфоткай"]):
                p_scr = "memory/screenshot.png"
                if os.path.exists(p_scr):
                    try:
                        await self.bot.send_photo(msg.chat.id, FSInputFile(p_scr), caption="📸 Скриншот экрана твоего ПК")
                    except Exception as e_scr:
                        print(f"[TG] Ошибка отправки фото: {e_scr}")

            # Отправка голосового ответа на входящее голосовое сообщение
            try:
                await self.bot.send_chat_action(msg.chat.id, "upload_voice")
                v_path = await self.a.voice.generate_voice_file(clean, emotion=emotion)
                if v_path and os.path.exists(v_path):
                    try:
                        await msg.answer_voice(FSInputFile(v_path))
                    except Exception as e_v:
                        print(f"[TG] answer_voice fallback to audio: {e_v}")
                        await msg.answer_audio(FSInputFile(v_path), caption="🎙️ Голос Мии")
            except Exception as e:
                print(f"[TG] Ошибка отправки голосового: {e}")
        except Exception as e:
            print(f"[TG] Ошибка обработки голосового: {e}")
            await msg.answer(f"⚠️ Ошибка обработки голосового: {e}")

    async def on_text(self, msg: Message):
        if not self.is_admin(msg):
            return
        self.a.last_chat_id = msg.chat.id
        txt = (msg.text or "").strip()

        low = txt.lower().strip()

        # Быстрые команды музыки
        music_triggers = [
            "музыка", "включи музыку", "яндекс музыка", "включи яндекс музыку",
            "я.музыка", "включи я.музыку", "вруби музыку", "включи трек", "включи треки",
            "запусти музыку", "play music", "музыку", "поставь музыку", "плей", "play",
            "мою волну", "моя волна", "включи мою волну",
            "🎵 яндекс музыка", "🎵 моя волна"
        ]
        if txt in ["🎵 Яндекс Музыка", "🎵 Моя Волна"] or low in music_triggers or any(low.startswith(p) for p in ["включи музыку", "вруби музыку", "включи яндекс музыку", "включи я.музыку", "поставь музыку", "включи мою волну"]):
            await self.cmd_music(msg)
            return

        # Быстрые кнопки и триггеры сценария «Фокус»
        focus_triggers = [
            "фокус", "режим фокус", "режим «фокус»", "включи фокус", "включи режим фокус",
            "запусти фокус", "запусти режим фокус", "активируй фокус", "режим концентрации",
            "🎯 фокус"
        ]
        if txt == "🎯 Фокус" or low in focus_triggers or any(low.startswith(p) for p in ["включи режим фокус", "запусти режим фокус", "включи фокус", "запусти фокус"]):
            msg.text = "/run фокус"
            await self.cmd_run(msg)
            return

        # Быстрые кнопки и триггеры сценария «Отдых»
        rest_triggers = [
            "отдых", "режим отдых", "режим «отдых»", "включи отдых", "включи режим отдых",
            "запусти отдых", "запусти режим отдых", "активируй отдых", "хочу отдохнуть",
            "🎮 отдых"
        ]
        if txt == "🎮 Отдых" or low in rest_triggers or any(low.startswith(p) for p in ["включи режим отдых", "запусти режим отдых", "включи отдых", "запусти отдых"]):
            msg.text = "/run отдых"
            await self.cmd_run(msg)
            return

        # Управление медиа и громкостью текстом
        if low in ["пауза", "pause", "стоп"]:
            res = self.a.tools.tool_media_control("pause")
            await msg.answer(f"⏸️ {res}")
            return
        if low in ["плей", "play", "продолжи", "продолжить"]:
            res = self.a.tools.tool_media_control("play")
            await msg.answer(f"▶️ {res}")
            return
        if low in ["громче", "громче звук", "сделай громче", "прибавь звук", "прибавь громкость"]:
            res = self.a.tools.tool_volume("up")
            await msg.answer(f"🔊 {res}")
            return
        if low in ["тише", "тише звук", "сделай тише", "убавь звук", "убавь громкость"]:
            res = self.a.tools.tool_volume("down")
            await msg.answer(f"🔉 {res}")
            return

        # Переключение голоса текстом
        if low in ["голос джарвиса", "джарвис", "включи джарвиса", "режим джарвиса"]:
            cur = self.a.set_voice_profile("jarvis")
            await msg.answer("⚡ <b>Голосовой профиль переключен на: Джарвис (мужской)</b>", parse_mode="HTML")
            return
        if low in ["голос аниме", "аниме", "голос тянки", "аниме тянка", "включи аниме"]:
            cur = self.a.set_voice_profile("anime")
            await msg.answer("🌸 <b>Голосовой профиль переключен на: Аниме-тянка (Ксения)</b>", parse_mode="HTML")
            return
        if low in ["голос мии", "миечка", "классический голос", "верни мию"]:
            cur = self.a.set_voice_profile("mia")
            await msg.answer("🌺 <b>Голосовой профиль переключен на: Мия (Бая)</b>", parse_mode="HTML")
            return

        # Быстрые команды меню
        if txt == "⚡ JARVIS Панель" or low in ["джарвис", "jarvis", "панель", "hud"]:
            await self.cmd_jarvis(msg)
            return
        elif txt == "📸 Скриншот" or low in ["скрин", "скриншот", "экран"]:
            await self.cmd_screen(msg)
            return
        elif txt == "📊 Статус" or low in ["статус", "состояние"]:
            await self.cmd_status(msg)
            return

        # Удаление команды или сценария
        for pref in ["удали команду ", "удали сценарий ", "удалить команду ", "удалить сценарий "]:
            if low.startswith(pref):
                del_name = low.replace(pref, "").strip()
                res = self.a.tools.tool_delete_scenario(del_name)
                await msg.answer(f"🗑️ <b>{res}</b>", parse_mode="HTML")
                return

        await self.bot.send_chat_action(msg.chat.id, "typing")
        emotion, clean, raw = await self.a.handle_user_message(msg.text, speak=False, source="telegram")
        await msg.answer(clean)

        if getattr(self, "always_voice", False):
            try:
                await self.bot.send_chat_action(msg.chat.id, "upload_voice")
                v_path = await self.a.voice.generate_voice_file(clean, emotion=emotion)
                if v_path and os.path.exists(v_path):
                    try:
                        await msg.answer_voice(FSInputFile(v_path))
                    except Exception as e_v:
                        print(f"[TG] answer_voice fallback to audio: {e_v}")
                        await msg.answer_audio(FSInputFile(v_path), caption="🎙️ Голос Мии")
            except Exception as e:
                print(f"[TG] Ошибка отправки голосового: {e}")

    async def send_photo(self, path):
        if self.a.last_chat_id:
            await self.bot.send_photo(self.a.last_chat_id, FSInputFile(path))

    def _create_bot(self, proxy):
        api_server = getattr(self.a.cfg, "TG_API_SERVER", None)
        api = TelegramAPIServer.from_base(api_server) if api_server else None

        if api_server:
            print(f"[TG] Telegram подключен через Cloudflare Worker: {api_server}")
        elif proxy:
            print(f"[TG] Telegram пробует прокси: {proxy}")
        else:
            print("[TG] Telegram подключается напрямую (без VPN)")

        session = AiohttpSession(proxy=proxy, api=api)
        return Bot(self.a.cfg.TG_TOKEN, session=session)

    async def notify(self, text, parse_mode="HTML"):
        target_id = self.a.last_chat_id or getattr(self.a.cfg, "ADMIN_ID", None)
        if target_id:
            try:
                await self.bot.send_message(target_id, text, parse_mode=parse_mode)
            except Exception:
                try:
                    await self.bot.send_message(target_id, text)
                except Exception:
                    pass

    async def setup_commands(self):
        """Регистрирует список команд в Telegram: появляется кнопка 'Меню' и подсказки при вводе '/'."""
        commands = [
            BotCommand(command="jarvis", description="⚡ Панель управления JARVIS (HUD + пульт)"),
            BotCommand(command="start", description="📖 Справка и меню возможностей"),
            BotCommand(command="screen", description="📸 Скриншот экрана твоего ПК"),
            BotCommand(command="status", description="📊 Статус системы, звука и ИИ"),
            BotCommand(command="mute", description="🔇 Выключить голос на ПК"),
            BotCommand(command="unmute", description="🔊 Включить голос на ПК"),
            BotCommand(command="voice", description="🎙️ Вкл/выкл голосовые ответы в ТГ"),
            BotCommand(command="scenarios", description="📋 Список сценариев автоматизации"),
            BotCommand(command="run", description="▶️ Запустить сценарий (/run отдых)"),
            BotCommand(command="cmd", description="💻 Выполнить команду на ПК"),
            BotCommand(command="cancel", description="🛑 Отменить выключение ПК"),
        ]
        try:
            await self.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
            print("[TG] Меню команд в Telegram успешно установлено!")
        except Exception as e:
            print(f"[TG] Ошибка установки команд: {e}")

    async def run(self):
        """Не падаем при сбое сети — при ошибке прокси автоматически переключаемся на прямое подключение."""
        using_proxy = bool(self.proxy)
        await self.setup_commands()
        while True:
            try:
                print("[TG] Подключаюсь к Telegram...")
                await self.dp.start_polling(self.bot)
            except Exception as e:
                err_str = str(e).lower()
                # Если прокси недоступен (VPN выключен, порт закрыт и т.д.), переключаемся на прямое подключение
                if using_proxy and any(w in err_str for w in ["proxy", "connect", "refused", "10809", "1443"]):
                    print(f"[TG] Прокси {self.proxy} недоступен (возможно, VPN выключен).")
                    print("     Автоматически переключаюсь на прямое подключение без VPN...")
                    try:
                        await self.bot.session.close()
                    except Exception:
                        pass
                    self.bot = self._create_bot(None)
                    using_proxy = False
                    await asyncio.sleep(2)
                    continue

                print(f"[TG] Telegram недоступен ({type(e).__name__}). Повтор через 15 сек...")
                print("     Веб-панель http://localhost:8000 при этом работает.")
                await asyncio.sleep(15)