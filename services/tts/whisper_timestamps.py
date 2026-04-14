from typing import Optional
from faster_whisper import WhisperModel

_model = None
_model_size_loaded: Optional[str] = None

def _get_model(model_size: str = "tiny") -> WhisperModel:
    global _model, _model_size_loaded
    if _model is None or _model_size_loaded != model_size:
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        _model_size_loaded = model_size
    return _model

def get_word_timestamps(wav_path: str, model_size: str = "tiny") -> list[dict]:
    """
    Transcribe wav_path with faster-whisper and return word-level timestamps.
    Returns: [{"word": str, "start": float, "end": float}, ...]
    """
    model = _get_model(model_size)
    segments, _ = model.transcribe(wav_path, word_timestamps=True)
    words = []
    for segment in segments:
        for w in segment.words:
            words.append({"word": w.word.strip(), "start": w.start, "end": w.end})
    return words
