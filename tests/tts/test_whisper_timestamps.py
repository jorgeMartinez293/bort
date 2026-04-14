from unittest.mock import patch, MagicMock

def test_get_word_timestamps_returns_list_of_dicts():
    mock_segment = MagicMock()
    mock_word = MagicMock()
    mock_word.word = " honey"
    mock_word.start = 0.5
    mock_word.end = 0.9
    mock_segment.words = [mock_word]

    with patch("services.tts.whisper_timestamps.WhisperModel") as MockModel:
        instance = MockModel.return_value
        instance.transcribe.return_value = ([mock_segment], MagicMock())
        from services.tts.whisper_timestamps import get_word_timestamps
        result = get_word_timestamps("fake.wav", model_size="tiny")

    assert result == [{"word": "honey", "start": 0.5, "end": 0.9}]
