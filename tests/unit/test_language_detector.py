"""Tests for language detection."""

import pytest

from app.multilingual.detector import detect_language, get_language_name


class TestLanguageDetection:
    """Tests for language detection utilities."""

    def test_detect_english(self):
        """Test detecting English text."""
        result = detect_language("This is a beautiful sunset over the ocean")

        assert result.code == "en"
        assert result.name == "English"
        assert result.is_english is True
        assert result.confidence > 0.8

    def test_detect_chinese(self):
        """Test detecting Chinese text."""
        result = detect_language("海上美丽的日落")

        assert result.code in ["zh-cn", "zh-tw", "zh"]
        assert "Chinese" in result.name
        assert result.is_english is False
        assert result.confidence > 0.8

    def test_detect_spanish(self):
        """Test detecting Spanish text."""
        result = detect_language("Una hermosa puesta de sol sobre el océano")

        assert result.code == "es"
        assert result.name == "Spanish"
        assert result.is_english is False

    def test_detect_japanese(self):
        """Test detecting Japanese text."""
        result = detect_language("海の上の美しい夕日")

        assert result.code == "ja"
        assert result.name == "Japanese"
        assert result.is_english is False

    def test_detect_empty_string(self):
        """Test detection with empty string defaults to English."""
        result = detect_language("")

        assert result.code == "en"
        assert result.confidence == 0.0

    def test_detect_short_text(self):
        """Test detection with very short text."""
        result = detect_language("hi")

        # Short text detection is unreliable, but should not error
        assert result.code is not None
        assert result.name is not None

    def test_get_language_name(self):
        """Test language name lookup."""
        assert get_language_name("en") == "English"
        assert get_language_name("zh-cn") == "Chinese (Simplified)"
        assert get_language_name("es") == "Spanish"
        assert get_language_name("unknown") == "UNKNOWN"
