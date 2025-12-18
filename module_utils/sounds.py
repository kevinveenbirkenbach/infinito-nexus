import os
import warnings
from functools import lru_cache
from typing import Optional

_SOUND_DISABLED_REASON: Optional[str] = None


@lru_cache(maxsize=1)
def _warn_sound_disabled_once() -> None:
    if not _SOUND_DISABLED_REASON:
        return
    warnings.warn(
        f"Sound support disabled: {_SOUND_DISABLED_REASON}",
        RuntimeWarning,
        stacklevel=2,
    )


class DummySound:
    @staticmethod
    def play_start_sound() -> None:
        _warn_sound_disabled_once()

    @staticmethod
    def play_infinito_intro_sound() -> None:
        _warn_sound_disabled_once()

    @staticmethod
    def play_finished_successfully_sound() -> None:
        _warn_sound_disabled_once()

    @staticmethod
    def play_finished_failed_sound() -> None:
        _warn_sound_disabled_once()

    @staticmethod
    def play_warning_sound() -> None:
        _warn_sound_disabled_once()


try:
    import numpy as np
    import simpleaudio as sa
    import shutil
    import subprocess
    import tempfile
    import wave as wavmod

    class Sound:
        """
        Sound effects for the application.
        """

        fs = 44100
        complexity_factor = 10
        max_length = 2.0

        @staticmethod
        def _generate_complex_wave(
            frequency: float,
            duration: float,
            harmonics: int | None = None,
        ) -> np.ndarray:
            if harmonics is None:
                harmonics = Sound.complexity_factor

            t = np.linspace(0, duration, int(Sound.fs * duration), False)
            wave = np.zeros_like(t)

            for n in range(1, harmonics + 1):
                wave += (1 / n) * np.sin(2 * np.pi * frequency * n * t)

            # ADSR envelope
            attack = int(0.02 * Sound.fs)
            release = int(0.05 * Sound.fs)
            env = np.ones_like(wave)
            env[:attack] = np.linspace(0, 1, attack)
            env[-release:] = np.linspace(1, 0, release)

            wave *= env
            wave /= np.max(np.abs(wave))
            return (wave * (2**15 - 1)).astype(np.int16)

        @staticmethod
        def _crossfade(w1: np.ndarray, w2: np.ndarray, fade_len: int) -> np.ndarray:
            fade_len = min(fade_len, len(w1), len(w2))
            if fade_len <= 0:
                return np.concatenate([w1, w2])

            fade_out = np.linspace(1, 0, fade_len)
            fade_in = np.linspace(0, 1, fade_len)

            w1_end = w1[-fade_len:].astype(np.float32) * fade_out
            w2_start = w2[:fade_len].astype(np.float32) * fade_in
            middle = (w1_end + w2_start).astype(np.int16)

            return np.concatenate([w1[:-fade_len], middle, w2[fade_len:]])

        @staticmethod
        def _play_via_system(wave: np.ndarray) -> None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                fname = f.name

            try:
                with wavmod.open(fname, "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(Sound.fs)
                    w.writeframes(wave.tobytes())

                def run(cmd: list[str]) -> bool:
                    return (
                        subprocess.run(
                            cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False,
                        ).returncode
                        == 0
                    )

                if shutil.which("pw-play") and run(["pw-play", fname]):
                    return
                if shutil.which("paplay") and run(["paplay", fname]):
                    return
                if shutil.which("aplay") and run(["aplay", "-q", fname]):
                    return
                if shutil.which("ffplay") and run(
                    ["ffplay", "-autoexit", "-nodisp", fname]
                ):
                    return

                play_obj = sa.play_buffer(wave, 1, 2, Sound.fs)
                play_obj.wait_done()

            finally:
                try:
                    os.unlink(fname)
                except Exception as e:
                    warnings.warn(
                        f"Failed to delete temporary sound file {fname}: {e}",
                        RuntimeWarning,
                    )

        @staticmethod
        def _play(wave: np.ndarray) -> None:
            backend = os.getenv("INFINITO_AUDIO_BACKEND", "auto").lower()

            if backend == "system":
                Sound._play_via_system(wave)
                return

            if backend == "simpleaudio":
                play_obj = sa.play_buffer(wave, 1, 2, Sound.fs)
                play_obj.wait_done()
                return

            # auto
            try:
                play_obj = sa.play_buffer(wave, 1, 2, Sound.fs)
                play_obj.wait_done()
            except Exception:
                Sound._play_via_system(wave)

        @classmethod
        def play_infinito_intro_sound(cls) -> None:
            build_time = 10.0
            celebr_time = 12.0
            overlap = 3.0

            bass_seg = 0.125
            melody_seg = 0.25
            bass_freq = 65.41
            melody_freqs = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]

            steps = int(build_time / (bass_seg + melody_seg))
            build_seq: list[np.ndarray] = []

            for i in range(steps):
                amp = (i + 1) / steps
                b = (
                    cls._generate_complex_wave(bass_freq, bass_seg).astype(np.float32)
                    * amp
                )
                m = (
                    cls._generate_complex_wave(
                        melody_freqs[i % len(melody_freqs)], melody_seg
                    ).astype(np.float32)
                    * amp
                )
                build_seq.append(b.astype(np.int16))
                build_seq.append(m.astype(np.int16))

            build_wave = np.concatenate(build_seq)

            roots = [523.25, 349.23, 233.08, 155.56, 103.83, 69.30, 46.25]
            chord_time = celebr_time / len(roots)
            celebr_seq: list[np.ndarray] = []

            for root in roots:
                t = np.linspace(0, chord_time, int(cls.fs * chord_time), False)
                chord = sum(
                    np.sin(2 * np.pi * f * t)
                    for f in [root, root * 5 / 4, root * 3 / 2]
                )
                chord /= np.max(np.abs(chord))
                celebr_seq.append((chord * (2**15 - 1)).astype(np.int16))

            celebr_wave = np.concatenate(celebr_seq)
            breakdown_wave = np.concatenate(list(reversed(build_seq)))

            fade_samples = int(overlap * cls.fs)
            bc = cls._crossfade(build_wave, celebr_wave, fade_samples)
            full = cls._crossfade(bc, breakdown_wave, fade_samples)

            cls._play(full)

        @classmethod
        def play_start_sound(cls) -> None:
            freqs = [523.25, 659.26, 783.99, 880.00, 1046.50, 1174.66]
            cls._prepare_and_play(freqs)

        @classmethod
        def play_finished_successfully_sound(cls) -> None:
            freqs = [523.25, 587.33, 659.26, 783.99, 880.00, 987.77]
            cls._prepare_and_play(freqs)

        @classmethod
        def play_finished_failed_sound(cls) -> None:
            freqs = [880.00, 830.61, 783.99, 659.26, 622.25, 523.25]
            durations = [0.4, 0.3, 0.25, 0.25, 0.25, 0.25]
            cls._prepare_and_play(freqs, durations)

        @classmethod
        def play_warning_sound(cls) -> None:
            freqs = [700.00, 550.00, 750.00, 500.00, 800.00, 450.00]
            cls._prepare_and_play(freqs)

        @classmethod
        def _prepare_and_play(
            cls, freqs: list[float], durations: list[float] | None = None
        ) -> None:
            count = len(freqs)

            if durations is None:
                durations = [cls.max_length / count] * count
            else:
                total = sum(durations)
                durations = [d * cls.max_length / total for d in durations]

            waves = [cls._generate_complex_wave(f, d) for f, d in zip(freqs, durations)]
            cls._play(np.concatenate(waves))

except ImportError as exc:
    # Do NOT warn at import time — this module is used in many unit tests / subprocess calls.
    # Warn only when a sound method is actually invoked.
    _SOUND_DISABLED_REASON = str(exc)
    Sound = DummySound
