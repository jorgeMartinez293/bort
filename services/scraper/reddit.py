import praw
from services.scraper.cleaner import clean_til, is_suitable

def fetch_posts(
    subreddit: str,
    limit: int,
    seen_ids: set,
    client_id: str,
    client_secret: str,
    user_agent: str,
) -> list[dict]:
    """Fetch top posts from a subreddit, filter and clean them."""
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )
    results = []
    for post in reddit.subreddit(subreddit).hot(limit=limit):
        if not is_suitable(post.score, post.id, seen_ids):
            continue
        results.append({
            "reddit_id": post.id,
            "subreddit": post.subreddit.display_name,
            "raw_title": post.title,
            "cleaned_script": clean_til(post.title),
            "upvotes": post.score,
        })
    return results
