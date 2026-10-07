# voice.py — озвучка ответов (Silero TTS v4 + Edge-TTS fallback)
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio, io, os, re, edge_tts
import sounddevice as sd
import soundfile as sf

# Диапазоны Unicode эмодзи
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-c
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed alphanumerics
    "\u200d"                 # zero-width joiner
    "\ufe0e-\ufe0f"          # variation selectors
    "]+",
    flags=re.UNICODE
)

# Текстовые смайлики (типа :-), =), :D, ^_^, <3)
TEXT_EMOTICONS = re.compile(
    r'(?<!\w)(?:'
    r'[:;=8]-?[)\](\/\\DpP*oO|3]|'
    r'[)\](]-?[:;=8]|'
    r'\^_\^|<3|xD|XD'
    r')(?!\w)'
)

# Словарь фонетической адаптации названий сервисов и терминов для русского синтеза речи
TTS_WORD_REPLACEMENTS = {
    r'\btelegram\b': 'Телеграм',
    r'\btg\b': 'Телеграм',
    r'\byoutube\b': 'Ютуб',
    r'\byt\b': 'Ютуб',
    r'\byandex\b': 'Яндекс',
    r'\bayugram\b': 'Аюграм',
    r'\bdiscord\b': 'Дискорд',
    r'\bchrome\b': 'Хром',
    r'\bgoogle\b': 'Гугл',
    r'\bwindows\b': 'Виндовс',
    r'\bwin\b': 'Виндовс',
    r'\bspotify\b': 'Спотифай',
    r'\bsteam\b': 'Стим',
    r'\bvk\b': 'Вэка',
    r'\bpc\b': 'пэка',
    r'\bai\b': 'ИИ',
    r'\bllm\b': 'эллэм',
    r'\bgpu\b': 'джипию',
    r'\bcpu\b': 'сипию',
    r'\bram\b': 'озу',
    r'\bgb\b': 'гигабайт',
    r'\bmb\b': 'мегабайт',
    r'\bkb\b': 'килобайт',
    r'\bcmd\b': 'командная строка',
    r'\bpowershell\b': 'пауэршелл',
    r'\bvpn\b': 'вэпээн',
    r'\bwi-?fi\b': 'вайфай',
    r'\bbluetooth\b': 'блютуз',
    r'\bok\b': 'окей',
    r'\bokay\b': 'окей',
    r'\byes\b': 'да',
    r'\bno\b': 'нет',
    r'\bonline\b': 'онлайн',
    r'\boffline\b': 'офлайн',
}

LATIN_TO_CYRILLIC = {
    'shch': 'щ', 'yo': 'ё', 'zh': 'ж', 'ch': 'ч', 'sh': 'ш', 'yu': 'ю', 'ya': 'я',
    'th': 'с', 'ph': 'ф', 'ck': 'к', 'oo': 'у', 'ee': 'и', 'ea': 'и',
    'a': 'а', 'b': 'б', 'c': 'к', 'd': 'д', 'e': 'е', 'f': 'ф', 'g': 'г',
    'h': 'х', 'i': 'и', 'j': 'дж', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н',
    'o': 'о', 'p': 'п', 'q': 'к', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
    'v': 'в', 'w': 'в', 'x': 'кс', 'y': 'и', 'z': 'з'
}

NUMS_RU = {
    0: "ноль", 1: "один", 2: "два", 3: "три", 4: "четыре", 5: "пять",
    6: "шесть", 7: "семь", 8: "восемь", 9: "девять", 10: "десять",
    11: "одиннадцать", 12: "двенадцать", 13: "тринадцать", 14: "четырнадцать", 15: "пятнадцать",
    16: "шестнадцать", 17: "семнадцать", 18: "восемнадцать", 19: "девятнадцать", 20: "двадцать",
    30: "тридцать", 40: "сорок", 50: "пятьдесят", 60: "шестьдесят", 70: "семьдесят",
    80: "восемьдесят", 90: "девяносто", 100: "сто", 200: "двести", 300: "триста",
    400: "четыреста", 500: "пятьсот", 600: "шестьсот", 700: "семьсот", 800: "восемьсот", 900: "девятьсот"
}

