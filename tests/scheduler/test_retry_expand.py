# tests/scheduler/test_retry_expand.py
from unittest.mock import MagicMock, patch
from services.scheduler.main import retry_expand


def test_retry_expand_expands_and_enqueues_on_gemini_success():
    rows = [{"id": 7, "cleaned_script": "Did you know bees dance."}]
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    mock_q = MagicMock()
    elaboration = "This happens because bees use waggle dances to communicate direction."

    with patch("services.scheduler.main.gemini_elaborate_or_none", return_value=elaboration), \
         patch("services.scheduler.main.enqueue_tts") as mock_enqueue:
        retry_expand(conn, mock_q)

    mock_enqueue.assert_called_once_with(mock_q, content_id=7)
    conn.commit.assert_called_once()


def test_retry_expand_breaks_on_first_gemini_failure():
    rows = [
        {"id": 1, "cleaned_script": "Short script one."},
        {"id": 2, "cleaned_script": "Short script two."},
    ]
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    mock_q = MagicMock()

    with patch("services.scheduler.main.gemini_elaborate_or_none", return_value=None), \
         patch("services.scheduler.main.enqueue_tts") as mock_enqueue:
        retry_expand(conn, mock_q)

    mock_enqueue.assert_not_called()
    conn.commit.assert_not_called()
