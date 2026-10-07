# voice_input.py — "уши": мгновенное распознавание речи (faster-whisper на GPU CUDA / CPU)
import os, sys
import numpy as np
from audio_utils import EnergyVAD, rms_level

# 1. Добавляем пути к системным CUDA DLL (из Ollama / NVIDIA), чтобы cublas64_12.dll гарантированно находилась
cuda_dirs = [
    r"C:\Users\7ims (admin)\AppData\Local\Programs\Ollama\lib\ollama\cuda_v12",
    r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0\bin",
]
for cd in cuda_dirs:
    if os.path.exists(cd):
        try:
            os.add_dll_directory(cd)
            os.environ["PATH"] = cd + ";" + os.environ.get("PATH", "")
        except Exception:
            pass

# 2. Патч совместимости PyAV 19+ для faster-whisper
try:
    import av
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception:
    pass

import ctranslate2
from faster_whisper import WhisperModel

class Ears:
    def __init__(self, cfg):
        self.cfg = cfg
        self.model_name = getattr(cfg, "WHISPER_MODEL", "small")
        self.vad_enabled = bool(getattr(cfg, "WHISPER_VAD_ENABLED", True))
        self.vad = EnergyVAD(
            sample_rate=int(getattr(cfg, "WHISPER_SAMPLE_RATE", 16000)),
            frame_size=int(getattr(cfg, "WHISPER_VAD_FRAME_SIZE", 512)),
            threshold=float(getattr(cfg, "WHISPER_VAD_THRESHOLD", 0.004)),
            noise_multiplier=float(getattr(cfg, "WHISPER_VAD_NOISE_MULTIPLIER", 2.2)),
            silence_multiplier=float(getattr(cfg, "WHISPER_VAD_SILENCE_MULTIPLIER", 1.3)),
            min_speech_ms=int(getattr(cfg, "WHISPER_VAD_MIN_SPEECH_MS", 80)),
            min_silence_ms=int(getattr(cfg, "WHISPER_VAD_MIN_SILENCE_MS", 280)),
        )
        self._cpu_model = None
        has_cuda = ctranslate2.get_cuda_device_count() > 0
        device = "cuda" if has_cuda else "cpu"
        compute_type = "float16" if has_cuda else "int8"

        try:
            try:
                print(f"[Whisper] Loading model ({self.model_name}) on {'GPU (CUDA)' if has_cuda else 'CPU'} [{compute_type}]...")
            except Exception:
                pass
            self.model = WhisperModel(self.model_name, device=device, compute_type=compute_type)
            try:
                print(f"[Whisper] Speech recognition ready on {'GPU (CUDA)' if has_cuda else 'CPU'}!")
            except Exception:
                pass
        except Exception as e:
            try:
                print(f"[Whisper] Failed on {device}: {e}, falling back to CPU...")
            except Exception:
                pass
            self.model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            try:
                print("[Whisper] Speech recognition ready on CPU [int8]!")
            except Exception:
                pass

    def _prepare_audio(self, audio_or_path):
        """Prepare a captured NumPy buffer without amplifying room noise."""
        if not isinstance(audio_or_path, np.ndarray):
            return audio_or_path
        audio = np.asarray(audio_or_path, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            return audio

        # Remove the microphone's DC offset before energy/VAD calculations.
        audio = audio - np.float32(np.mean(audio))
        if self.vad_enabled:
            trimmed = self.vad.trim(
                audio,
                pad_ms=int(getattr(self.cfg, "WHISPER_VAD_PADDING_MS", 100)),
                min_ms=int(getattr(self.cfg, "WHISPER_VAD_MIN_AUDIO_MS", 180)),
            )
            # Keep the original recording when a very quiet microphone leaves
            # the VAD uncertain; Whisper's neural VAD can still recover it.
            if trimmed.size:
                audio = trimmed

        # RMS based AGC is gentler than peak normalization: a single click or
        # a music transient no longer turns the whole recording into noise.
        level = rms_level(audio)
        target = float(getattr(self.cfg, "WHISPER_AGC_TARGET_RMS", 0.085))
        max_gain = float(getattr(self.cfg, "WHISPER_AGC_MAX_GAIN", 3.0))
        if level > 0.0005 and target > 0:
            gain = min(max_gain, target / level)
            audio = audio * np.float32(gain)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak > 0.95:
            audio = audio * np.float32(0.95 / peak)
        return np.ascontiguousarray(audio, dtype=np.float32)

    def _transcribe_model(self, model, audio):
        kwargs = {
            "language": getattr(self.cfg, "WHISPER_LANGUAGE", "ru"),
            "beam_size": int(getattr(self.cfg, "WHISPER_BEAM_SIZE", 1)),
            "vad_filter": self.vad_enabled,
            "no_speech_threshold": float(getattr(self.cfg, "WHISPER_NO_SPEECH_THRESHOLD", 0.6)),
        }
        if self.vad_enabled:
            kwargs["vad_parameters"] = {
                "min_silence_duration_ms": int(getattr(self.cfg, "WHISPER_VAD_MIN_SILENCE_MS", 280)),
                "speech_pad_ms": int(getattr(self.cfg, "WHISPER_VAD_PADDING_MS", 100)),
            }
        try:
            return model.transcribe(audio, **kwargs)
        except TypeError:
            # Older faster-whisper builds may not accept newer VAD kwargs.
            kwargs.pop("vad_parameters", None)
            kwargs.pop("no_speech_threshold", None)
            return model.transcribe(audio, **kwargs)

    def transcribe(self, audio_or_path):
        """Распознаёт аудио из пути к файлу или напрямую из NumPy массива (в памяти без диска)."""
        prepared = self._prepare_audio(audio_or_path)
        try:
            segments, _ = self._transcribe_model(self.model, prepared)
            return " ".join(s.text for s in segments).strip()
        except Exception as e:
            try:
                print(f"[Ears] Ошибка распознавания речи: {e}. Пробую резервный CPU движок...")
            except Exception:
                pass
            try:
                if self._cpu_model is None:
                    self._cpu_model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                segments, _ = self._transcribe_model(self._cpu_model, prepared)
                return " ".join(s.text for s in segments).strip()
            except Exception as e_cpu:
                try:
                    print(f"[Ears] Ошибка CPU распознавания: {e_cpu}")
                except Exception:
                    pass
                return ""
