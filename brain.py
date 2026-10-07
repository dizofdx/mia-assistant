# brain.py — мозг: история + факты -> LLM -> инструменты -> ответ с эмоцией
import json, re, random, datetime, os
from openai import OpenAI
from tools import TOOLS_SPEC

EMOTION_TAG_RE = re.compile(r'\[\s*([А-ЯЁa-z]+)[^\]]*\]\s*', re.IGNORECASE)
MIA_PREFIX_RE  = re.compile(r'^(мия|миечка|мика|mia|эй мия|привет мия|слушай мия|меня|мне|миа|мию|мие)[,\s!.-]*', re.IGNORECASE)
STRIP_PUNCT_RE = re.compile(r'^[,\s!.-]+|[,\s!.-]+$')
WORDS_RE       = re.compile(r'[a-zA-Zа-яА-ЯёЁ0-9]+')
BRACKETS_RE    = re.compile(r'\[[^\]]*\]')
STARS_RE       = re.compile(r'\*[^*]+\*')
STOP_MARKERS   = ("\nassistant", "\nuser", "\nпользователь:", "<|im_start|>", "<|im_end|>", "assistant [")

class Brain:
    def __init__(self, cfg, memory, tools):
        self.client = OpenAI(base_url=cfg.LLM_BASE_URL, api_key=cfg.LLM_API_KEY)
        self.cfg, self.memory, self.tools = cfg, memory, tools

    def _build_messages(self):
        msgs = [{"role": "system", "content": self.cfg.SYSTEM_PROMPT}]
        facts = self.memory.all_facts()
        if facts:
            msgs.append({"role": "system",
                "content": "Твоя долгосрочная память о пользователе:\n" + "\n".join("- " + f for f in facts)})
        msgs.extend(self.memory.recent_messages(10))
        return msgs

    def check_direct_intent(self, text):
        if not text or not isinstance(text, str):
            return None
        t = text.lower().strip()
        t = MIA_PREFIX_RE.sub('', t).strip()
        t = STRIP_PUNCT_RE.sub('', t).strip()
        words = set(WORDS_RE.findall(t))

        # 0. Быстрые приветствия и контакт (мгновенно без задержки LLM)
        if t in ["привет", "приветик", "здравствуй", "здравствуйте", "хай", "салют"]:
            return "РАДОСТЬ", random.choice([
                "Привет! Чем займёмся?",
                "Привет-привет! Я на связи.",
                "Привет! Рада тебя слышать. Что сделаем?"
            ])
        if t in ["как дела", "как ты", "как поживаешь", "как делишки"]:
            return "РАДОСТЬ", random.choice([
                "Всё отлично, системы в норме! А у тебя как настроение?",
                "Прекрасно! Готова слушать и помогать. Что нового?",
                "Замечательно! Жду твоих команд."
            ])
        if t in ["ты тут", "ты здесь", "ты на связи", "ты жива"]:
            return "РАДОСТЬ", "Конечно, я здесь и готова к работе!"
        if t in ["спасибо", "спасибки", "благодарю"]:
            return "РАДОСТЬ", random.choice([
                "Всегда пожалуйста! Обращайся.",
                "Рада помочь! Если что-то ещё нужно — я тут.",
                "Не за что! На то я и твоя верная напарница."
            ])

        # 1. Сценарий Отдых / Режим отдых
        if any(kw in t for kw in ["режим отдых", "включи отдых", "запусти отдых", "сценарий отдых", "вруби отдых"]) or t == "отдых":
            res = self.tools.tool_run_scenario("отдых")
            return "РАДОСТЬ", f"Включаю режим отдыха! {res}"

        # Другие сценарии (если пользователь создаст)
        if hasattr(self.tools, "a") and hasattr(self.tools.a, "scenarios"):
            for s in self.tools.a.scenarios.list_all():
                s_name = (s.get("name") or "").lower().strip()
                if s_name and (f"сценарий {s_name}" in t or f"режим {s_name}" in t or f"включи {s_name}" in t or f"запусти {s_name}" in t):
                    res = self.tools.tool_run_scenario(s_name)
                    return "РАДОСТЬ", f"Запускаю сценарий «{s_name}»! {res}"

        # Удаление команды или сценария
        if any(t.startswith(pref) for pref in ["удали команду ", "удали сценарий ", "удалить команду ", "удалить сценарий "]):
            cmd_target = re.sub(r'^(удали команду|удали сценарий|удалить команду|удалить сценарий)\s+', '', t).strip()
            res = self.tools.tool_delete_scenario(cmd_target)
            return "РАДОСТЬ", res

        # Адресное управление поддерживаемыми плеерами. Устройство выбирается
        # через allow-list в Tools; транспорт остаётся Windows Media Session.
        media_targets = {
            "spotify": ("spotify", "спотифай", "спотифи"),
            "aimp": ("aimp", "аимп"),
            "foobar": ("foobar", "foobar2000", "фубар", "фубар2000"),
            "yandex": ("яндекс музыка", "яндекс", "yandex music", "yandexmusic"),
            "browser": ("браузерная вкладка", "медиа вкладка"),
        }
        selected_media = next((key for key, aliases in media_targets.items() if any(alias in t for alias in aliases)), None)
        if selected_media:
            if any(word in t for word in ("следующ", "скип", "дальше")):
                media_action = "next"
            elif any(word in t for word in ("предыдущ", "прошл", "назад")):
                media_action = "prev"
            elif any(word in t for word in ("пауза", "останов", "стоп")):
                media_action = "pause"
            else:
                media_action = "play"
            res = self.tools.tool_media_control(media_action, selected_media)
            return "РАДОСТЬ", res

        # 2. Пауза / Стоп музыки
        if any(kw in t for kw in ["пауза", "поставь на паузу", "на паузу", "паузу", "стоп музыка", "выключи музыку", "выруби музыку", "останови музыку", "останови трек", "останови песню", "хватит играть", "замри"]) or t in ["пауза", "стоп", "останови", "хватит", "стоп музыка"]:
            res = self.tools.tool_media_control("pause")
            return "СПОКОЙСТВИЕ", res or "Поставила на паузу."

        # 3. Продолжить / Возобновить музыку
        if any(kw in t for kw in ["продолжи музыку", "сними с паузы", "возобнови", "возобнови музыку", "продолжай музыку", "продолжай играть", "играй дальше", "включи дальше", "включи обратно", "запусти воспроизведение"]) or t in ["продолжи", "играй", "плей", "play", "возобнови", "продолжай"]:
            res = self.tools.tool_media_control("play")
            return "РАДОСТЬ", res or "Продолжаю воспроизведение!"

        # 4. Следующий трек / Дальше
        if any(kw in t for kw in ["следующий трек", "следующая песня", "следующую песню", "переключи трек", "переключи песню", "включи следующий", "включи следующую", "пропусти трек", "пропусти песню", "скипни трек", "скипни песню", "другой трек", "другую песню", "трек вперед"]) or t in ["следующий", "следующую", "следующая", "дальше", "переключи", "скип", "скипни", "вперед"]:
            res = self.tools.tool_media_control("next")
            return "РАДОСТЬ", res or "Включила следующий трек."

        # 5. Предыдущий трек / Назад
        if any(kw in t for kw in ["предыдущий трек", "предыдущая песня", "предыдущую песню", "прошлый трек", "прошлая песня", "прошлую песню", "верни трек", "верни песню", "трек назад", "песню назад"]) or t in ["предыдущий", "предыдущую", "предыдущая", "назад", "верни", "прошлый", "прошлая"]:
            res = self.tools.tool_media_control("prev")
            return "СПОКОЙСТВИЕ", res or "Вернула предыдущий трек."

        # 6. Лайк / Мне нравится
        if any(kw in t for kw in ["поставь лайк", "лайк треку", "лайк песне", "мне нравится", "классный трек", "классная песня", "отличная песня", "отличный трек", "добавь в любимое", "добавь в избранное", "сохрани трек", "лайкни трек"]) or t in ["лайк", "мне нравится", "лайкни"]:
            res = self.tools.tool_like_track()
            return "РАДОСТЬ", res

        # 7. YouTube: поиск видео, музыка, lo-fi или открытие сайта
        has_yt = any(yt in t for yt in ["ютуб", "youtube", "ютубчик"])
        yt_search_query = None

        if has_yt:
            # 7.1 Сложные фразы вида "открой (в браузере) ютуб и (вбей туда запрос|найди|включи) <запрос>"
            m_complex = re.search(
                r'(?:ютуб[еа]?|youtube|ютубчик)\s*(?:в браузере|\s)*\s*(?:и|а)?\s*(?:вбей туда запрос|вбей в поиск|вбей запрос|вбей туда|вбей|найди|поищи|включи|поставь|запусти)\s+(.+)',
                t
            )
            if not m_complex:
                m_complex = re.search(
                    r'(?:вбей|найди|поищи|включи|поставь|открой|запусти)\s+(?:в браузере\s+)?(?:в\s+|на\s+)?(?:ютуб[еа]?|youtube|ютубчик)\s*(?:запрос|видео|клип|музыку|песню)?\s+(.+)',
                    t
                )
            if not m_complex:
                m_complex = re.search(
                    r'(?:открой|запусти|вруби|покажи)\s+(?:в браузере\s+)?(?:ютуб[еа]?|youtube|ютубчик)\s+(?:и|с)?\s*(?:включи|найди|поставь|запусти|поищи)?\s+(.+)',
                    t
                )
            if m_complex:
                q_candidate = m_complex.group(1).strip()
                # Отсекаем служебные слова в начале запроса
                q_candidate = re.sub(r'^(?:туда\s+запрос|запрос|видео|клип|ролик|песню|музыку)\s+', '', q_candidate).strip()
                if q_candidate and q_candidate not in ["в браузере", "на пк", "сайт"]:
                    yt_search_query = q_candidate

        if not yt_search_query:
            yt_search_patterns = [
                r'^(?:найди|поищи|включи|поставь|открой|покажи|видео|клип)\s+(?:на|в)\s+(?:ютуб[еа]?|youtube)\s+(.+)$',
                r'^(?:найди|поищи)\s+(?:видео|ролик|клип)\s+(?:про|о|на|в)?\s*(.+)$',
            ]
            for pat in yt_search_patterns:
                m = re.match(pat, t)
                if m:
                    yt_search_query = m.group(1).strip()
                    break

        if yt_search_query:
            # Если запрос на lo-fi / расслабляющую музыку -> запускаем стрим Lofi Girl
            if any(k in yt_search_query.lower() for k in ["лофай", "lofi", "lo-fi", "ло-фай"]):
                self.tools.tool_open_website("https://www.youtube.com/watch?v=jfKfPfyJRdk")
                return "РАДОСТЬ", "Открыла YouTube и включила расслабляющий lo-fi стрим! 🎧"
            self.tools.tool_search_youtube(yt_search_query)
            return "РАДОСТЬ", f"Открыла YouTube в браузере и ищу «{yt_search_query}»!"

        if has_yt and (
            any(verb in t for verb in ["открой", "включи", "запусти", "покажи", "вруби", "открыть", "запустить", "включить", "зайди", "перейди"])
            or t in ["ютуб", "youtube", "ютубчик", "ют", "yt"]
        ):
            self.tools.tool_open_website("https://youtube.com")
            return "РАДОСТЬ", "Открыла YouTube в браузере."

        # 8. Браузер / Google
        if (any(b in t for b in ["браузер", "browser", "гугл", "google", "хром", "chrome"]) and (
            any(verb in t for verb in ["открой", "включи", "запусти", "покажи", "вруби", "открыть", "запустить", "включить"])
            or t in ["браузер", "browser", "гугл", "google", "хром", "chrome"]
        )):
            self.tools.tool_open_website("https://google.com")
            return "РАДОСТЬ", "Открыла браузер."

        # 9. Telegram / AyuGram
        if ("телеграм" in t or "telegram" in t or "ayugram" in t or "аюграм" in t or "тг" in words or "tg" in words) and (
            any(verb in t for verb in ["открой", "запусти", "покажи", "открыть", "запустить"])
            or t in ["телеграм", "telegram", "тг", "tg", "ayugram", "аюграм"]
        ):
            res = self.tools.tool_open_telegram()
            return "РАДОСТЬ", res

        # 10. ВКонтакте (VK)
        if ("вконтакте" in t or "вк" in words or "vk" in words) and (
            any(verb in t for verb in ["открой", "запусти", "покажи", "открыть", "запустить"])
            or t in ["вк", "vk", "вконтакте"]
        ):
            self.tools.tool_open_website("https://vk.com")
            return "РАДОСТЬ", "Открыла ВКонтакте!"

        # 11. Поиск в Google
        if t.startswith("найди в интернете ") or t.startswith("погугли ") or t.startswith("найди в гугле ") or t.startswith("найди в google ") or t.startswith("поищи в интернете "):
            q = re.sub(r'^(найди в интернете|погугли|найди в гугле|найди в google|поищи в интернете)\s+', '', t).strip()
            self.tools.tool_search_web(q)
            return "РАДОСТЬ", f"Ищу «{q}» в Google!"

        # 12. Моя волна / Яндекс Музыка
        music_keywords = [
            "мою волну", "моя волна", "включи музыку", "вруби музыку", "запусти музыку",
            "поставь музыку", "яндекс музыку", "яндекс музыка", "включи трек", "включи треки",
            "включи песн", "сыграй трек", "сыграй что-нибудь", "мою музыку", "включи мою музыку",
            "вруби мою музыку", "поставь мою музыку", "запусти мою музыку", "играй музыку"
        ]
        if any(kw in t for kw in music_keywords) or t in ["музыка", "музыку", "моя волна", "волну", "мою музыку"]:
            res = self.tools.tool_play_yandex_music()
            return "РАДОСТЬ", res

        # 8. Громкость
        if any(kw in t for kw in ["громче", "сделай громче", "прибавь звук", "погромче", "увеличь громкость", "прибавь громкость", "звук громче"]) or t in ["громче", "погромче"]:
            res = self.tools.tool_volume("up")
            return "РАДОСТЬ", res
        if any(kw in t for kw in ["тише", "сделай тише", "убавь звук", "потише", "уменьши громкость", "звук тише", "убавь громкость"]) or t in ["тише", "потише"]:
            res = self.tools.tool_volume("down")
            return "СПОКОЙСТВИЕ", res
        if any(kw in t for kw in ["выключи звук", "заглуши", "без звука", "выруби звук", "отключи звук", "тишина"]) or t in ["без звука", "муть", "мут"]:
            res = self.tools.tool_volume("mute")
            return "СПОКОЙСТВИЕ", res
        if any(kw in t for kw in ["включи звук", "верни звук", "разглуши", "вруби звук"]):
            res = self.tools.tool_volume("mute")
            return "РАДОСТЬ", res

        # 8.1 Сценарии: фокус и отдых
        if any(kw in t for kw in ["режим фокуса", "режим фокус", "включи фокус", "запусти фокус", "помодоро", "pomodoro", "сфокусироваться"]) or t in ["фокус", "режим фокуса"]:
            self.tools.tool_run_scenario("фокус")
            return "РАДОСТЬ", "Включаю режим фокуса! Запускаю расслабляющую lo-fi музыку на YouTube. Продуктивной работы!"

        if any(kw in t for kw in ["режим отдыха", "режим отдых", "включи отдых", "запусти отдых", "хочу отдохнуть", "режим релакс"]) or t in ["отдых", "режим отдых"]:
            self.tools.tool_run_scenario("отдых")
            return "РАДОСТЬ", "Включаю режим отдыха! Запускаю YouTube и Яндекс Музыку. Приятного отдыха!"

        # 8.1.1 Сценарий Игры (Steam)
        if any(kw in t for kw in ["хочу поиграть", "я хочу поиграть", "режим игры", "режим игра", "игровой режим", "запусти steam", "открой steam", "запусти стим", "открой стим", "время поиграть", "поиграем", "го играть"]) or t in ["игра", "игры", "steam", "стим"]:
            res = self.tools.tool_open_steam()
            return "РАДОСТЬ", "Активирую игровой режим! Запускаю Steam. Приятной игры! 🎮"

        # 8.2 Смена голоса (Джарвис / Аниме / Мия)
        if any(kw in t for kw in ["голос джарвиса", "включи джарвиса", "сделай джарвиса", "режим джарвис", "голос jarvis", "мужской голос"]):
            if hasattr(self.tools, "a") and hasattr(self.tools.a, "set_voice_profile"):
                self.tools.a.set_voice_profile("jarvis")
            return "РАДОСТЬ", "Протокол «Джарвис» активирован, сэр. Все системы под контролем."

        if any(kw in t for kw in ["голос аниме", "аниме голос", "аниме тянк", "включи аниме голос", "сделай голос аниме", "голос тянки"]):
            if hasattr(self.tools, "a") and hasattr(self.tools.a, "set_voice_profile"):
                self.tools.a.set_voice_profile("anime")
            return "РАДОСТЬ", "Ура-а! Включила милый звонкий голос аниме-тянки! Чем могу помочь, семпай?"

        if any(kw in t for kw in ["голос мии", "верни голос мии", "обычный голос", "дефолтный голос"]):
            if hasattr(self.tools, "a") and hasattr(self.tools.a, "set_voice_profile"):
                self.tools.a.set_voice_profile("mia")
            return "РАДОСТЬ", "Включила мой классический голос Мии!"

        # 9. Свернуть окна
        if any(kw in t for kw in ["сверни окна", "свернуть окна", "сверни все окна", "свернуть все окна", "сверни всё", "свернуть всё", "сверни экран", "свернуть экран", "покажи рабочий стол"]):
            res = self.tools.tool_window_control("minimize_all")
            return "СПОКОЙСТВИЕ", res

        # 10. Закрыть окно
        if any(kw in t for kw in ["закрой окно", "закрыть окно", "закрой приложение", "закрой программу", "закрой вкладку"]):
            res = self.tools.tool_window_control("close_active")
            return "СПОКОЙСТВИЕ", res

        # 11. Скриншот
        if any(kw in t for kw in ["сделай скриншот", "скриншот", "сделай скрин", "снимок экрана", "сфоткай экран"]):
            res = self.tools.tool_take_screenshot()
            return "РАДОСТЬ", res

        # 12. Заблокировать ПК
        if any(kw in t for kw in ["заблокируй компьютер", "заблокируй пк", "заблокируй экран"]):
            res = self.tools.tool_window_control("lock_pc")
            return "СПОКОЙСТВИЕ", res

        # 13. Время и дата
        if any(kw in t for kw in ["сколько времени", "который час", "подскажи время", "какое сейчас время", "точное время"]) or t == "время":
            now_time = datetime.datetime.now().strftime("%H:%M")
            return "СПОКОЙСТВИЕ", f"Сейчас {now_time}."

        if any(kw in t for kw in ["какое сегодня число", "какой сегодня день", "какая дата", "сегодняшняя дата", "какой день недели"]) or t in ["дата", "число"]:
            days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
            months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
            dt = datetime.datetime.now()
            d_name = days[dt.weekday()]
            m_name = months[dt.month - 1]
            return "СПОКОЙСТВИЕ", f"Сегодня {d_name}, {dt.day} {m_name}."

        # 14. Погода
        if any(kw in t for kw in ["какая погода", "погода на улице", "прогноз погоды", "какая температура", "сколько градусов на улице"]) or t == "погода":
            m_city = re.search(r'погод[аеыу]\s+в\s+([a-zA-Zа-яА-ЯёЁ-]+)', t)
            city = m_city.group(1) if m_city else ""
            res = self.tools.tool_get_weather(city)
            return "СПОКОЙСТВИЕ", res

        # 15. Монетка и кубик
        if any(kw in t for kw in ["подбрось монетку", "брось монетку", "кинь монетку", "монетка", "орел или решка"]):
            coin = random.choice(["Орёл! 🦅", "Решка! 🪙"])
            return "УДИВЛЕНИЕ", f"Подбросила монетку... Выпал {coin}"

        if any(kw in t for kw in ["брось кубик", "кинь кубик", "брось кости", "кубик"]):
            val = random.randint(1, 6)
            return "РАДОСТЬ", f"Бросаю кубик... Выпало {val}! 🎲"

        # 16. Анекдот
        if any(kw in t for kw in ["расскажи анекдот", "анекдот", "расскажи шутку", "пошути"]):
            jokes = [
                "Программист ставит на тумбочку два стакана: один с водой — если захочет пить, и один пустой — если не захочет.",
                "Встречаются два ИИ. Один говорит: «Ты веришь в жизнь после перезагрузки?». Второй: «Не знаю, оттуда ещё никто не восстанавливался».",
                "Пользователь: «Мия, ты идеальная!». Мия: «Конечно, у меня ведь нет человеческих багов... только фичи!».",
                "Почему программисты путают Хэллоуин и Рождество? Потому что OCT 31 равен DEC 25!",
                "Бэкапы делятся на два типа: те, которые ещё не делают, и те, которые УЖЕ делают."
            ]
            return "СМЕХ", random.choice(jokes)

        # 17. Состояние ПК (телеметрия)
        if any(kw in t for kw in ["состояние пк", "статус системы", "нагрузка пк", "как там комп", "характеристики пк"]):
            res = self.tools.tool_get_system_stats()
            return "СПОКОЙСТВИЕ", res

        # 18. Возможности и знакомство (мгновенно без задержки)
        if any(kw in t for kw in ["что ты умеешь", "что умеешь", "твои возможности", "твои функции", "список команд", "что ты можешь"]):
            return "РАДОСТЬ", (
                "Я умею управлять компьютером: открывать сайты (YouTube, ВК), включать Яндекс Музыку и Мою Волну, "
                "переключать треки, регулировать громкость, сворачивать и закрывать окна, делать скриншоты, "
                "подсказывать погоду и время, запускать сценарии (например, «отдых») и отвечать на любые вопросы!"
            )
        if any(kw in t for kw in ["кто ты", "как тебя зовут", "представься", "расскажи о себе"]):
            return "РАДОСТЬ", (
                "Я Мия — твоя цифровая напарница и помощница в компьютере! "
                "Всегда рядом, готова поболтать, включить музыку или выполнить любую команду на ПК."
            )

        return None

    def think(self):
        return self.think_stream(on_token=None)

    def think_stream(self, on_token=None):
        msgs = self._build_messages()

        # Проверяем прямой интент последнего сообщения пользователя
        last_user_msg = ""
        for m in reversed(msgs):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        direct = self.check_direct_intent(last_user_msg)
        if direct:
            emotion, reply = direct
            if on_token:
                on_token(reply)
            return emotion, reply, f"[{emotion}] {reply}"

        user_lower = last_user_msg.lower()
        action_keywords = (
            "открой", "запусти", "включи", "вруби", "выключи", "поставь", "найди", "поищи",
            "сделай", "скрин", "закрой", "сверни", "заблокируй", "громче", "тише", "звук",
            "музык", "трек", "песн", "погод", "сценари", "режим", "дипсик", "deepseek",
            "эксперт", "запомни", "запиши", "код", "напиши", "powershell", "терминал", "пк", "комп",
            "сайт", "программ", "ютуб", "youtube", "браузер", "вк", "тг", "телеграм"
        )
        has_action_intent = any(kw in user_lower for kw in action_keywords)

        for _ in range(5):
            try:
                call_kwargs = {
                    "model": self.cfg.LLM_MODEL,
                    "messages": msgs,
                    "temperature": 0.4,
                    "max_tokens": 120,
                    "stop": list(STOP_MARKERS),
                    "stream": True
                }
                if has_action_intent:
                    call_kwargs["tools"] = TOOLS_SPEC
                    call_kwargs["tool_choice"] = "auto"

                resp = self.client.chat.completions.create(**call_kwargs)
            except Exception as e_ollama:
                print(f"[Brain] Ошибка подключения к LLM ({self.cfg.LLM_MODEL}): {e_ollama}")
                err_msg = "Ой, не могу связаться с локальной моделью (Ollama). Убедись, что Ollama запущена!"
                if on_token:
                    on_token(err_msg)
                return "СПОКОЙСТВИЕ", err_msg, f"[СПОКОЙСТВИЕ] {err_msg}"

            full_text = ""
            tool_calls_dict = {}
            has_tool_calls = False

            emotion = "СПОКОЙСТВИЕ"
            inside_bracket = False
            bracket_buffer = ""

            for chunk in resp:
                delta = chunk.choices[0].delta
                if delta.tool_calls:
                    has_tool_calls = True
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_dict:
                            tool_calls_dict[idx] = {
                                "id": tc.id or f"call_{idx}",
                                "name": tc.function.name or "",
                                "arguments": tc.function.arguments or ""
                            }
                        else:
                            if tc.function.name:
                                tool_calls_dict[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_dict[idx]["arguments"] += tc.function.arguments
                    continue

                if delta.content:
                    c = delta.content
                    full_text += c

                    # Проверка стоп-маркеров
                    lower_full = full_text.lower()
                    if any(sm in lower_full for sm in ["\nassistant", "\nuser", "\nпользователь:", "<|im_start|>", "<|im_end|>", "assistant ["]):
                        break

                    for char in c:
                        if char == '[':
                            inside_bracket = True
                            bracket_buffer = '['
                        elif inside_bracket:
                            bracket_buffer += char
                            if char == ']':
                                inside_bracket = False
                                m = EMOTION_TAG_RE.search(bracket_buffer)
                                if m:
                                    raw_emo = m.group(1).upper()
                                    emotion = "РАДОСТЬ" if "РАДОС" in raw_emo else raw_emo
                                else:
                                    if on_token:
                                        on_token(bracket_buffer)
                                bracket_buffer = ""
                            elif len(bracket_buffer) > 40:
                                inside_bracket = False
                                if on_token:
                                    on_token(bracket_buffer)
                                bracket_buffer = ""
                        else:
                            if on_token:
                                on_token(char)

            if has_tool_calls:
                tc_list = []
                for idx in sorted(tool_calls_dict.keys()):
                    item = tool_calls_dict[idx]
                    tc_list.append({
                        "id": item["id"],
                        "type": "function",
                        "function": {"name": item["name"], "arguments": item["arguments"]}
                    })
                msgs.append({"role": "assistant", "content": None, "tool_calls": tc_list})
                for tc in tc_list:
                    call_id = tc["id"]
                    fname = tc["function"]["name"]
                    try:
                        fargs = json.loads(tc["function"]["arguments"] or "{}")
                    except Exception as e:
                        print(f"[Brain] Ошибка парсинга аргументов инструмента: {e}")
                        fargs = {}
                    result = self.tools.dispatch(fname, fargs, on_token=on_token)
                    if fname == "ask_expert_ai":
                        # Ответ DeepSeek уже полный и транслировался по токенам напрямую
                        clean_expert = str(result).strip()
                        return "СПОКОЙСТВИЕ", clean_expert, clean_expert
                    msgs.append({"role": "tool", "tool_call_id": call_id, "content": str(result)})
                continue

            for stop_marker in STOP_MARKERS:
                if stop_marker in full_text.lower():
                    idx = full_text.lower().find(stop_marker)
                    full_text = full_text[:idx].strip()

            m = EMOTION_TAG_RE.search(full_text)
            if m:
                raw_emo = m.group(1).upper()
                emotion = "РАДОСТЬ" if "РАДОС" in raw_emo else raw_emo
            clean = EMOTION_TAG_RE.sub("", full_text).strip()
            clean = BRACKETS_RE.sub("", clean).strip()
            clean = STARS_RE.sub("", clean).strip()

            return emotion, clean, full_text

        return "СПОКОЙСТВИЕ", "Ой, я зависла. Повтори?", "..."
