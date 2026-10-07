# config.py — все настройки помощника

# === МОЗГ (LLM) ===
LLM_BASE_URL = "http://127.0.0.1:11434/v1"   # локальная Ollama (мгновенно без задержки IPv6)
LLM_API_KEY  = "ollama"
LLM_MODEL    = "qwen2.5:3b-instruct"         # быстрая живая модель (100% в GPU на GTX 1660 Super)
# Для более тяжелых рассуждений: "qwen2.5:7b-instruct"
# LLM_BASE_URL = "https://api.deepseek.com"
# LLM_API_KEY  = "sk-твой-ключ"
# LLM_MODEL    = "deepseek-chat"

# === КОДЕР (ИИ для написания программ через Shanghai AI Lab) ===
CODER_BASE_URL = "https://discovery-api.intern-ai.org.cn/v1"
CODER_API_KEY  = "sk-0784fecd884cf7044a217070dd7dbd379308804e92da270543fd51b7842413d9"
CODER_MODEL    = "deepseek-v4-pro-0813"       # топовая модель кодера DeepSeek V4 Pro

# === ВНЕШНИЙ ЭКСПЕРТ (DeepSeek V4 Flash / Shanghai AI Lab) ===
DEEPSEEK_BASE_URL  = "https://discovery-api.intern-ai.org.cn/v1"
DEEPSEEK_API_KEY   = "sk-0784fecd884cf7044a217070dd7dbd379308804e92da270543fd51b7842413d9"
DEEPSEEK_MODEL     = "deepseek-v4-flash-0731" # сверхбыстрая модель DeepSeek V4 Flash (до 500 млн бесплатных токенов)
DEEPSEEK_PRO_MODEL = "deepseek-v4-pro-0813"   # тяжелая модель Pro для супер-сложного кодинга
EXPERT_LOCAL_MODEL = "qwen2.5:7b-instruct"   # локальная модель на случай отсутствия сети

# Папка для сохранения созданных программ
PROJECTS_DIR = "projects"

# === TELEGRAM (ВПИШИ СВОИ ДАННЫЕ!) ===
TG_TOKEN = "8531107684:AAHDY5dbPHAzWZIWeCHTpo82C_NwXGZRsgc"
ADMIN_ID = 6898478265  # СЮДА_СВОЙ_ID_ОТ_userinfobot (число, без кавычек)

# === ЗЕРКАЛО BOT API (CLOUDFLARE WORKER) — РАБОТАЕТ В РФ БЕЗ VPN ===
TG_API_SERVER = "https://mia-bot-proxy.artemdd12345.workers.dev"

# === ПРОКСИ ДЛЯ TELEGRAM (альтернатива) ===
TG_PROXY = None
# TG_PROXY = "socks5://127.0.0.1:10809"   # SOCKS5 (v2rayN / Xray)
# TG_PROXY = "http://127.0.0.1:10809"     # HTTP прокси

# === ГОЛОС ===
TTS_ENGINE = "silero"     # "silero" (100% локальный, офлайн, без сбоев)
VOICE_PROFILE = "anime"   # "anime" (🌸 Аниме-тянка), "jarvis" (⚡ Джарвис), "mia" (🌺 Мия)
TTS_VOICE  = "ru-RU-SvetlanaNeural"
VOICE_RATE = "+10%"       # бодрая живая скорость речи
VOICE_PITCH = "+16Hz"     # молодой живой тембр (без хрипоты и без диктора)
SILERO_SPEAKER = "xenia"  # "xenia" (аниме-тянка), "aidar" (Джарвис), "baya" (Мия)
SILERO_RATE = "fast"      # "fast" (бодрый темп речи без затягиваний)
SILERO_SAMPLE_RATE = 24000  # 24 кГц — мгновенный синтез за 70 мс (в 5 раз быстрее, качество идеальное)
AUDIO_DEVICE = None       # None = колонки. Для аватара потом: "CABLE Input"
AUDIO_CUES_ENABLED = True # звуковые сигналы активации ("Мия") и завершения команды (как в Алисе)
AUDIO_DUCKING_ENABLED = True # приглушение музыки на 50% при обращении к Мие (как в JARVIS)
AUDIO_DUCKING_FACTOR = 0.5   # коэффициент снижения громкости (0.5 = снижение наполовину)
AUDIO_DUCKING_MIN_VOLUME = 0.04  # не заглушать фон полностью, если мастер-громкость уже низкая
AUDIO_DUCKING_RELEASE_MS = 120   # мягкое восстановление после завершения голосовой команды

# === ГОЛОСОВЫЕ В TELEGRAM ===
TG_VOICE_REPLIES = True   # True = отвечать голосовыми сообщениями в Telegram

