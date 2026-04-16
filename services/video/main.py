# services/video/main.py
import os, json, logging, subprocess, requests

from services.shared.db import get_conn, init_db
from services.shared.queue import get_redis
from services.video.subtitles import timestamps_to_ass
from services.video.renderer import render, pick_background_clip, pick_music_track, RenderError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [video] %(message)s")
log = logging.getLogger(__name__)

MEDIA_PATH   = os.environ.get("MEDIA_PATH",   "/media")
MUSIC_PATH   = os.environ.get("MUSIC_PATH",   "/media/music")
MUSIC_VOLUME = float(os.environ.get("MUSIC_VOLUME", "0.25"))

def get_audio_duration(wav_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", wav_path],
        capture_output=True
    )
    return float(json.loads(result.stdout)["format"]["duration"])

def get_image_dimensions(img_path: str) -> tuple[int, int]:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-select_streams", "v:0", img_path],
        capture_output=True
    )
    stream = json.loads(result.stdout)["streams"][0]
    return stream["width"], stream["height"]

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
        # Download Reddit image if available
        image_path = None
        image_url = row["image_url"] if "image_url" in row.keys() else None
        if image_url:
            img_dest = os.path.join(audio_dir, f"{content_id}_img.jpg")
            try:
                resp = requests.get(image_url, headers={"User-Agent": "bort/0.1"}, timeout=15)
                resp.raise_for_status()
                with open(img_dest, "wb") as f:
                    f.write(resp.content)
                image_path = img_dest
                log.info(f"Downloaded image for content {content_id}")
            except Exception as e:
                log.warning(f"Image download failed for content {content_id}: {e}")

        # Calculate subtitle position: right below the image (or centered if no image)
        subtitle_top_y = 0
        image_top_y = 0
        if image_path:
            img_w, img_h = get_image_dimensions(image_path)
            scale = min(900 / img_w, 720 / img_h)  # must match renderer scale=900:720
            scaled_h = int(img_h * scale)
            image_top_y = (1920 - scaled_h) // 2
            subtitle_top_y = image_top_y + scaled_h + 25

        with open(ts_path) as f:
            timestamps = json.load(f)
        ass_content = timestamps_to_ass(timestamps, with_image=image_path is not None, subtitle_top_y=subtitle_top_y)
        with open(ass_path, "w") as f:
            f.write(ass_content)

        duration = get_audio_duration(wav_path)
        background = pick_background_clip(bg_dir)
        music = pick_music_track(MUSIC_PATH)
        render(background, wav_path, ass_path, out_path, duration,
               music=music, music_volume=MUSIC_VOLUME, image_path=image_path, image_top_y=image_top_y)

        thumb_path = os.path.splitext(out_path)[0] + "_thumb.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-i", out_path, "-vframes", "1", "-q:v", "10", "-vf", "scale=200:-2", thumb_path],
            capture_output=True,
        )

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
