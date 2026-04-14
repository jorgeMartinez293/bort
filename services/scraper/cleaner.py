import re

MIN_UPVOTES = 3_000
MAX_WORDS = 150


def clean_til(raw_title: str) -> str:
    """Strip TIL prefix, clean markdown, add hook, truncate to MAX_WORDS."""
    # Remove TIL prefix variants
    text = re.sub(r"^TIL\s+(?:that\b\s*)?", "", raw_title, flags=re.IGNORECASE).strip()
    # Strip markdown links: [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Strip bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Strip leftover markdown
    text = re.sub(r"[*_`]", "", text)
    text = text.strip()
    if not text:
        return ""
    # Capitalize first letter
    text = text[0].upper() + text[1:]
    # Truncate before adding hook
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS]) + "."
    # Add hook
    return f"Did you know that {text[0].lower()}{text[1:]}"


def is_suitable(upvotes: int, reddit_id: str, seen_ids: set) -> bool:
    """Return True if the post should be turned into a video."""
    if upvotes < MIN_UPVOTES:
        return False
    if reddit_id in seen_ids:
        return False
    return True
