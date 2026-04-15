from unittest.mock import patch, MagicMock
from services.scraper.reddit import fetch_posts


def _make_response(posts_data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {"children": [{"data": p} for p in posts_data]}
    }
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_fetch_posts_returns_cleaned_list():
    posts_data = [
        {"id": "aaa", "title": "TIL that honey never expires.", "score": 50_000,
         "subreddit": "todayilearned", "stickied": False},
        {"id": "bbb", "title": "TIL octopuses have three hearts", "score": 25_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 2
    assert posts[0]["reddit_id"] == "aaa"
    assert posts[0]["cleaned_script"].startswith("Did you know")
    assert posts[0]["upvotes"] == 50_000


def test_fetch_posts_skips_seen_ids():
    posts_data = [
        {"id": "aaa", "title": "TIL that honey never expires.", "score": 50_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids={"aaa"})
    assert posts == []


def test_fetch_posts_skips_stickied():
    posts_data = [
        {"id": "aaa", "title": "TIL that honey never expires.", "score": 50_000,
         "subreddit": "todayilearned", "stickied": True},
        {"id": "bbb", "title": "TIL octopuses have three hearts", "score": 25_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["reddit_id"] == "bbb"
