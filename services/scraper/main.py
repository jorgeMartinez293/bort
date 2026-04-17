# services/scraper/main.py
import os, json, logging, schedule, time

from services.shared.db import get_conn, init_db
from services.shared.queue import get_queue, enqueue_tts
from services.scraper.reddit import fetch_posts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [scraper] %(message)s")
log = logging.getLogger(__name__)

BOT_ID = 1  # Phase 1: single bot, seeded in DB on first run

def seed_default_bot(conn):
    existing = conn.execute("SELECT id FROM bots WHERE id=1").fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO bots (id, name, niche, subreddits, schedule_cron, platforms, background_mode, active) "
            "VALUES (1,'did-you-know','facts','[\"todayilearned\",\"interestingasfuck\"]','0 */6 * * *','[\"youtube\"]','random',1)"
        )
        conn.commit()
        log.info("Seeded default bot")

def run_scrape():
    conn = get_conn()
    init_db(conn)
    seed_default_bot(conn)

    bot = conn.execute("SELECT * FROM bots WHERE id=?", (BOT_ID,)).fetchone()
    subreddits = json.loads(bot["subreddits"])
    seen = {r["reddit_id"] for r in conn.execute("SELECT reddit_id FROM content").fetchall()}

    q = get_queue("tts")
    total = 0
    for sub in subreddits:
        posts = fetch_posts(
            subreddit=sub,
            limit=25,
            seen_ids=seen,
            user_agent=os.environ.get("REDDIT_USER_AGENT", "bort/0.1"),
        )
        for post in posts:
            cur = conn.execute(
                "INSERT INTO content (bot_id, reddit_id, subreddit, raw_title, cleaned_script, upvotes, status, image_url) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (BOT_ID, post["reddit_id"], post["subreddit"], post["raw_title"], post["cleaned_script"], post["upvotes"], post["status"], post.get("image_url"))
            )
            conn.commit()
            assert cur.lastrowid is not None
            if post["status"] == "pending":
                enqueue_tts(q, content_id=cur.lastrowid)
            seen.add(post["reddit_id"])
            total += 1
    log.info(f"Scraped {total} new posts")

if __name__ == "__main__":
    log.info("Scraper starting — running immediately then every 6h")
    run_scrape()
    schedule.every(6).hours.do(run_scrape)
    while True:
        schedule.run_pending()
        time.sleep(60)