def int_to_ru_words(n: int) -> str:
    if n < 0:
        return "минус " + int_to_ru_words(-n)
    if n in NUMS_RU:
        return NUMS_RU[n]
    if n < 100:
        tens = (n // 10) * 10
        rem = n % 10
        return f"{NUMS_RU[tens]} {NUMS_RU[rem]}"
    if n < 1000:
        hundreds = (n // 100) * 100
        rem = n % 100
        if rem == 0:
            return NUMS_RU[hundreds]
        return f"{NUMS_RU[hundreds]} {int_to_ru_words(rem)}"
    if n < 1000000:
        thousands = n // 1000
        rem = n % 1000
        if thousands % 10 == 1 and thousands % 100 != 11:
            th_word = "тысяча"
            th_str = int_to_ru_words(thousands)
            if th_str.endswith("один"):
                th_str = th_str[:-4] + "одна"
        elif thousands % 10 in [2, 3, 4] and thousands % 100 not in [12, 13, 14]:
            th_word = "тысячи"
            th_str = int_to_ru_words(thousands)
            if th_str.endswith("два"):
                th_str = th_str[:-3] + "две"
        else:
            th_word = "тысяч"
            th_str = int_to_ru_words(thousands)
        if rem == 0:
            return f"{th_str} {th_word}"
        return f"{th_str} {th_word} {int_to_ru_words(rem)}"
    return str(n)

def normalize_numbers(text: str) -> str:
    # Заменяем знаки процентов, градусов и распространенных величин
    text = re.sub(r'(\d+)\s*%', r'\1 процентов', text)
    text = re.sub(r'(\d+)\s*°[cCсС]?', r'\1 градусов', text)
    text = re.sub(r'(\d+)\s*([гg][бb]|гигабайт\w*)', r'\1 гигабайт', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d+)\s*([мm][бb]|мегабайт\w*)', r'\1 мегабайт', text, flags=re.IGNORECASE)
    def _repl(m):
        try:
            val = int(m.group(0))
            if val <= 999999:
                return int_to_ru_words(val)
        except Exception:
            pass
        return m.group(0)
    return re.sub(r'\b\d+\b', _repl, text)

def transliterate_latin(text: str) -> str:
    """Транслитерирует любые оставшиеся латинские слова в кириллицу, чтобы Silero не глотал их и не падал."""
    def _repl(match):
        w = match.group(0).lower()
        for k, v in LATIN_TO_CYRILLIC.items():
            w = w.replace(k, v)
        return w
    return re.sub(r'[a-zA-Z]+', _repl, text)

def clean_for_speech(text: str) -> str:
    """Удаляет из текста для озвучки блоки кода, теги эмоций [радость], ремарки *улыбается*, инлайн-код, эмодзи, смайлики и адаптирует термины для русской речи."""
    if not text:
        return ""
    
    had_code = bool(re.search(r'```[\s\S]*?```|`[^`]+`', text))

    # 1. Удаляем блоки кода ```...```
    clean = re.sub(r'```[\s\S]*?```', '', text)
    # 2. Удаляем инлайн-код `...`
    clean = re.sub(r'`[^`]*`', '', clean)
    # 3. Удаляем любые теги в квадратных скобках [РАДОСТЬ], [смех], [действие]
    clean = re.sub(r'\[[^\]]*\]', '', clean)
    # 4. Удаляем текстовые действия/ремарки типа *улыбается*, *машет рукой*
    clean = re.sub(r'\*[^*]+\*', '', clean)
    # 5. Удаляем ремарки в круглых скобках (улыбается), (хихикает), (зевает)
    clean = re.sub(r'\([^)]{1,40}\)', '', clean)
    # 6. Удаляем эмодзи и смайлы
    clean = EMOJI_PATTERN.sub('', clean)
    clean = TEXT_EMOTICONS.sub('', clean)
    # 7. Удаляем кавычки, скобки и спецсимволы, которых нет в алфавите Silero
    clean = re.sub(r'[«»""„“\'`\(\)\[\]\{\}<>/\\|@#$%^&*+=~]', ' ', clean)
    # 8. Удаляем оставшееся markdown-форматирование
    clean = re.sub(r'[*_~#]+', '', clean)
    # 9. Удаляем веб-ссылки
    clean = re.sub(r'https?://\S+', '', clean)

    # 9. Фонетическая замена частых англоязычных терминов и брендов
    for pattern, rep in TTS_WORD_REPLACEMENTS.items():
        clean = re.sub(pattern, rep, clean, flags=re.IGNORECASE)

    # 10. Транслитерация оставшихся английских слов в кириллицу (Silero понимает только кириллицу)
    clean = transliterate_latin(clean)

    # 11. Нормализуем числа и цифры в словесную русскую форму (чтобы Silero не проглатывал цифры!)
    clean = normalize_numbers(clean)

    # 12. Расставляем правильные ударения (+) для выразительного и человечного произношения
    stress_words = {
        r'\bяндекс\b': 'Я+ндекс',
        r'\bяндексе\b': 'Я+ндексе',
        r'\bяндекса\b': 'Я+ндекса',
        r'\bмузыка\b': 'му+зыка',
        r'\bмузыку\b': 'му+зыку',
        r'\bмузыке\b': 'му+зыке',
        r'\bютуб\b': 'юту+б',
        r'\bютубе\b': 'юту+бе',
        r'\bютуба\b': 'юту+ба',
        r'\bвключила\b': 'включи+ла',
        r'\bоткрыла\b': 'откры+ла',
        r'\bсделала\b': 'сде+лала',
        r'\bпоняла\b': 'поняла+',
        r'\bслушаю\b': 'слу+шаю',
        r'\bфокус\b': 'фо+кус',
        r'\bфокуса\b': 'фо+куса',
        r'\bотдых\b': 'о+тдых',
        r'\bотдыха\b': 'о+тдыха',
        r'\bлофай\b': 'ло+фай',
        r'\bджарвис\b': 'джа+рвис',
        r'\bджарвиса\b': 'джа+рвиса',
        r'\bаниме\b': 'а+ниме',
        r'\bсемпай\b': 'семпа+й',
        r'\bсекунду\b': 'секу+нду',
        r'\bминуту\b': 'мину+ту',
        r'\bминут\b': 'мину+т',
        r'\bгромче\b': 'гро+мче',
        r'\bпогромче\b': 'погро+мче',
        r'\bтише\b': 'ти+ше',
        r'\bпотише\b': 'поти+ше',
        r'\bголосовой\b': 'голосово+й',
        r'\bголосовые\b': 'голосовы+е',
    }
    for pat, val in stress_words.items():
        clean = re.sub(pat, val, clean, flags=re.IGNORECASE)

    # 13. Паузы и пунктуация: тире превращаем в запятую (чтобы была естественная интонационная пауза)
    clean = re.sub(r'\s*[-—–]\s*', ', ', clean)
    clean = re.sub(r'([.,!?;:])(?=[^\s])', r'\1 ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'\s+([.,!?])', r'\1', clean)

    # Если в сообщении был только код, произносим лаконичную фразу
    if not clean and had_code:
        return "Код я отправила в чат."
    return clean

# Интонационные параметры для каждой эмоции (молодой, живой тон без хрипоты)
EMOTION_VOICE_MODS = {
    "РАДОСТЬ":     {"rate": "+12%", "pitch": "+18Hz"},
    "СМЕХ":        {"rate": "+14%", "pitch": "+20Hz"},
    "УДИВЛЕНИЕ":   {"rate": "+10%", "pitch": "+22Hz"},
    "ГРУСТЬ":      {"rate": "-6%",  "pitch": "+6Hz"},
    "ЗЛОСТЬ":      {"rate": "+8%",  "pitch": "+8Hz"},
    "СМУЩЕНИЕ":    {"rate": "-2%",  "pitch": "+16Hz"},
    "ЗАДУМЧИВОСТЬ":{"rate": "-2%",  "pitch": "+12Hz"},
    "СПОКОЙСТВИЕ": {"rate": "+8%",  "pitch": "+14Hz"},
}

class Voice:
    def __init__(self, cfg):
        self.cfg = cfg
        self.is_speaking = False
        self._speak_lock = asyncio.Lock()
        self._silero_model = None
        self._silero_ready = False
        self.profile = getattr(cfg, "VOICE_PROFILE", "anime")
        self._cue_cache = {}
        self._phrase_cache = {}
        self._init_cues()
        self._init_silero()

    def set_profile(self, name):
        """Переключает профиль голоса: 'anime' (xenia), 'jarvis' (aidar), 'mia' (baya)."""
        name = (name or "").lower().strip()
        if any(w in name for w in ["jarvis", "джарвис", "aidar", "мужск", "робот"]):
            self.profile = "jarvis"
        elif any(w in name for w in ["anime", "аниме", "тянк", "xenia", "девочк"]):
            self.profile = "anime"
        elif any(w in name for w in ["mia", "мия", "baya", "классик"]):
            self.profile = "mia"
        else:
            self.profile = name
        return self.get_profile_name()

    def get_profile_name(self):
        mapping = {
            "anime": "🌸 Аниме-тянка",
            "jarvis": "⚡ Джарвис",
            "mia": "🌺 Мия (Классик)",
        }
        return mapping.get(self.profile, self.profile)

    def get_speaker(self):
        spk_map = {
            "anime": "xenia",
            "jarvis": "aidar",
            "mia": "baya",
        }
        return spk_map.get(self.profile, getattr(self.cfg, "SILERO_SPEAKER", "xenia"))

    @property
    def speaker(self):
        return self.get_speaker()

    async def generate_voice_file(self, text, output_path="memory/reply_voice.wav", emotion="СПОКОЙСТВИЕ"):
        """Генерирует аудиофайл для отправки голосовых сообщений в Telegram (Silero или Edge-TTS)."""
        clean_text = clean_for_speech(text)
        if not clean_text.strip():
            return None
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        engine = getattr(self.cfg, "TTS_ENGINE", "silero")

        async def _try_silero():
            for _ in range(60):
                if self._silero_ready:
                    break
                await asyncio.sleep(0.1)
            if self._silero_ready and self._silero_model:
                spk = self.get_speaker()
                sr = getattr(self.cfg, "SILERO_SAMPLE_RATE", 24000)
                safe_text = clean_text.replace("&", "и").replace("<", "").replace(">", "").strip()
                try:
                    audio_np = await asyncio.to_thread(self._synthesize_sentences, safe_text, spk, sr)
                    # Для Telegram Bot API голосовые сообщения обязаны быть OGG OPUS:
                    ogg_path = output_path.replace(".mp3", ".ogg").replace(".wav", ".ogg")
                    try:
                        sf.write(ogg_path, audio_np, sr, format="OGG", subtype="OPUS")
                        return ogg_path
                    except Exception as e_opus:
                        print(f"[Voice] Не удалось записать OGG OPUS ({e_opus}), fallback на WAV...")
                        wav_path = output_path.replace(".mp3", ".wav").replace(".ogg", ".wav")
                        sf.write(wav_path, audio_np, sr)
                        return wav_path
                except Exception as e_s:
                    print(f"[Voice] Ошибка генерации Silero: {e_s}")
            return None

        async def _try_edge():
            try:
                mods = EMOTION_VOICE_MODS.get((emotion or "").upper(), {"rate": "+8%", "pitch": "+14Hz"})
                rate = mods["rate"]
                pitch = mods["pitch"]
                tts = edge_tts.Communicate(clean_text, getattr(self.cfg, "TTS_VOICE", "ru-RU-SvetlanaNeural"), rate=rate, pitch=pitch)
                mp3_path = output_path.replace(".wav", ".mp3")
                await asyncio.wait_for(tts.save(mp3_path), timeout=4.0)
                if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
                    return mp3_path
            except Exception as e:
                print(f"[Voice] Edge-TTS не удался: {e}")
            return None

        if engine == "silero":
            res = await _try_silero()
            if res:
                return res
            return await _try_edge()
        else:
            res = await _try_edge()
            if res:
                return res
            return await _try_silero()

    def _init_silero(self):
        def _loader():
            try:
                import torch
                try:
                    torch.set_num_threads(4)
                except Exception:
                    pass
                model_path = os.path.join(os.path.dirname(__file__), "models", "v4_ru.pt")
                if not os.path.exists(model_path):
                    import urllib.request
                    os.makedirs(os.path.dirname(model_path), exist_ok=True)
                    urllib.request.urlretrieve("https://models.silero.ai/models/tts/ru/v4_ru.pt", model_path)
                device = torch.device("cpu")
                model = torch.package.PackageImporter(model_path).load_pickle("tts_models", "model")
                model.to(device)
                self._silero_model = model

                # Предварительный прогрев и кэширование типовых фраз для 0 мс мгновенного отклика:
                spk = getattr(self.cfg, "SILERO_SPEAKER", "xenia")
                sr = getattr(self.cfg, "SILERO_SAMPLE_RATE", 24000)
                try:
                    with torch.inference_mode():
                        _ = model.apply_tts(text="Мия", speaker=spk, sample_rate=sr, put_accent=False, put_yo=False)
                except Exception:
                    pass

                # Предзагрузка типовых фраз в RAM-кэш
                common_phrases = [
                    "Да, я слушаю!",
                    "Врубаю «Мою Волну» в Яндекс Музыке! 🎵",
                    "Поставила на паузу.",
                    "Продолжаю воспроизведение!",
                    "Включила следующий трек.",
                    "Вернула предыдущий трек.",
                    "Сделала погромче!",
                    "Сделала потише!",
                    "Выключила звук.",
                    "Включила звук обратно.",
                    "Все окна свернуты.",
                    "Компьютер заблокирован."
                ]
                for p in common_phrases:
                    try:
                        clean_p = clean_for_speech(p)
                        key = (clean_p, spk, sr)
                        if key not in self._phrase_cache:
                            with torch.inference_mode():
                                audio_t = model.apply_tts(text=clean_p, speaker=spk, sample_rate=sr, put_accent=False, put_yo=False)
                                self._phrase_cache[key] = audio_t.numpy()
                        self._phrase_cache[(p, spk, sr)] = self._phrase_cache[key]
                    except Exception:
                        pass

                self._silero_ready = True

                try:
                    print(f"[Silero] TTS ready (fast 24kHz mode)! Speaker: {spk}")
                except Exception:
                    pass
            except Exception as e:
                try:
                    import traceback
                    traceback.print_exc()
                    print(f"[Silero] Load error: {e}")
                except Exception:
                    pass

        import threading
        threading.Thread(target=_loader, daemon=True).start()

    def _synthesize_sentences(self, safe_text, spk, sr):
        """Синтезирует речь по предложениям с естественными дыхательными паузами и защитой от обрезания."""
        import numpy as np, torch
        raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?…\n])\s+', safe_text) if s.strip()]

        # Если предложение слишком длинное (>85 символов), дополнительно делим по запятым
        sentence_list = []
        for s in raw_sentences:
            if len(s) > 85 and ',' in s:
                sub_parts = [p.strip() for p in s.split(',') if p.strip()]
                for idx, part in enumerate(sub_parts):
                    if idx < len(sub_parts) - 1:
                        sentence_list.append(part + ',')
                    else:
                        sentence_list.append(part)
            else:
                sentence_list.append(s)

        if not sentence_list:
            sentence_list = [safe_text]

        chunks = []
        pause_samples = int(sr * 0.12)  # 120 мс мягкая естественная пауза между предложениями
        inter_silence = np.zeros(pause_samples, dtype=np.float32)

        def _synthesize_chunk(chunk_txt):
            if not chunk_txt.endswith(('.', '!', '?', '…', ',')):
                chunk_txt += '.'
            with torch.inference_mode():
                # Мгновенная генерация за 70 мс (без тяжелого словарного предиктора ударений)
                try:
                    audio_tensor = self._silero_model.apply_tts(
                        text=chunk_txt,
                        speaker=spk,
                        sample_rate=sr,
                        put_accent=False,
                        put_yo=False
                    )
                except Exception:
                    audio_tensor = self._silero_model.apply_tts(
                        text=chunk_txt,
                        speaker=spk,
                        sample_rate=sr
                    )
                return audio_tensor.numpy()

        for idx, sentence in enumerate(sentence_list):
            cache_key = (sentence, spk, sr)
            if cache_key in self._phrase_cache:
                audio_np = self._phrase_cache[cache_key]
            else:
                audio_np = _synthesize_chunk(sentence)
                if len(sentence) < 60 and len(self._phrase_cache) < 150:
                    self._phrase_cache[cache_key] = audio_np

            chunks.append(audio_np)
            if idx < len(sentence_list) - 1:
                chunks.append(inter_silence)

        # Добавляем 0.35 сек тишины в хвост аудио, чтобы аппаратура и буфер звуковой карты никогда не обрезали последнее слово
        chunks.append(np.zeros(int(sr * 0.35), dtype=np.float32))
        return np.concatenate(chunks)

    async def speak_silero(self, text, speaker=None, sample_rate=None):
        if not self._silero_ready or self._silero_model is None:
            raise RuntimeError("Silero not ready")
        
        spk = speaker or self.get_speaker()
        sr = sample_rate or getattr(self.cfg, "SILERO_SAMPLE_RATE", 24000)
        safe_text = text.replace("&", "и").replace("<", "").replace(">", "").strip()

        audio_to_play = await asyncio.to_thread(self._synthesize_sentences, safe_text, spk, sr)

        self.is_speaking = True
        try:
            sd.play(audio_to_play, sr, device=self.cfg.AUDIO_DEVICE)
            await asyncio.to_thread(sd.wait)
            await asyncio.sleep(0.06)
        finally:
            self.is_speaking = False

    async def speak_edge(self, text, emotion="СПОКОЙСТВИЕ"):
        mods = EMOTION_VOICE_MODS.get((emotion or "").upper(), {"rate": "+2%", "pitch": "+5Hz"})
        rate = mods["rate"]
        pitch = mods["pitch"]

        data = b""
        tts = edge_tts.Communicate(text, self.cfg.TTS_VOICE, rate=rate, pitch=pitch)
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                data += chunk["data"]
        audio, samplerate = sf.read(io.BytesIO(data), dtype="float32")
        self.is_speaking = True
        try:
            import numpy as np
            pad_samples = int(samplerate * 0.35)
            silence_pad = np.zeros(pad_samples, dtype=np.float32)
            audio_to_play = np.concatenate([audio, silence_pad])

            sd.play(audio_to_play, samplerate, device=self.cfg.AUDIO_DEVICE)
            await asyncio.to_thread(sd.wait)
            await asyncio.sleep(0.08)
        finally:
            self.is_speaking = False

    async def speak(self, text, emotion="СПОКОЙСТВИЕ"):
        clean_text = clean_for_speech(text)
        if not clean_text.strip():
            return

        async with self._speak_lock:
            engine = getattr(self.cfg, "TTS_ENGINE", "silero")
            if engine == "silero":
                # 1. Сначала локальный Silero (офлайн, мгновенно)
                for _ in range(60):
                    if self._silero_ready:
                        break
                    await asyncio.sleep(0.1)
                
                if self._silero_ready:
                    try:
                        await self.speak_silero(clean_text)
                        return
                    except Exception as e:
                        print(f"⚠️ Ошибка Silero ({e}), пробуем Edge-TTS...")
                else:
                    print("⚠️ Silero ещё загружается, пробуем Edge-TTS...")

                try:
                    await self.speak_edge(clean_text, emotion=emotion)
                except Exception as e2:
                    print(f"⚠️ Не удалось озвучить через Edge-TTS: {e2}")

            else:
                # 1. Сначала Edge-TTS
                try:
                    await self.speak_edge(clean_text, emotion=emotion)
                    return
                except Exception as e:
                    print(f"⚠️ Ошибка Edge-TTS ({e}), переключаюсь на локальный Silero...")
                    for _ in range(20):
                        if self._silero_ready:
                            break
                        await asyncio.sleep(0.1)
                    if self._silero_ready:
                        try:
                            await self.speak_silero(clean_text)
                        except Exception as e2:
                            print(f"⚠️ Ошибка Silero: {e2}")

    def _create_fallback_chime(self, path: str, cue_type: str):
        """Создает гармоничный звуковой сигнал при отсутствии файла."""
        try:
            import numpy as np
            sr = 48000
            if cue_type == "wake":
                # Восходящий двухтоновый звон D5 (587 Гц) -> A5 (880 Гц)
                d1, d2 = 0.09, 0.14
                t1 = np.linspace(0, d1, int(sr * d1), False)
                t2 = np.linspace(0, d2, int(sr * d2), False)
                env1 = np.exp(-t1 * 12.0)
                env2 = np.exp(-t2 * 9.0)
                s1 = (np.sin(2 * np.pi * 587.33 * t1) + 0.3 * np.sin(2 * np.pi * 1174.66 * t1)) * env1
                s2 = (np.sin(2 * np.pi * 880.0 * t2) + 0.3 * np.sin(2 * np.pi * 1760.0 * t2)) * env2
                fade_in = int(sr * 0.008)
                if len(s1) > fade_in:
                    s1[:fade_in] *= np.linspace(0, 1, fade_in)
                audio = np.concatenate([s1, s2])
                audio = audio * (0.28 / (np.max(np.abs(audio)) + 1e-6))
            else:
                # Мягкий гармоничный аккорд C6 (1046 Гц) + E6 (1318 Гц)
                dur = 0.22
                t = np.linspace(0, dur, int(sr * dur), False)
                env = np.exp(-t * 9.5)
                tone = 0.6 * np.sin(2 * np.pi * 1046.50 * t) + 0.4 * np.sin(2 * np.pi * 1318.51 * t)
                fade_in = int(sr * 0.008)
                if len(tone) > fade_in:
                    tone[:fade_in] *= np.linspace(0, 1, fade_in)
                audio = tone * env
                audio = audio * (0.26 / (np.max(np.abs(audio)) + 1e-6))
            sf.write(path, audio.astype(np.float32), sr)
        except Exception as e:
            print(f"[Voice] Не удалось сгенерировать сигнал {cue_type}: {e}")

    def _init_cues(self):
        """Инициализирует и предзагружает звуковые сигналы (wake, done)."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sounds_dir = os.path.join(base_dir, "sounds")
        os.makedirs(sounds_dir, exist_ok=True)
        cues = {
            "wake": os.path.join(sounds_dir, "wake.wav"),
            "done": os.path.join(sounds_dir, "done.wav"),
        }
        for name, path in cues.items():
            if not os.path.exists(path):
                self._create_fallback_chime(path, name)
            if os.path.exists(path):
                try:
                    data, sr = sf.read(path, dtype="float32")
                    self._cue_cache[name] = (data, sr)
                except Exception as e:
                    print(f"[Voice] Ошибка предзагрузки звука {name}: {e}")

    def play_cue_sync(self, name: str = "wake", wait: bool = True):
        """Синхронно воспроизводит короткий звуковой сигнал (wake / done)."""
        if not getattr(self.cfg, "AUDIO_CUES_ENABLED", True):
            return
        cue = self._cue_cache.get(name)
        if cue is None:
            self._init_cues()
            cue = self._cue_cache.get(name)
        if cue is None:
            return

        data, sr = cue
        self.is_speaking = True
        try:
            sd.play(data, sr, device=self.cfg.AUDIO_DEVICE)
            if wait:
                sd.wait()
        except Exception as e:
            print(f"[Voice] Ошибка воспроизведения сигнала {name}: {e}")
        finally:
            self.is_speaking = False

    async def play_cue(self, name: str = "done", wait: bool = True):
        """Асинхронно воспроизводит звуковой сигнал в отдельном потоке."""
        if not getattr(self.cfg, "AUDIO_CUES_ENABLED", True):
            return
        await asyncio.to_thread(self.play_cue_sync, name, wait)