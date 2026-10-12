"""
verify_mic_and_hotword.py
Тестирование и верификация всех улучшений микрофона, распознавания речи и хотворда:
1. Корректное извлечение команд и обращений в любом месте фразы (_extract_command).
2. Автоматическое определение микрофона (_resolve_input_device).
3. Метод прерывания речи voice.stop() (barge-in).
4. Чувствительность EnergyVAD (порог 0.0015) для естественного голоса.
5. Эндпоинты веб-панели /api/audio/devices, /api/audio/set_mic, /api/audio/test_mic.
"""

import sys, os
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = r"D:\assistant"
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from fastapi.testclient import TestClient
import config
import main
import web_panel
from audio_utils import EnergyVAD

def test_1_extract_command(asst):
    print("[1/5] Тест распознавания имени 'Мия' в начале, середине и конце фразы...")
    hl = asst.hotword

    cases = [
        ("Привет, Мия!", True, ""),
        ("Мия, открой браузер", True, "открой браузер"),
        ("Открой браузер, Мия", True, "открой браузер"),
        ("Ты тут, Мия?", True, "ты тут"),
        ("Эй Мия какая погода", True, "какая погода"),
        ("Мия", True, ""),
        ("Какая погода сегодня", False, ""),
    ]

    for phrase, expected_wake, expected_cmd in cases:
        is_wake, cmd = hl._extract_command(phrase)
        assert is_wake == expected_wake, f"Ошибка wake для '{phrase}': {is_wake} != {expected_wake}"
        if expected_cmd:
            assert expected_cmd.lower() in cmd.lower(), f"Ошибка cmd для '{phrase}': '{cmd}' != '{expected_cmd}'"
        else:
            assert cmd == "", f"Ожидалась пустая команда для '{phrase}', получено: '{cmd}'"

    print("  ✅ [УСПЕШНО] Имя 'Мия' надежно распознается в любой позиции фразы")
    return True

def test_2_resolve_input_device(asst):
    print("[2/5] Тест определения входного устройства микрофона...")
    hl = asst.hotword

    idx, name = hl._resolve_input_device()
    assert idx is not None or name == "По умолчанию"
    print(f"  Определен микрофон: [{idx}] {name}")
    print("  ✅ [УСПЕШНО] Устройство ввода микрофона определено корректно")
    return True

def test_3_voice_stop(asst):
    print("[3/5] Тест метода голосового прерывания voice.stop()...")
    v = asst.voice

    v.is_speaking = True
    v.stop()
    assert v.is_speaking == False, "is_speaking не сбросился в False"
    assert getattr(v, "_stop_requested", False) == True, "_stop_requested не установился"

    print("  ✅ [УСПЕШНО] voice.stop() мгновенно сбрасывает статус речи")
    return True

def test_4_vad_sensitivity():
    print("[4/5] Тест чувствительности EnergyVAD при пороге 0.0015...")
    vad = EnergyVAD(sample_rate=16000, frame_size=1024, threshold=0.0015, initial_noise=0.0008)

    # Тишина / шум комнаты (RMS ~ 0.0007)
    noise_frame = np.random.normal(0, 0.0007, 1024).astype(np.float32)
    for _ in range(5):
        vad.process(noise_frame)
    assert vad.active == False, "Шум комнаты не должен активировать VAD"

    # Обычный голос на комфортном расстоянии (RMS ~ 0.0022)
    voice_frame = np.random.normal(0, 0.0022, 1024).astype(np.float32)
    triggered = False
    for _ in range(5):
        if vad.process(voice_frame):
            triggered = True
            break
    assert triggered == True, "Голос с RMS 0.0022 должен уверенно активировать VAD"

    print("  ✅ [УСПЕШНО] Порог 0.0015 отсекает комнатный шум и уверенно улавливает голос")
    return True

def test_5_web_audio_endpoints(asst):
    print("[5/5] Тест API эндпоинтов управления микрофоном в веб-панели...")
    app = web_panel.create_app(asst)

    try:
        with TestClient(app) as client:
            # 5.1 GET /api/audio/devices
            res = client.get("/api/audio/devices")
            assert res.status_code == 200
            data = res.json()
            assert data.get("ok") == True
            assert "inputs" in data and len(data["inputs"]) > 0, "Список микрофонов пуст"
            assert "current_mic" in data

            # 5.2 POST /api/audio/set_mic
            target_device = data["inputs"][0]["index"]
            res_set = client.post("/api/audio/set_mic", json={"device": target_device, "threshold": 0.0015})
            assert res_set.status_code == 200
            assert res_set.json().get("ok") == True
            assert asst.cfg.HOTWORD_ENERGY_THRESHOLD == 0.0015

            # 5.3 POST /api/audio/test_mic
            res_test = client.post("/api/audio/test_mic")
            assert res_test.status_code == 200
            test_data = res_test.json()
            assert test_data.get("ok") == True
            assert "rms" in test_data and "peak" in test_data and "device_name" in test_data
            print(f"  Тест микрофона через API успешен: [{test_data.get('device_index')}] {test_data.get('device_name')} (RMS: {test_data.get('rms')})")
    finally:
        asst.hotword.stop()

    print("  ✅ [УСПЕШНО] Эндпоинты /api/audio/* работают штатно")
    return True

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  🎤 ВЕРИФИКАЦИЯ РАБОТЫ МИКРОФОНА, VAD И ГОЛОСОВОГО ВВОДА МИИ")
    print("=" * 70 + "\n")

    asst = None
    try:
        asst = main.Assistant()
        test_1_extract_command(asst)
        test_2_resolve_input_device(asst)
        test_3_voice_stop(asst)
        test_4_vad_sensitivity()
        test_5_web_audio_endpoints(asst)
    finally:
        if asst is not None and hasattr(asst, "hotword"):
            asst.hotword.stop()

    print("\n" + "=" * 70)
    print("  🎉 ВСЕ ТЕСТЫ МИКРОФОНА И ВВОДА УСПЕШНО ПРОЙДЕНЫ!")
    print("=" * 70 + "\n")
    sys.exit(0)
