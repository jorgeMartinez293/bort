# tests/shared/test_queue.py
from unittest.mock import MagicMock
from services.shared.queue import enqueue_tts, enqueue_render

def test_enqueue_tts_puts_correct_args_on_queue():
    mock_q = MagicMock()
    enqueue_tts(mock_q, content_id=42)
    mock_q.enqueue.assert_called_once_with(
        "services.tts.main.process_content",
        kwargs={"content_id": 42},
        job_id="tts-42",
        job_timeout=300,
    )

def test_enqueue_render_puts_correct_args_on_queue():
    mock_q = MagicMock()
    enqueue_render(mock_q, content_id=7)
    mock_q.enqueue.assert_called_once_with(
        "services.video.main.process_content",
        kwargs={"content_id": 7},
        job_id="render-7",
        job_timeout=600,
    )
