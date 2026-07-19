import contextlib
import io
import os
import sys
import tempfile
import threading
import unittest

from funasr_server import FunASRServer, suppress_console_output


class NoisyModel:
    def __init__(self, result):
        self.result = result

    def generate(self, **kwargs):
        print("中文 stdout noise")
        print("\r  0%|          | 0/1 [00:00<?, ?it/s]", file=sys.stderr)
        print("中文 stderr noise", file=sys.stderr)
        return self.result


class FunASRConsoleNoiseTest(unittest.TestCase):
    def test_overlapping_suppression_restores_console_streams(self):
        first_entered = threading.Event()
        second_entered = threading.Event()
        first_may_exit = threading.Event()
        second_may_exit = threading.Event()
        errors = []

        def first_worker():
            try:
                with suppress_console_output():
                    first_entered.set()
                    second_entered.wait(timeout=5)
                    first_may_exit.wait(timeout=5)
            except Exception as exc:
                errors.append(exc)

        def second_worker():
            try:
                first_entered.wait(timeout=5)
                with suppress_console_output():
                    second_entered.set()
                    first_may_exit.set()
                    second_may_exit.wait(timeout=5)
                    print("still suppressed after first worker exits")
            except Exception as exc:
                errors.append(exc)

        stdout = io.StringIO()
        stderr = io.StringIO()
        first = threading.Thread(target=first_worker)
        second = threading.Thread(target=second_worker)

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            first.start()
            second.start()
            first.join(timeout=5)
            second_may_exit.set()
            second.join(timeout=5)
            print("visible after suppression")

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(stdout.getvalue(), "visible after suppression\n")
        self.assertEqual(stderr.getvalue(), "")

    def test_transcription_suppresses_model_console_noise(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio:
            audio_path = audio.name

        try:
            server = FunASRServer(damo_root=tempfile.gettempdir())
            server.initialized = True
            server.vad_model = NoisyModel([{"value": [[0, 1000]]}])
            server.asr_model = NoisyModel([{"text": "测试文本"}])
            server.punc_model = NoisyModel([{"text": "测试文本。"}])

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = server.transcribe_audio(audio_path)

            self.assertTrue(result["success"])
            self.assertEqual(result["text"], "测试文本。")
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), "")
        finally:
            os.unlink(audio_path)


if __name__ == "__main__":
    unittest.main()
