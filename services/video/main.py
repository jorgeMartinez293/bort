# services/video/main.py
import os, json, logging

from services.shared.db import get_conn, init_db
from services.shared.queue import get_redis
from services.video.subtitles import timestamps_to_ass
from services.video.renderer import render, pick_background_clip, RenderError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [video] %(message)s")
log = logging.getLogger(__name__)

MEDIA_PATH = os.environ.get("MEDIA_PATH", "/media")

def get_audio_duration(wav_path: str) -> float:
    """Get duration of WAV using ffprobe."""
    import subprocess, json as _json
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", wav_path],
        capture_output=True
    )
    data = _json.loads(result.stdout)
    return float(data["format"]["duration"])

def process_content(content_id: int):
    conn = get_conn()
    init_db(conn)
    row = conn.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
    if not row:
        log.error(f"Content {content_id} not found")
        return

    audio_dir = os.path.join(MEDIA_PATH, "generated", "audio")
    video_dir = os.path.join(MEDIA_PATH, "generated", "videos")
    bg_dir    = os.path.join(MEDIA_PATH, "backgrounds")
    os.makedirs(video_dir, exist_ok=True)

    wav_path  = os.path.join(audio_dir, f"{content_id}.wav")
    ts_path   = os.path.join(audio_dir, f"{content_id}_timestamps.json")
    ass_path  = os.path.join(audio_dir, f"{content_id}.ass")
    out_path  = os.path.join(video_dir, f"{content_id}.mp4")

    try:
        with open(ts_path) as f:
            timestamps = json.load(f)
        ass_content = timestamps_to_ass(timestamps)
        with open(ass_path, "w") as f:
            f.write(ass_content)

        duration = get_audio_duration(wav_path)
        background = pick_background_clip(bg_dir)
        render(background, wav_path, ass_path, out_path, duration)

        conn.execute(
            "INSERT INTO videos (content_id, bot_id, audio_path, video_path, duration_secs, status) "
            "VALUES (?,?,?,?,?,'pending_review')",
            (content_id, row["bot_id"], wav_path, out_path, duration)
        )
        conn.commit()
        conn.execute("UPDATE content SET status='rendered' WHERE id=?", (content_id,))
        conn.commit()
        log.info(f"Rendered video for content {content_id} → {out_path}")
    except (RenderError, FileNotFoundError, json.JSONDecodeError, ValueError, OSError) as e:
        log.error(f"Render failed for content {content_id}: {e}")
        conn.execute("UPDATE content SET status='skip' WHERE id=?", (content_id,))
        conn.commit()

if __name__ == "__main__":
    from rq import Worker
    log.info("Video worker starting")
    worker = Worker(["render"], connection=get_redis())  # type: ignore
    worker.work()
