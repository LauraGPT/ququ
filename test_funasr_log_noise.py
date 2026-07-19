import contextlib
import io
import os
import sys
import tempfile
import unittest

from funasr_server import FunASRServer


class NoisyModel:
    def __init__(self, result):
        self.result = result

    def generate(self, **kwargs):
        print("中文 stdout noise")
        print("\r  0%|          | 0/1 [00:00<?, ?it/s]", file=sys.stderr)
        print("中文 stderr noise", file=sys.stderr)
        return self.result


class FunASRConsoleNoiseTest(unittest.TestCase):
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
