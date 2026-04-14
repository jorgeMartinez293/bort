# services/tts/main.py
import os, json, logging

from services.shared.db import get_conn, init_db
from services.shared.queue import get_queue, enqueue_render
from services.tts.piper_tts import synthesize, TTSError
from services.tts.whisper_timestamps import get_word_timestamps

logging.basicConfig(level=logging.INFO, format="%(asctime)s [tts] %(message)s")
log = logging.getLogger(__name__)

MEDIA_PATH = os.environ.get("MEDIA_PATH", "/media")
MODEL_PATH = os.environ.get("PIPER_MODEL_PATH", "/media/tts_models/en_US-lessac-medium.onnx")

def process_content(content_id: int):
    conn = get_conn()
    init_db(conn)
    row = conn.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
    if not row:
        log.error(f"Content {content_id} not found")
        return

    audio_dir = os.path.join(MEDIA_PATH, "generated", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    wav_path = os.path.join(audio_dir, f"{content_id}.wav")
    ts_path = os.path.join(audio_dir, f"{content_id}_timestamps.json")

    try:
        synthesize(row["cleaned_script"], wav_path, MODEL_PATH)
        log.info(f"TTS done for content {content_id}")
        timestamps = get_word_timestamps(wav_path)
        with open(ts_path, "w") as f:
            json.dump(timestamps, f)
        conn.execute("UPDATE content SET status='tts_done' WHERE id=?", (content_id,))
        conn.commit()
        q = get_queue("render")
        enqueue_render(q, content_id=content_id)
        log.info(f"Enqueued render for content {content_id}")
    except TTSError as e:
        log.error(f"TTS failed for content {content_id}: {e}")
        conn.execute("UPDATE content SET status='skip' WHERE id=?", (content_id,))
        conn.commit()

if __name__ == "__main__":
    from rq import Worker
    from services.shared.queue import get_redis
    log.info("TTS worker starting")
    worker = Worker(["tts"], connection=get_redis())
    worker.work()
