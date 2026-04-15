# services/scraper/reddit.py
import requests
from services.scraper.cleaner import clean_til, is_suitable


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
        results.append({
            "reddit_id": post["id"],
            "subreddit": post["subreddit"],
            "raw_title": post["title"],
            "cleaned_script": clean_til(post["title"]),
            "upvotes": post["score"],
        })
    return results
