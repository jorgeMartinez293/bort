#!/usr/bin/env python3
"""Purge existing audio/video files and re-enqueue all DB content through TTS → render.

Re-runs clean_til + expand_script over every raw_title so the updated expander
(which now always appends a curious-fact sentence) takes effect.

Run inside the tts-worker container:
    docker compose exec tts-worker python scripts/regenerate.py
"""
import os
import logging

from services.shared.db import get_conn, init_db
from services.shared.queue import get_queue, enqueue_tts
from services.scraper.cleaner import clean_til
from services.scraper.expander import expand_script

logging.basicConfig(level=logging.INFO, format="%(asctime)s [regen] %(message)s")
log = logging.getLogger(__name__)

MEDIA_PATH = os.environ.get("MEDIA_PATH", "/media")


def _delete_dir_files(directory: str) -> int:
    """Delete all files in a directory. Returns count deleted."""
    if not os.path.isdir(directory):
        return 0
    count = 0
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
            count += 1
    return count


def run():
    conn = get_conn()
    init_db(conn)

    rows = conn.execute("SELECT id, raw_title FROM content").fetchall()
    if not rows:
        log.info("No content in DB — nothing to do.")
        return

    # 1. Re-expand scripts so every entry gets a curious-fact sentence
    log.info(f"Re-expanding scripts for {len(rows)} content rows...")
    for row in rows:
        new_script = expand_script(clean_til(row["raw_title"]))
        conn.execute(
            "UPDATE content SET cleaned_script=? WHERE id=?",
            (new_script, row["id"]),
        )
    conn.commit()
    log.info("Scripts updated.")

    # 2. Delete generated files from disk
    video_dir = os.path.join(MEDIA_PATH, "generated", "videos")
    audio_dir = os.path.join(MEDIA_PATH, "generated", "audio")
    n_videos = _delete_dir_files(video_dir)
    n_audio  = _delete_dir_files(audio_dir)
    log.info(f"Deleted {n_videos} video file(s) and {n_audio} audio file(s).")

    # 3. Purge DB records (FK order: uploads → videos)
    conn.execute("DELETE FROM uploads")
    conn.execute("DELETE FROM videos")
    conn.execute("UPDATE content SET status='pending'")
    conn.commit()
    log.info("Cleared uploads/videos tables; all content reset to 'pending'.")

    # 4. Re-enqueue every content item through the TTS pipeline
    q = get_queue("tts")
    content_ids = [r["id"] for r in conn.execute("SELECT id FROM content ORDER BY id").fetchall()]
    for cid in content_ids:
        enqueue_tts(q, content_id=cid)
    log.info(f"Enqueued {len(content_ids)} item(s) for TTS → render.")


if __name__ == "__main__":
    run()
