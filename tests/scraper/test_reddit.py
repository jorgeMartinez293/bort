from unittest.mock import patch, MagicMock
from services.scraper.reddit import fetch_posts


def _make_response(posts_data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {"children": [{"data": p} for p in posts_data]}
    }
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_fetch_posts_long_script_is_pending_without_gemini():
    """A script already >= TARGET_WORD_COUNT words gets status 'pending' with no Gemini call."""
    long_title = "TIL " + " ".join(["word"] * 30)
    posts_data = [
        {"id": "aaa", "title": long_title, "score": 50_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        with patch("services.scraper.reddit.gemini_elaborate_or_none", return_value=None) as mock_gem:
            posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["status"] == "pending"
    mock_gem.assert_not_called()


def test_fetch_posts_short_script_with_gemini_is_pending():
    """A short script expanded by Gemini gets status 'pending'."""
    posts_data = [
        {"id": "aaa", "title": "TIL that honey never expires.", "score": 50_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    elaboration = "This happens because honey is a natural preservative with low moisture."
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        with patch("services.scraper.reddit.gemini_elaborate_or_none", return_value=elaboration):
            posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["status"] == "pending"
    assert posts[0]["cleaned_script"].startswith("Did you know")
    assert elaboration in posts[0]["cleaned_script"]


def test_fetch_posts_short_script_without_gemini_is_expand_pending():
    """A short script where Gemini fails gets status 'expand_pending' and no elaboration."""
    posts_data = [
        {"id": "bbb", "title": "TIL octopuses have three hearts", "score": 25_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        with patch("services.scraper.reddit.gemini_elaborate_or_none", return_value=None):
            posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["status"] == "expand_pending"
    assert posts[0]["cleaned_script"].startswith("Did you know")


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
    with patch("services.scraper.reddit.requests.get") as mock_get, \
         patch("services.scraper.reddit.gemini_elaborate_or_none", return_value=None):
        mock_get.return_value = _make_response(posts_data)
        posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["reddit_id"] == "bbb"
