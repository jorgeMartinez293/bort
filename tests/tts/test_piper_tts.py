import pytest
from unittest.mock import patch, MagicMock

def test_synthesize_returns_wav_path(tmp_path):
    with patch("services.tts.piper_tts.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        out = tmp_path / "out.wav"
        from services.tts.piper_tts import synthesize
        result = synthesize("Hello world", output_path=str(out), model_path="fake.onnx")
        assert result == str(out)
        cmd = mock_run.call_args[0][0]
        assert "--length_scale" in cmd
        assert "1.2" in cmd


def test_synthesize_length_scale_custom(tmp_path):
    with patch("services.tts.piper_tts.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        from services.tts.piper_tts import synthesize
        synthesize("Hi", output_path=str(tmp_path / "out.wav"), model_path="fake.onnx", length_scale=1.5)
        cmd = mock_run.call_args[0][0]
        assert "1.5" in cmd

def test_synthesize_raises_on_nonzero_returncode(tmp_path):
    with patch("services.tts.piper_tts.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr=b"error")
        from services.tts.piper_tts import synthesize, TTSError
        with pytest.raises(TTSError):
            synthesize("Hello", output_path=str(tmp_path / "out.wav"), model_path="fake.onnx")
