# hotword.py — фоновый слушатель микрофона по ключевому слову ("Мия")
import threading, time, os, re, asyncio
import numpy as np
import sounddevice as sd
from audio_utils import EnergyVAD

class HotwordListener:
    def __init__(self, assistant):
        self.a = assistant
        self.cfg = assistant.cfg
        self.enabled = getattr(self.cfg, "HOTWORD_ENABLED", True)
        self.running = False
        self.thread = None
        self.sample_rate = 16000
        self.block_size = 1024
        self.threshold = float(getattr(self.cfg, "HOTWORD_ENERGY_THRESHOLD", 0.0015))
        self.wake_names = getattr(self.cfg, "HOTWORD_NAMES", ["мия", "миечка", "мика", "mia"])
        self.active_listening_until = 0.0
        self.mic_device = None
        self.mic_device_name = "По умолчанию"
        self._active_stream = None
        os.makedirs("memory", exist_ok=True)

    @staticmethod
    def _find_supported_samplerate(device_idx):
        """Проверяет поддерживаемые частоты дискретизации для устройства."""
        candidates = [16000, 48000, 44100, 32000, 22050, 8000]
        for rate in candidates:
            try:
                sd.check_input_settings(device=device_idx, samplerate=rate, channels=1)
                return rate
            except Exception:
                pass
        try:
            dev = sd.query_devices(device_idx)
            return int(dev.get("default_samplerate", 16000))
        except Exception:
            return 16000

    @staticmethod
    def _resample(samples: np.ndarray, in_rate: int, out_rate: int = 16000) -> np.ndarray:
        """Ресэмплирует одномерный аудиомассив до 16 кГц без внешних зависимостей."""
        if in_rate == out_rate or len(samples) == 0:
            return samples
        target_len = int(len(samples) * out_rate / in_rate)
        return np.interp(
            np.linspace(0, len(samples), target_len, endpoint=False),
            np.arange(len(samples)),
            samples
        ).astype(np.float32)

    def _resolve_input_device(self):
        """Определяет корректный индекс входного устройства микрофона."""
        target = getattr(self.cfg, "MIC_DEVICE", None)
        try:
            devices = sd.query_devices()
        except Exception:
            return None, "По умолчанию"

        if target is not None:
            # 1. Если указан точный числовой индекс
            if isinstance(target, int) and 0 <= target < len(devices):
                dev = devices[target]
                if dev.get("max_input_channels", 0) > 0:
                    return target, dev.get("name", f"Устройство {target}")
            # 2. Если указана строка (имя или часть имени)
            target_str = str(target).lower().strip()
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    try:
                        hostapi = sd.query_hostapis(dev.get("hostapi", 0))["name"]
                    except Exception:
                        hostapi = ""
                    if hostapi != "Windows WDM-KS" and target_str in dev.get("name", "").lower():
                        return idx, dev.get("name", f"Устройство {idx}")
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and target_str in dev.get("name", "").lower():
                    return idx, dev.get("name", f"Устройство {idx}")

        # По умолчанию берем системный дефолт из sounddevice
        try:
            def_dev = sd.default.device[0]
            if def_dev is not None and def_dev >= 0 and def_dev < len(devices):
                dev = devices[def_dev]
                if dev.get("max_input_channels", 0) > 0:
                    return def_dev, dev.get("name", f"Устройство {def_dev}")
        except Exception:
            pass

        # Первое подходящее устройство
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                try:
                    hostapi = sd.query_hostapis(dev.get("hostapi", 0))["name"]
                except Exception:
                    hostapi = ""
                if hostapi != "Windows WDM-KS":
                    return idx, dev.get("name", f"Устройство {idx}")
        return None, "Не обнаружено"

    def start(self):
        if self.running or not self.enabled:
            return
        self.running = True
        self.threshold = float(getattr(self.cfg, "HOTWORD_ENERGY_THRESHOLD", 0.0015))
        self.mic_device, self.mic_device_name = self._resolve_input_device()
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        dev_label = f"[{self.mic_device}] {self.mic_device_name}" if self.mic_device is not None else self.mic_device_name
        print(f"[WakeWord] 🎤 Фоновый слушатель запущен | Микрофон: {dev_label} | Порог VAD: {self.threshold}")

    def stop(self):
        self.running = False
        if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and hasattr(self.a, "ducker"):
            try:
                self.a.ducker.unduck()
            except Exception:
                pass
        if self._active_stream:
            try:
                self._active_stream.abort()
            except Exception:
                pass
        if self.thread and self.thread.is_alive() and threading.current_thread() != self.thread:
            try:
                self.thread.join(timeout=1.5)
            except Exception:
                pass
            self.thread = None

    def restart(self):
        """Перезапускает слушатель с актуальными настройками устройства и порога."""
        self.stop()
        time.sleep(0.1)
        self.start()

    def toggle(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.start()
        else:
            self.stop()
        return self.enabled

    def _extract_command(self, text):
        """Проверяет, было ли названо имя Мии, и извлекает саму команду."""
        if not text:
            return False, ""
        raw = text.strip()
        low = raw.lower()
        cleaned = re.sub(r'[^\w\s]', ' ', low)
        words = cleaned.split()

        wake_names = getattr(self.cfg, "HOTWORD_NAMES", ["мия", "миечка", "мика", "mia"])
        extended_names = set(w.lower() for w in wake_names) | {
            "мия", "миечка", "мика", "mia", "миа", "мию", "мие", "мией", "мей", "мийо",
            "михель", "miya", "mya", "mika", "миля", "мий", "миё", "миенька"
        }

        wake_regex = re.compile(
            r'\b(ми[яаеюё]|мией|миечк[аеиу]|мик[аеиу]|миеньк[аеиу]|мий|mia|miya|mika)\b',
            re.IGNORECASE
        )
        greeting_prefix_regex = re.compile(
            r'^(?:эй|хей|привет|здравствуй|здравствуйте|слушай|послушай|ок|ну|скажи)\b[,!\s]*',
            re.IGNORECASE
        )

        matched_name = None
        m = wake_regex.search(low)
        if m:
            matched_name = m.group(1)
        else:
            for w in words:
                if w in extended_names:
                    matched_name = w
                    break

        if not matched_name:
            if words and words[0] in {"меня", "мне"} and len(words) > 1:
                matched_name = words[0]

        if not matched_name:
            return False, ""

        # Убираем имя и лишние приветственные префиксы
        cmd = re.sub(r'[,!\s]*\b' + re.escape(matched_name) + r'\b[,!?.\s]*', ' ', raw, flags=re.IGNORECASE).strip()
        cmd = greeting_prefix_regex.sub('', cmd).strip()
        cmd = re.sub(r'^[,\s!.-]+|[,\s!.-]+$', '', cmd).strip()
        # Если ничего содержательного не осталось, считаем вызовом без команды
        if not re.search(r'[a-zA-Zа-яА-ЯёЁ0-9]', cmd):
            cmd = ""
        return True, cmd

    def _listen_loop(self):
        was_speaking = False
        echo_drain_blocks = 0
        no_device_logged = False
        while self.running and self.enabled:
            try:
                self.mic_device, self.mic_device_name = self._resolve_input_device()
                if self.mic_device is None:
                    def_in = -1
                    try:
                        def_in = sd.default.device[0]
                    except Exception:
                        pass
                    if def_in is None or def_in < 0:
                        if not no_device_logged:
                            print("[WakeWord] ⚠️ Микрофон не обнаружен в системе (устройство ввода отсутствует или выключено). Ожидание подключения...")
                            no_device_logged = True
                        try:
                            sd._terminate()
                            sd._initialize()
                        except Exception:
                            pass
                        time.sleep(3.0)
                        continue

                if no_device_logged:
                    print(f"[WakeWord] 🎤 Микрофон обнаружен и активирован: [{self.mic_device}] {self.mic_device_name}")
                    no_device_logged = False

                stream_rate = self._find_supported_samplerate(self.mic_device)
                base_threshold = float(getattr(self.cfg, "HOTWORD_ENERGY_THRESHOLD", 0.0015))
                min_silence_ms = int(getattr(self.cfg, "HOTWORD_VAD_MIN_SILENCE_MS", 900))
                max_duration_ms = int(getattr(self.cfg, "HOTWORD_MAX_DURATION_MS", 8000))
                pre_roll_ms = float(getattr(self.cfg, "HOTWORD_PRE_ROLL_MS", 350))
                vad_enabled = bool(getattr(self.cfg, "HOTWORD_VAD_ENABLED", True))

                read_block_size = int(self.block_size * stream_rate / self.sample_rate)

                with sd.InputStream(device=self.mic_device, samplerate=stream_rate, channels=1,
                                    dtype='float32', blocksize=read_block_size) as stream:
                    self._active_stream = stream
                    pre_buffer = []
                    max_pre = max(1, int(self.sample_rate * pre_roll_ms / 1000 / self.block_size))
                    vad = EnergyVAD(
                        sample_rate=self.sample_rate,
                        frame_size=self.block_size,
                        threshold=base_threshold,
                        noise_multiplier=float(getattr(self.cfg, "HOTWORD_VAD_NOISE_MULTIPLIER", 1.8)),
                        silence_multiplier=float(getattr(self.cfg, "HOTWORD_VAD_SILENCE_MULTIPLIER", 1.35)),
                        min_speech_ms=int(getattr(self.cfg, "HOTWORD_VAD_MIN_SPEECH_MS", 100)),
                        min_silence_ms=min_silence_ms,
                    )

                    while self.running and self.enabled:
                        if self.active_listening_until and time.time() >= self.active_listening_until:
                            self.active_listening_until = 0.0
                            if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and hasattr(self.a, "ducker"):
                                self.a.ducker.unduck()

                        # Когда Мия говорит:
                        is_speaking_now = getattr(self.a.voice, "is_speaking", False)
                        if is_speaking_now:
                            was_speaking = True
                            data, _ = stream.read(read_block_size)
                            raw_block = data.flatten()
                            block = self._resample(raw_block, stream_rate, self.sample_rate) if stream_rate != self.sample_rate else raw_block
                            rms = float(np.sqrt(np.mean(block**2)))

                            # Поддержка barge-in: только при громком голосе поверх звука колонок
                            # и строго по стоп-словам (без "мия", чтобы не прерывать речь ложно)
                            barge_threshold = max(0.012, base_threshold * 4.0)
                            if rms >= barge_threshold:
                                barge_blocks = [block]
                                for _ in range(int(self.sample_rate * 1.2 / self.block_size)):
                                    d, _ = stream.read(read_block_size)
                                    rb = d.flatten()
                                    barge_blocks.append(self._resample(rb, stream_rate, self.sample_rate) if stream_rate != self.sample_rate else rb)
                                barge_audio = np.concatenate(barge_blocks)
                                try:
                                    barge_text = self.a.ears.transcribe(barge_audio).lower()
                                except Exception:
                                    barge_text = ""
                                if any(kw in barge_text for kw in ["стоп", "хватит", "замолчи", "тихо", "молчи", "отмена", "стой"]):
                                    print(f"[WakeWord] 🛑 Речь ассистента прервана голосовой командой: «{barge_text}»")
                                    self.a.voice.stop()
                                    was_speaking = False
                                    echo_drain_blocks = 3
                            pre_buffer.clear()
                            vad.reset()
                            continue

                        # Если речь только что завершилась: дренируем акустическое эхо комнаты (~380 мс)
                        if was_speaking:
                            was_speaking = False
                            echo_drain_blocks = max(echo_drain_blocks, 6)

                        if echo_drain_blocks > 0:
                            stream.read(read_block_size)
                            echo_drain_blocks -= 1
                            pre_buffer.clear()
                            vad.reset()
                            continue

                        data, _ = stream.read(read_block_size)
                        raw_block = data.flatten()
                        block = self._resample(raw_block, stream_rate, self.sample_rate) if stream_rate != self.sample_rate else raw_block
                        rms = float(np.sqrt(np.mean(block**2)))

                        speech_detected = vad.process(block) if vad_enabled else rms >= base_threshold

                        pre_buffer.append(block)
                        if len(pre_buffer) > max_pre:
                            pre_buffer.pop(0)

                        if speech_detected:
                            phrase_blocks = list(pre_buffer)
                            pre_buffer.clear()
                            silence_blocks = 0
                            max_silence = max(1, int(self.sample_rate * min_silence_ms / 1000 / self.block_size))
                            max_duration = max(1, int(self.sample_rate * max_duration_ms / 1000 / self.block_size))

                            while self.running and self.enabled:
                                if getattr(self.a.voice, "is_speaking", False):
                                    break
                                d, _ = stream.read(read_block_size)
                                raw_d = d.flatten()
                                b = self._resample(raw_d, stream_rate, self.sample_rate) if stream_rate != self.sample_rate else raw_d
                                phrase_blocks.append(b)
                                b_rms = float(np.sqrt(np.mean(b**2)))
                                b_speech = vad.process(b) if vad_enabled else b_rms >= max(0.0008, base_threshold * 0.5)

                                if not b_speech:
                                    silence_blocks += 1
                                else:
                                    silence_blocks = 0

                                if silence_blocks >= max_silence or len(phrase_blocks) >= max_duration:
                                    break

                            total_samples = len(phrase_blocks) * self.block_size
                            if total_samples >= int(self.sample_rate * 0.35):
                                audio_arr = np.concatenate(phrase_blocks, axis=0)
                                vad.reset()

                                try:
                                    text = self.a.ears.transcribe(audio_arr)
                                except Exception:
                                    text = ""

                                if text and text.strip():
                                    raw_text = text.strip()
                                    is_wake, cmd = self._extract_command(raw_text)
                                    now = time.time()

                                    # Режим активного диалога после обращения к Мие
                                    if not is_wake and now < self.active_listening_until:
                                        words_check = re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9]+', raw_text.lower())
                                        if len(words_check) == 1 and len(words_check[0]) == 1 and words_check[0] not in ("я", "да"):
                                            continue
                                        is_wake = True
                                        cmd = raw_text
                                        self.active_listening_until = 0.0

                                    if not is_wake:
                                        try:
                                            intent = self.a.brain.check_direct_intent(raw_text)
                                            if intent is not None:
                                                is_wake = True
                                                cmd = raw_text
                                        except Exception:
                                            pass

                                    if is_wake:
                                        print(f"[WakeWord] 🎯 Услышала речь! Фраза: «{raw_text}»")
                                        if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and hasattr(self.a, "ducker"):
                                            self.a.ducker.duck()

                                        if cmd:
                                            self.active_listening_until = 0.0
                                            self.a._spawn(self.a.handle_user_message(cmd, speak=True, source="voice"))
                                        else:
                                            async def _respond_and_arm():
                                                if not getattr(self.a, "is_muted", False):
                                                    await self.a.voice.play_cue("wake", wait=True)
                                                    await self.a.voice.speak("Да, я слушаю!")
                                                self.active_listening_until = time.time() + 10.0

                                            self.a._spawn(_respond_and_arm())
            except Exception as e:
                err_msg = str(e)
                if not no_device_logged:
                    print(f"[WakeWord] ⚠️ Ошибка аудиопотока ({err_msg}), пробую переподключиться...")
                try:
                    sd._terminate()
                    sd._initialize()
                except Exception:
                    pass
                time.sleep(2.0)
            finally:
                self._active_stream = None
