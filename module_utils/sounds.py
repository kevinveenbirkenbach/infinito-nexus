import os

class DummySound:
    @staticmethod
    def play_start_sound(): pass
    @staticmethod
    def play_infinito_intro_sound(): pass
    @staticmethod
    def play_finished_successfully_sound(): pass
    @staticmethod
    def play_finished_failed_sound(): pass
    @staticmethod
    def play_warning_sound(): pass

_IN_DOCKER = os.path.exists('/.dockerenv')

if _IN_DOCKER:
    Sound = DummySound
else:
    try:
        import numpy as np
        import simpleaudio as sa
        import shutil, subprocess, tempfile, wave as wavmod
        class Sound:
            """
            Sound effects for the application with enhanced complexity.
            Each sound uses at least 6 distinct tones and lasts no more than max_length seconds,
            except the intro sound which is a detailed 26-second Berlin techno-style build-up, 12-second celebration with a descending-fifth chord sequence of 7 chords, and breakdown with melodic background.
            Transitions between phases now crossfade over 3 seconds for smoother flow.
            """

            fs = 44100  # Sampling rate (samples per second)
            complexity_factor = 10  # Number of harmonics to sum for richer timbres
            max_length = 2.0  # Maximum total duration of any sound in seconds

            @staticmethod
            def _generate_complex_wave(frequency: float, duration: float, harmonics: int = None) -> np.ndarray:
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
                # Ensure fade_len less than each
                fade_len = min(fade_len, len(w1), len(w2))
                fade_out = np.linspace(1, 0, fade_len)
                fade_in = np.linspace(0, 1, fade_len)
                w1_end = w1[-fade_len:] * fade_out
                w2_start = w2[:fade_len] * fade_in
                middle = (w1_end + w2_start).astype(np.int16)
                return np.concatenate([w1[:-fade_len], middle, w2[fade_len:]])

            @staticmethod
            def _play_via_system(wave: np.ndarray):
                # Write a temp WAV and play it via available system player
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    fname = f.name
                try:
                    with wavmod.open(fname, "wb") as w:
                        w.setnchannels(1)
                        w.setsampwidth(2)
                        w.setframerate(Sound.fs)
                        w.writeframes(wave.tobytes())
                    def run(cmd):
                        return subprocess.run(
                            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        ).returncode == 0
                    # Preferred order: PipeWire → PulseAudio → ALSA → ffplay
                    if shutil.which("pw-play") and run(["pw-play", fname]): return
                    if shutil.which("paplay")  and run(["paplay",  fname]): return
                    if shutil.which("aplay")   and run(["aplay", "-q", fname]): return
                    if shutil.which("ffplay")  and run(["ffplay", "-autoexit", "-nodisp", fname]): return
                    # Last resort if no system player exists: simpleaudio
                    play_obj = sa.play_buffer(wave, 1, 2, Sound.fs)
                    play_obj.wait_done()
                finally:
                    try: os.unlink(fname)
                    except Exception: pass

            @staticmethod
            def _play(wave: np.ndarray):
                # Switch via env: system | simpleaudio | auto (default)
                backend = os.getenv("INFINITO_AUDIO_BACKEND", "auto").lower()
                if backend == "system":
                    return Sound._play_via_system(wave)
                if backend == "simpleaudio":
                    play_obj = sa.play_buffer(wave, 1, 2, Sound.fs)
                    play_obj.wait_done()
                    return
                # auto: try simpleaudio first; if it fails, fall back to system
                try:
                    play_obj = sa.play_buffer(wave, 1, 2, Sound.fs)
                    play_obj.wait_done()
                except Exception:
                    Sound._play_via_system(wave)

            @classmethod
            def play_infinito_intro_sound(cls):
                # Phase durations
                build_time = 10.0
                celebr_time = 12.0
                breakdown_time = 10.0
                overlap = 3.0  # seconds of crossfade
                bass_seg = 0.125  # 1/8s kick
                melody_seg = 0.25  # 2/8s melody
                bass_freq = 65.41  # C2 kick
                melody_freqs = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]

                # Build-up phase
                steps = int(build_time / (bass_seg + melody_seg))
                build_seq = []
                for i in range(steps):
                    amp = (i + 1) / steps
                    b = cls._generate_complex_wave(bass_freq, bass_seg).astype(np.float32) * amp
                    m = cls._generate_complex_wave(melody_freqs[i % len(melody_freqs)], melody_seg).astype(np.float32) * amp
                    build_seq.append(b.astype(np.int16))
                    build_seq.append(m.astype(np.int16))
                build_wave = np.concatenate(build_seq)

                # Celebration phase: 7 descending-fifth chords
                roots = [523.25, 349.23, 233.08, 155.56, 103.83, 69.30, 46.25]
                chord_time = celebr_time / len(roots)
                celebr_seq = []
                for root in roots:
                    t = np.linspace(0, chord_time, int(cls.fs * chord_time), False)
                    chord = sum(np.sin(2 * np.pi * f * t) for f in [root, root * 5/4, root * 3/2])
                    chord /= np.max(np.abs(chord))
                    celebr_seq.append((chord * (2**15 - 1)).astype(np.int16))
                celebr_wave = np.concatenate(celebr_seq)

                # Breakdown phase (mirror of build-up)
                breakdown_wave = np.concatenate(list(reversed(build_seq)))

                # Crossfade transitions
                fade_samples = int(overlap * cls.fs)
                bc = cls._crossfade(build_wave, celebr_wave, fade_samples)
                full = cls._crossfade(bc, breakdown_wave, fade_samples)

                cls._play(full)

            @classmethod
            def play_start_sound(cls):
                freqs = [523.25, 659.26, 783.99, 880.00, 1046.50, 1174.66]
                cls._prepare_and_play(freqs)

            @classmethod
            def play_finished_successfully_sound(cls):
                freqs = [523.25, 587.33, 659.26, 783.99, 880.00, 987.77]
                cls._prepare_and_play(freqs)

            @classmethod
            def play_finished_failed_sound(cls):
                freqs = [880.00, 830.61, 783.99, 659.26, 622.25, 523.25]
                durations = [0.4, 0.3, 0.25, 0.25, 0.25, 0.25]
                cls._prepare_and_play(freqs, durations)

            @classmethod
            def play_warning_sound(cls):
                freqs = [700.00, 550.00, 750.00, 500.00, 800.00, 450.00]
                cls._prepare_and_play(freqs)

            @classmethod
            def _prepare_and_play(cls, freqs, durations=None):
                count = len(freqs)
                if durations is None:
                    durations = [cls.max_length / count] * count
                else:
                    total = sum(durations)
                    durations = [d * cls.max_length / total for d in durations]
                waves = [cls._generate_complex_wave(f, d) for f, d in zip(freqs, durations)]
                cls._play(np.concatenate(waves))
    except Exception:
        warnings.warn("Sound support disabled: numpy or simpleaudio could not be imported", RuntimeWarning)
        Sound = DummySound
