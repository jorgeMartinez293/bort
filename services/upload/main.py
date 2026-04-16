import json
import logging

from services.shared.db import get_conn, init_db
from services.shared.queue import get_redis
from services.upload.youtube import build_service, upload_video
from services.scraper.cleaner import format_youtube_title

logging.basicConfig(level=logging.INFO, format="%(asctime)s [upload] %(message)s")
log = logging.getLogger(__name__)


def process_upload(video_id: int) -> None:
    conn = get_conn()
    init_db(conn)

    row = conn.execute(
        "SELECT v.*, c.raw_title, b.yt_description, b.yt_tags, b.yt_privacy "
        "FROM videos v "
        "JOIN content c ON v.content_id = c.id "
        "JOIN bots b ON v.bot_id = b.id "
        "WHERE v.id=?",
        (video_id,),
    ).fetchone()
    if not row:
        log.error(f"Video {video_id} not found")
        return

    description = row["yt_description"] or ""
    tags = json.loads(row["yt_tags"] or "[]")
    privacy = row["yt_privacy"] or "private"

    conn.execute("UPDATE videos SET status='uploading' WHERE id=?", (video_id,))
    conn.execute(
        "UPDATE uploads SET status='uploading' WHERE video_id=? AND platform='youtube'",
        (video_id,),
    )
    conn.commit()

    try:
        service = build_service()
        yt_id = upload_video(
            service,
            title=format_youtube_title(row["raw_title"]),
            description=description,
            tags=tags,
            video_path=row["video_path"],
            privacy_status=privacy,
        )
        conn.execute(
            "UPDATE uploads SET status='done', platform_video_id=?, published_at=CURRENT_TIMESTAMP "
            "WHERE video_id=? AND platform='youtube'",
            (yt_id, video_id),
        )
        conn.execute("UPDATE videos SET status='uploaded' WHERE id=?", (video_id,))
        conn.commit()
        log.info(f"Video {video_id} uploaded → YouTube {yt_id} ({privacy})")
    except Exception as e:
        log.error(f"Upload failed for video {video_id}: {e}")
        conn.execute(
            "UPDATE uploads SET status='failed', error_msg=? "
            "WHERE video_id=? AND platform='youtube'",
            (str(e), video_id),
        )
        conn.execute("UPDATE videos SET status='upload_failed' WHERE id=?", (video_id,))
        conn.commit()


if __name__ == "__main__":
    from rq import Worker

    log.info("Upload worker starting")
    Worker(["upload"], connection=get_redis()).work()
