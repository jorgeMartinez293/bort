# tests/scraper/test_expander.py
import os
from unittest.mock import patch
from services.scraper.expander import gemini_available, gemini_elaborate_or_none

def test_gemini_available_false_when_no_key():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GEMINI_API_KEY", None)
        assert gemini_available() is False

def test_gemini_available_true_when_key_set():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        assert gemini_available() is True

def test_gemini_elaborate_or_none_returns_none_when_no_key():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GEMINI_API_KEY", None)
        result = gemini_elaborate_or_none("Honey never expires.")
        assert result is None
