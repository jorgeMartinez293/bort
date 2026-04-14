from services.scraper.cleaner import clean_til, is_suitable

def test_strips_til_prefix():
    result = clean_til("TIL that honey never expires.")
    assert not result.startswith("TIL")
    assert "honey never expires" in result

def test_strips_til_without_that():
    result = clean_til("TIL honey bees can recognize human faces.")
    assert not result.startswith("TIL")

def test_adds_hook_prefix():
    result = clean_til("TIL that octopuses have three hearts.")
    assert result.startswith("Did you know")

def test_strips_markdown_links():
    result = clean_til("TIL that [Wikipedia](https://en.wikipedia.org) exists.")
    assert "https://" not in result
    assert "[Wikipedia]" not in result

def test_is_suitable_passes_high_upvote_novel_post():
    assert is_suitable(upvotes=5000, reddit_id="abc123", seen_ids=set()) is True

def test_is_suitable_rejects_low_upvotes():
    assert is_suitable(upvotes=100, reddit_id="abc123", seen_ids=set()) is False

def test_is_suitable_rejects_duplicate():
    assert is_suitable(upvotes=10000, reddit_id="abc123", seen_ids={"abc123"}) is False

def test_script_max_length():
    long_text = "word " * 200
    result = clean_til("TIL that " + long_text)
    assert len(result.split()) <= 154  # 150 content words + 4 hook words

def test_strips_bare_urls():
    result = clean_til("TIL that check this out https://example.com for more")
    assert "https://" not in result

def test_is_suitable_boundary():
    assert is_suitable(upvotes=2999, reddit_id="x", seen_ids=set()) is False
    assert is_suitable(upvotes=3000, reddit_id="x", seen_ids=set()) is True

def test_empty_text_after_stripping():
    result = clean_til("TIL https://example.com")
    assert result == ""
