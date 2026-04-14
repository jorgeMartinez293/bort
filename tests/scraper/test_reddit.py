from unittest.mock import MagicMock, patch
from services.scraper.reddit import fetch_posts

def _make_post(id_, title, score):
    p = MagicMock()
    p.id = id_
    p.title = title
    p.score = score
    p.subreddit.display_name = "todayilearned"
    return p

def test_fetch_posts_returns_cleaned_list():
    mock_sub = MagicMock()
    mock_sub.hot.return_value = [
        _make_post("aaa", "TIL that honey never expires.", 50_000),
        _make_post("bbb", "TIL octopuses have three hearts", 25_000),
    ]
    with patch("services.scraper.reddit.praw.Reddit") as MockReddit:
        MockReddit.return_value.subreddit.return_value = mock_sub
        posts = fetch_posts(
            subreddit="todayilearned",
            limit=10,
            seen_ids=set(),
            client_id="x", client_secret="y", user_agent="test"
        )
    assert len(posts) == 2
    assert posts[0]["reddit_id"] == "aaa"
    assert posts[0]["cleaned_script"].startswith("Did you know")
    assert posts[0]["upvotes"] == 50_000

def test_fetch_posts_skips_seen_ids():
    mock_sub = MagicMock()
    mock_sub.hot.return_value = [
        _make_post("aaa", "TIL that honey never expires.", 50_000),
    ]
    with patch("services.scraper.reddit.praw.Reddit") as MockReddit:
        MockReddit.return_value.subreddit.return_value = mock_sub
        posts = fetch_posts(
            subreddit="todayilearned", limit=10,
            seen_ids={"aaa"},
            client_id="x", client_secret="y", user_agent="test"
        )
    assert posts == []
