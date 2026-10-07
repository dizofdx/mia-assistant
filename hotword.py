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
        self.threshold = getattr(self.cfg, "HOTWORD_ENERGY_THRESHOLD", 0.0035)
        self.wake_names = getattr(self.cfg, "HOTWORD_NAMES", ["мия", "миечка", "мика", "mia"])
        self.active_listening_until = 0.0
        os.makedirs("memory", exist_ok=True)

    def start(self):
        if self.running or not self.enabled:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("[WakeWord] Фоновый слушатель имени ('Мия') запущен")

    def stop(self):
        self.running = False
        # Never leave the user's master volume reduced when listening is
        # disabled or the input stream is torn down.
        if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and hasattr(self.a, "ducker"):
            try:
                self.a.ducker.unduck()
            except Exception:
                pass

    def toggle(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.start()
        else:
            self.stop()
        return self.enabled

    def _extract_command(self, text):
        """Проверяет, было ли названо имя Мии, и извлекает саму команду."""
        raw = text.lower().strip()
        cleaned = re.sub(r'[^\w\s]', ' ', raw)
        words = cleaned.split()

        # Расширенный список вариантов произношения имени "Мия" и созвучных слов от Whisper
        wake_names = getattr(self.cfg, "HOTWORD_NAMES", ["мия", "миечка", "мика", "mia"])
        extended_names = set(wake_names) | {
            "миа", "мию", "мие", "мией", "мей", "мийо", "михель", "miya", "mya", "mika",
            "меня", "мне", "миля", "миша", "нея", "нее"
        }

        # 1. Поиск совпадений по первым словам фразы
        matched_name = None
        for name in extended_names:
            if words and words[0] == name:
                matched_name = name
                break
            elif len(words) > 1 and words[1] == name and words[0] in ["эй", "хей", "ну", "привет", "ок", "слушай"]:
                matched_name = name
                break

        # 2. Поиск по корням регулярным выражением
        if not matched_name:
            m = re.search(r'^(?:эй|привет|здравствуй|слушай|ок|хей|ну)?\s*(ми[яаею]|миечк[аеиу]|мик[аеиу]|mia|miya|меня|мне)\b', cleaned)
            if m:
                matched_name = m.group(1)

        if not matched_name:
            return False, ""

        # Убираем обращение и приветствие
        pattern = r'^(?:эй|привет|здравствуй|слушай|ок|хей|ну)?\s*' + re.escape(matched_name) + r'\b[,!\s]*'
        cmd = re.sub(pattern, '', raw, flags=re.IGNORECASE).strip()
        cmd = re.sub(r'[,!\s]*\b' + re.escape(matched_name) + r'\b[,!\s]*$', '', cmd, flags=re.IGNORECASE).strip()
        cmd = re.sub(r'^[,\s!.-]+', '', cmd).strip()
        return True, cmd

    def _listen_loop(self):
        while self.running and self.enabled:
            try:
                with sd.InputStream(samplerate=self.sample_rate, channels=1,
                                    dtype='float32', blocksize=self.block_size) as stream:
                    pre_buffer = []  # кольцевой буфер 0.35 сек до начала фразы
                    max_pre = max(1, int(self.sample_rate * float(getattr(self.cfg, "HOTWORD_PRE_ROLL_MS", 350)) / 1000 / self.block_size))
                    base_threshold = getattr(self.cfg, "HOTWORD_ENERGY_THRESHOLD", 0.0035)
                    vad_enabled = bool(getattr(self.cfg, "HOTWORD_VAD_ENABLED", True))
                    vad = EnergyVAD(
                        sample_rate=self.sample_rate,
                        frame_size=self.block_size,
                        threshold=base_threshold,
                        noise_multiplier=float(getattr(self.cfg, "HOTWORD_VAD_NOISE_MULTIPLIER", 2.5)),
                        silence_multiplier=float(getattr(self.cfg, "HOTWORD_VAD_SILENCE_MULTIPLIER", 1.35)),
                        min_speech_ms=int(getattr(self.cfg, "HOTWORD_VAD_MIN_SPEECH_MS", 100)),
                        min_silence_ms=int(getattr(self.cfg, "HOTWORD_VAD_MIN_SILENCE_MS", 500)),
                    )

                    while self.running and self.enabled:
                        # A timeout must release ducking even when the user
                        # does not say another phrase after the wake-word.
                        if self.active_listening_until and time.time() >= self.active_listening_until:
                            self.active_listening_until = 0.0
                            if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and hasattr(self.a, "ducker"):
                                self.a.ducker.unduck()

                        # Если Мия сейчас сама говорит вслух — не слушаем свои динамики
                        if getattr(self.a.voice, "is_speaking", False):
                            time.sleep(0.08)
                            pre_buffer.clear()
                            vad.reset()
                            continue

                        data, _ = stream.read(self.block_size)
                        block = data.flatten()
                        rms = float(np.sqrt(np.mean(block**2)))

                        # Адаптивный energy-VAD с hangover.  RMS remains as a
                        # compatibility fallback when VAD is disabled.
                        speech_detected = vad.process(block) if vad_enabled else rms >= base_threshold

                        pre_buffer.append(block)
                        if len(pre_buffer) > max_pre:
                            pre_buffer.pop(0)

                        # Обнаружен голос человека
                        if speech_detected:
                            phrase_blocks = list(pre_buffer)
                            pre_buffer.clear()
                            silence_blocks = 0
                            max_silence = max(1, int(self.sample_rate * int(getattr(self.cfg, "HOTWORD_VAD_MIN_SILENCE_MS", 500)) / 1000 / self.block_size))
                            max_duration = max(1, int(self.sample_rate * int(getattr(self.cfg, "HOTWORD_MAX_DURATION_MS", 6000)) / 1000 / self.block_size))

                            while self.running and self.enabled:
                                if getattr(self.a.voice, "is_speaking", False):
                                    break
                                d, _ = stream.read(self.block_size)
                                b = d.flatten()
                                phrase_blocks.append(b)
                                b_rms = float(np.sqrt(np.mean(b**2)))
                                b_speech = vad.process(b) if vad_enabled else b_rms >= max(0.004, base_threshold * 0.55)

                                # Hangover prevents short pauses from cutting
                                # the final syllable of a command.
                                if not b_speech:
                                    silence_blocks += 1
                                else:
                                    silence_blocks = 0

                                if silence_blocks >= max_silence or len(phrase_blocks) >= max_duration:
                                    break

                            # Если собрано больше 0.35 сек аудио
                            total_samples = len(phrase_blocks) * self.block_size
                            if total_samples >= int(self.sample_rate * 0.35):
                                audio_arr = np.concatenate(phrase_blocks, axis=0)
                                vad.reset()

                                # Мгновенное распознавание напрямую из памяти (с авто-AGC)
                                try:
                                    text = self.a.ears.transcribe(audio_arr)
                                except Exception:
                                    text = ""

                                if text and text.strip():
                                    is_wake, cmd = self._extract_command(text)
                                    now = time.time()
                                    if now > self.active_listening_until and self.active_listening_until > 0.0:
                                        self.active_listening_until = 0.0
                                        if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and hasattr(self.a, "ducker"):
                                            self.a.ducker.unduck()

                                    if not is_wake and now < self.active_listening_until:
                                        # Режим активного слушания после того, как позвали "Мия"
                                        is_wake = True
                                        cmd = text.strip()
                                        self.active_listening_until = 0.0

                                    if not is_wake:
                                        # Проверяем, не является ли это прямой командой управления ПК
                                        try:
                                            intent = self.a.brain.check_direct_intent(text)
                                            if intent is not None:
                                                is_wake = True
                                                cmd = text.strip()
                                        except Exception:
                                            pass

                                    if is_wake:
                                        print(f"[WakeWord] Услышала имя/команду! Фраза: «{text}»")
                                        if getattr(self.cfg, "AUDIO_DUCKING_ENABLED", True) and hasattr(self.a, "ducker"):
                                            self.a.ducker.duck()

                                        if cmd:
                                            # Есть команда -> выполняем через ИИ сразу без задержек
                                            self.active_listening_until = 0.0
                                            self.a._spawn(self.a.handle_user_message(cmd, speak=True, source="voice"))
                                        else:
                                            # Просто позвали "Мия" -> звуковой сигнал и бодрый голосовой ответ
                                            async def _respond_and_arm():
                                                if not getattr(self.a, "is_muted", False):
                                                    await self.a.voice.play_cue("wake", wait=True)
                                                    await self.a.voice.speak("Да, я слушаю!")
                                                self.active_listening_until = time.time() + 8.0

                                            self.a._spawn(_respond_and_arm())
                                    else:
                                        # Разговор без имени -> игнорируем
                                        pass
            except Exception as e:
                print(f"[WakeWord] Предупреждение аудиопотока: {e}")
                time.sleep(1.0)
