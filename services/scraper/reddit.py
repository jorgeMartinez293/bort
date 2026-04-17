import os
import requests
from services.scraper.cleaner import clean_til, is_suitable
from services.scraper.expander import gemini_elaborate_or_none, TARGET_WORD_COUNT

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _extract_image_url(post: dict) -> "str | None":
    if post.get("post_hint") != "image":
        return None
    url = post.get("url", "")
    ext = os.path.splitext(url.lower().split("?")[0])[1]
    return url if ext in _IMAGE_EXTS else None


def fetch_posts(
    subreddit: str,
    limit: int,
    seen_ids: set,
    user_agent: str = "bort/0.1",
) -> list:
    """Fetch hot posts from a subreddit via the public Reddit JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    response = requests.get(
        url,
        params={"limit": limit},
        headers={"User-Agent": user_agent},
        timeout=10,
    )
    response.raise_for_status()
    children = response.json()["data"]["children"]
    results = []
    for child in children:
        post = child["data"]
        if post.get("stickied"):
            continue
        if not is_suitable(post["score"], post["id"], seen_ids):
            continue

        script = clean_til(post["title"])
        if len(script.split()) >= TARGET_WORD_COUNT:
            cleaned_script = script
            status = "pending"
        else:
            elaboration = gemini_elaborate_or_none(script)
            if elaboration:
                base = script.rstrip()
                if base and base[-1] not in ".!?":
                    base += "."
                cleaned_script = f"{base} {elaboration}"
                status = "pending"
            else:
                cleaned_script = script
                status = "expand_pending"

        results.append({
            "reddit_id": post["id"],
            "subreddit": post["subreddit"],
            "raw_title": post["title"],
            "cleaned_script": cleaned_script,
            "upvotes": post["score"],
            "image_url": _extract_image_url(post),
            "status": status,
        })
    return results
