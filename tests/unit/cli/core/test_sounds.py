import unittest
from unittest.mock import patch

from cli.core.sounds import play_sound_in_child, failure_with_warning_loop


class TestSounds(unittest.TestCase):
    @patch("cli.core.sounds.Process")
    def test_play_sound_in_child_failure_returns_false(self, mock_process_cls):
        class FakeProcess:
            def __init__(self, target=None, args=None):
                self.exitcode = 1

            def start(self):
                pass

            def join(self):
                pass

        mock_process_cls.side_effect = FakeProcess

        ok = play_sound_in_child("play_warning_sound")
        self.assertFalse(ok)

    @patch("cli.core.sounds.time.sleep")
    @patch("cli.core.sounds.play_sound_in_child")
    def test_failure_with_warning_loop_no_signal_skips_sounds_and_exits(
        self, mock_play, _mock_sleep
    ):
        # time.monotonic jumps past timeout
        with patch("cli.core.sounds.time.monotonic", side_effect=[0.0, 100.0]):
            with self.assertRaises(SystemExit):
                failure_with_warning_loop(
                    no_signal=True, sound_enabled=True, alarm_timeout=1
                )

        mock_play.assert_not_called()


if __name__ == "__main__":
    unittest.main()
