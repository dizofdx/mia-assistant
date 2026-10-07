"""Small, dependency-light audio helpers shared by the microphone pipeline.

The application intentionally keeps a local energy VAD as a fallback.  It does
not require a second neural model and therefore keeps wake-word detection fast
on machines where Whisper is running on CPU.  It is also useful as a first
pass before Whisper's own VAD filter because it removes long music/silence
tails from the in-memory recording.
"""

from __future__ import annotations

import math
from typing import Iterable, Optional

import numpy as np


def rms_level(samples: np.ndarray) -> float:
    """Return a finite RMS value for a mono float audio frame."""
    arr = np.asarray(samples, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return 0.0
    value = float(np.sqrt(np.mean(np.square(arr), dtype=np.float64)))
    return value if math.isfinite(value) else 0.0


class EnergyVAD:
    """Adaptive energy VAD with a short hangover to preserve words.

    ``threshold`` is an absolute floor (microphone dependent), while
    ``noise_multiplier`` follows the room noise floor.  ``process`` returns a
    boolean for each frame and keeps a small state, making it suitable for a
    streaming ``sounddevice`` callback or a blocking input stream.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_size: int = 1024,
        threshold: float = 0.009,
        noise_multiplier: float = 2.5,
        silence_multiplier: float = 1.35,
        min_speech_ms: int = 120,
        min_silence_ms: int = 480,
        initial_noise: float = 0.0025,
    ) -> None:
        self.sample_rate = max(1, int(sample_rate))
        self.frame_size = max(1, int(frame_size))
        self.threshold = max(0.00001, float(threshold))
        self.noise_multiplier = max(1.05, float(noise_multiplier))
        self.silence_multiplier = max(1.01, float(silence_multiplier))
        self.min_speech_frames = max(1, math.ceil(self.sample_rate * max(1, min_speech_ms) / 1000 / self.frame_size))
        self.min_silence_frames = max(1, math.ceil(self.sample_rate * max(1, min_silence_ms) / 1000 / self.frame_size))
        self.noise_floor = max(1e-6, float(initial_noise))
        self._speech_frames = 0
        self._silence_frames = 0
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def reset(self, noise_floor: Optional[float] = None) -> None:
        if noise_floor is not None:
            self.noise_floor = max(1e-6, float(noise_floor))
        self._speech_frames = 0
        self._silence_frames = 0
        self._active = False

    def process(self, frame: np.ndarray, *, update_noise: bool = True) -> bool:
        level = rms_level(frame)
        # Update only below the speech gate.  This avoids learning a loud
        # speaker/music burst as the new baseline.
        gate = max(self.threshold, self.noise_floor * self.noise_multiplier)
        if update_noise and level < max(self.threshold * 0.8, self.noise_floor * self.noise_multiplier):
            self.noise_floor = self.noise_floor * 0.96 + level * 0.04

        speech_gate = max(self.threshold, self.noise_floor * self.noise_multiplier)
        silence_gate = max(self.threshold * 0.42, self.noise_floor * self.silence_multiplier)
        candidate = level >= speech_gate

        if candidate:
            self._speech_frames += 1
            self._silence_frames = 0
            if self._speech_frames >= self.min_speech_frames:
                self._active = True
        elif self._active:
            # Hangover keeps trailing consonants and short pauses in a phrase.
            if level <= silence_gate:
                self._silence_frames += 1
            else:
                self._silence_frames = 0
            if self._silence_frames >= self.min_silence_frames:
                self._active = False
                self._speech_frames = 0
                self._silence_frames = 0
        else:
            self._speech_frames = 0
        return self._active or candidate

    def trim(self, samples: np.ndarray, *, pad_ms: int = 100, min_ms: int = 0) -> np.ndarray:
        """Trim non-voiced head/tail while retaining a little context.

        When no voiced frame is found, the original array is returned.  This
        conservative behaviour lets Whisper decide in ambiguous/noisy cases.
        """
        arr = np.asarray(samples, dtype=np.float32).reshape(-1)
        if arr.size == 0:
            return arr
        frame = self.frame_size
        voiced = []
        probe = EnergyVAD(
            sample_rate=self.sample_rate,
            frame_size=frame,
            threshold=self.threshold,
            noise_multiplier=self.noise_multiplier,
            silence_multiplier=self.silence_multiplier,
            min_speech_ms=1,
            min_silence_ms=1,
            initial_noise=self.noise_floor,
        )
        for start in range(0, arr.size, frame):
            voiced.append(probe.process(arr[start : start + frame]))
        indexes = [i for i, value in enumerate(voiced) if value]
        if not indexes:
            return arr
        pad = max(0, int(self.sample_rate * max(0, pad_ms) / 1000))
        start = max(0, indexes[0] * frame - pad)
        end = min(arr.size, (indexes[-1] + 1) * frame + pad)
        if min_ms and end - start < int(self.sample_rate * min_ms / 1000):
            return arr
        return arr[start:end]

