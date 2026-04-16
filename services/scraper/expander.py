"""Script expander — lengthens narration scripts to TARGET_WORD_COUNT words.

Two strategies, tried in order:
1. Gemini Flash (free tier) — if GEMINI_API_KEY is set
2. Keyword-based templates — always available, zero dependencies

Both are completely free.  The Anthropic path has been intentionally removed.
"""
import os
import random
import logging
from typing import Optional

log = logging.getLogger(__name__)

# ~12 s at Piper lessac-medium's ~2.5 words-per-second pace
TARGET_WORD_COUNT = 30

# ---------------------------------------------------------------------------
# Template bank — keyword → list[elaboration sentence]
# ---------------------------------------------------------------------------
_TEMPLATES: dict = {
    "animal": [
        "Animals have evolved some of the most remarkable survival strategies on Earth.",
    ],
    "body": [
        "The human body is one of the most complex systems in the known universe.",
    ],
    "space": [
        "The universe is stranger and more vast than we can possibly imagine.",
    ],
    "history": [
        "History is full of facts that most of us were never taught in school.",
    ],
    "food": [
        "Food science reveals some of the most unexpected facts about everyday life.",
    ],
    "math": [
        "Mathematics hides some of the most mind-bending patterns in existence.",
    ],
    "default": [
        "The world is full of surprising facts most people never get to hear.",
        "This is just one of countless fascinating things about our planet.",
        "Science keeps showing us that reality is stranger than fiction.",
        "Most people go their entire lives without ever hearing this.",
    ],
}

_KEYWORDS: dict = {
    "animal": [
        "animal", "species", "fish", "bee", "bird", "cat", "dog", "spider",
        "whale", "dolphin", "lion", "wolf", "snake", "insect", "mammal",
        "reptile", "frog", "shark", "octopus", "elephant",
    ],
    "body": [
        "brain", "heart", "body", "blood", "nerve", "muscle", "bone",
        "organ", "cell", "dna", "gene", "skin", "lung", "human",
    ],
    "space": [
        "planet", "star", "universe", "galaxy", "solar", "nasa", "space",
        "moon", "asteroid", "comet", "orbit", "cosmos", "telescope",
    ],
    "history": [
        "ancient", "century", "year", "empire", "war", "roman", "egypt",
        "medieval", "king", "queen", "pharaoh", "civilization", "history",
    ],
    "food": [
        "food", "water", "honey", "salt", "sugar", "coffee", "bread",
        "fruit", "vegetable", "eat", "drink", "cook",
    ],
    "math": [
        "number", "math", "prime", "infinite", "calculation", "percent",
        "probability", "equation", "geometry",
    ],
}


def _pick_template(script: str) -> str:
    lower = script.lower()
    for category, keywords in _KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return random.choice(_TEMPLATES[category])
    return random.choice(_TEMPLATES["default"])


# ---------------------------------------------------------------------------
# Optional Gemini path (free tier: gemini-flash, 15 RPM, 1 M tokens/day)
# ---------------------------------------------------------------------------
_gemini_client = None
_gemini_ready = False


def _get_gemini():
    global _gemini_client, _gemini_ready
    if not _gemini_ready:
        _gemini_ready = True
        if not os.environ.get("GEMINI_API_KEY"):
            return None
        try:
            from google import genai  # type: ignore[import]
            _gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        except Exception as e:
            log.warning(f"Could not initialise Gemini client: {e}")
    return _gemini_client


_GEMINI_PROMPT = (
    "You write narration for short viral videos. "
    "Given this fact, output TWO elaboration sentences (30-50 words total) "
    "that explain or expand on the fact in an engaging way. "
    "The first sentence must start with one of: 'The reason for this is', "
    "'This happens because', 'Interestingly', or 'Scientists believe'. "
    "Output ONLY those two sentences, no quotes, no extra text.\n\nFact: {script}"
)


def _gemini_elaborate(script: str) -> Optional[str]:
    client = _get_gemini()
    if client is None:
        return None
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=_GEMINI_PROMPT.format(script=script),
        )
        text = response.text.strip()
        if text and 10 <= len(text.split()) <= 60:
            if not text.endswith("."):
                text += "."
            return text
    except Exception as e:
        log.warning(f"Gemini expansion failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def expand_script(script: str) -> str:
    """Append an elaboration sentence to *script* to reach TARGET_WORD_COUNT.

    Strategy (in order):
    1. Gemini Flash free tier — if GEMINI_API_KEY env var is set
    2. Keyword-based template — always available, zero cost

    Returns *script* unchanged if it is already >= TARGET_WORD_COUNT words.
    """
    if not script or len(script.split()) >= TARGET_WORD_COUNT:
        return script

    elaboration = _gemini_elaborate(script) or _pick_template(script)
    base = script.rstrip()
    if base and base[-1] not in ".!?":
        base += "."
    return f"{base} {elaboration}"