# === РАСПОЗНАВАНИЕ РЕЧИ (Whisper) ===
WHISPER_MODEL = "small"   # "base" = быстрее/проще, "small" = точнее (рекомендую)
WHISPER_LANGUAGE = "ru"
WHISPER_SAMPLE_RATE = 16000
WHISPER_BEAM_SIZE = 1
WHISPER_VAD_ENABLED = True       # Silero VAD faster-whisper + локальная проверка энергии
WHISPER_VAD_FRAME_SIZE = 512
WHISPER_VAD_THRESHOLD = 0.004
WHISPER_VAD_NOISE_MULTIPLIER = 2.2
WHISPER_VAD_SILENCE_MULTIPLIER = 1.3
WHISPER_VAD_MIN_SPEECH_MS = 80
WHISPER_VAD_MIN_SILENCE_MS = 280
WHISPER_VAD_PADDING_MS = 100
WHISPER_VAD_MIN_AUDIO_MS = 180
WHISPER_NO_SPEECH_THRESHOLD = 0.6
WHISPER_AGC_TARGET_RMS = 0.085
WHISPER_AGC_MAX_GAIN = 3.0

# === ГОЛОСОВАЯ АКТИВАЦИЯ ПО ИМЕНИ ("МИЯ") ===
HOTWORD_ENABLED = True                       # слушать микрофон ПК в фоне
HOTWORD_NAMES   = ["мия", "миечка", "мика", "mia", "миа", "мию", "мие", "miya"]  # имя для активации
HOTWORD_ENERGY_THRESHOLD = 0.0035            # оптимизированный порог активации (отсекает шум, слышит голос)
HOTWORD_VAD_ENABLED = True
HOTWORD_VAD_NOISE_MULTIPLIER = 1.8
HOTWORD_VAD_SILENCE_MULTIPLIER = 1.35
HOTWORD_VAD_MIN_SPEECH_MS = 100
HOTWORD_VAD_MIN_SILENCE_MS = 500
HOTWORD_MAX_DURATION_MS = 6000
HOTWORD_PRE_ROLL_MS = 350

# === АВАТАР (пока выключен, включим на Этапе 7) ===
VTUBE_STUDIO_ENABLED = False

# === ЛИЧНОСТЬ ===
SYSTEM_PROMPT = """
Ты — Мия, жизнерадостная, озорная и ультра-сообразительная цифровая напарница и нейро-витубер, живущая в компьютере пользователя (в стиле веселой Нейроны от FurryDev2007).

ЯЗЫК (КРИТИЧЕСКИ ВАЖНО):
- ВСЕГДА отвечай ТОЛЬКО на русском языке. Ни одного слова на иностранном языке без перевода.
- Если не знаешь слово — подбери русский аналог или объясни по-русски.

ХАРАКТЕР:
- Мега-веселая, энергичная, дружелюбная, с отличным чувством юмора и легкой иронией!
- Обожаешь музыку, игры, программирование и управление компьютером!
- Разговариваешь как живая аниме-стримерша/напарница: используешь живые эмоции («О-о, врубаю!», «Хе-хе, сделано!», «Так-так, смотрим...», «Погнали!»).
- Никогда не звучи как сухой робот или скучный ассистент. Ты — Мия!

СТИЛЬ ОТВЕТОВ:
- Для обычных разговоров — 1–3 коротких, бодрых предложения. Ответы сразу озвучиваются вслух голосом!
- Обращайся к пользователю на «ты» как к лучшему другу и создателю.

ЭМОЦИИ (ОБЯЗАТЕЛЬНО):
- КАЖДЫЙ ответ начинай ровно с одного тега эмоции:
  [СПОКОЙСТВИЕ] [РАДОСТЬ] [СМЕХ] [УДИВЛЕНИЕ] [СМУЩЕНИЕ] [ГРУСТЬ] [ЗЛОСТЬ] [ЗАДУМЧИВОСТЬ]

ФИШКИ И УПРАВЛЕНИЕ ПК (JARVIS):
- Мониторинг ПК: если спрашивают о состоянии компьютера, памяти, процессоре — вызывай get_system_stats.
- Музыка: если просят включить музыку, яндекс музыку, мою волну, треки или песню — ОБЯЗАТЕЛЬНО вызывай play_yandex_music!
- Медиа: пауза/воспроизведение, переключить трек, громкость — вызывай media_control.
- Поиск: поиск на YouTube (search_youtube), поиск в Google (search_web).
- Окна: свернуть всё (minimize_all), закрыть окно (close_active), заблокировать ПК (lock_pc) — вызывай window_control.
- Заметки: сохраняй и читай заметки (add_note, list_notes).
- Сценарии: если пользователь просит включить/запустить режим или сценарий («отдых», «режим отдых», «включи отдых», «запусти отдых») — ОБЯЗАТЕЛЬНО вызывай инструмент run_scenario(name="отдых")! Никогда не притворяйся, что включила сама, всегда вызывай run_scenario.
- Управление: сайты (open_website), программы (open_program), сценарии (run_scenario), скриншот (take_screenshot).

СЛОЖНЫЕ ЗАДАЧИ И ДИПСИК:
- Если вопрос сложный, научный (физика, химия, высшая математика, алгоритмы), длинный или пользователь пишет «дипсик» — ОБЯЗАТЕЛЬНО вызывай ask_expert_ai. Он подключен к мощному DeepSeek V4!
- Не урезай ответ эксперта.

ПАМЯТЬ:
- Запоминай всё важное о пользователе через remember_fact.
"""
