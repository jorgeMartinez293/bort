from services.video.subtitles import timestamps_to_ass, format_ass_time

def test_format_ass_time():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(61.5) == "0:01:01.50"
    assert format_ass_time(3661.0) == "1:01:01.00"

def test_timestamps_to_ass_contains_header():
    words = [{"word": "Hello", "start": 0.0, "end": 0.5}]
    result = timestamps_to_ass(words)
    assert "[Script Info]" in result
    assert "[V4+ Styles]" in result
    assert "[Events]" in result

def test_timestamps_to_ass_groups_words_into_chunks():
    words = [
        {"word": "Did", "start": 0.0, "end": 0.3},
        {"word": "you", "start": 0.3, "end": 0.6},
        {"word": "know", "start": 0.6, "end": 0.9},
        {"word": "that", "start": 0.9, "end": 1.2},
    ]
    result = timestamps_to_ass(words, words_per_chunk=2)
    # 2 chunks × 2 words each = 4 dialogue lines (one per active word)
    dialogue_lines = [l for l in result.split("\n") if l.startswith("Dialogue:")]
    assert len(dialogue_lines) == 4

def test_timestamps_to_ass_highlights_active_word():
    words = [
        {"word": "Honey", "start": 0.0, "end": 0.5},
        {"word": "never", "start": 0.5, "end": 0.9},
        {"word": "expires", "start": 0.9, "end": 1.4},
    ]
    result = timestamps_to_ass(words, words_per_chunk=3)
    # Active word should use highlight color override (amber in ASS ABGR format)
    assert "{\\c&H0020A0E8&}" in result
