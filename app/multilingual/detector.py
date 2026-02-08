"""Language detection utilities."""

from langdetect import DetectorFactory, detect, detect_langs
from langdetect.lang_detect_exception import LangDetectException

from app.models.query import LanguageInfo
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Make langdetect deterministic
DetectorFactory.seed = 0

# Language code to name mapping
LANGUAGE_NAMES: dict[str, str] = {
    "af": "Afrikaans",
    "ar": "Arabic",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "fa": "Persian",
    "fi": "Finnish",
    "fr": "French",
    "gu": "Gujarati",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "ko": "Korean",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mr": "Marathi",
    "ne": "Nepali",
    "nl": "Dutch",
    "no": "Norwegian",
    "pa": "Punjabi",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "so": "Somali",
    "sq": "Albanian",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tl": "Tagalog",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
}


def detect_language(text: str) -> LanguageInfo:
    """Detect the language of input text.

    Args:
        text: Input text to analyze

    Returns:
        LanguageInfo with detection results
    """
    # Clean text for detection
    clean_text = text.strip()

    if not clean_text:
        return LanguageInfo(
            code="en",
            name="English",
            confidence=0.0,
            is_english=True,
        )

    try:
        # Get detection with probabilities
        lang_probs = detect_langs(clean_text)

        if not lang_probs:
            raise LangDetectException(0, "No language detected")

        # Get top detection
        top_lang = lang_probs[0]
        lang_code = top_lang.lang
        confidence = top_lang.prob

        # Normalize Chinese codes
        if lang_code == "zh-cn" or lang_code == "zh-tw":
            pass  # Keep as is
        elif lang_code == "zh":
            lang_code = "zh-cn"

        # Get language name
        lang_name = LANGUAGE_NAMES.get(lang_code, lang_code.upper())

        return LanguageInfo(
            code=lang_code,
            name=lang_name,
            confidence=confidence,
            is_english=(lang_code == "en"),
        )

    except LangDetectException as e:
        logger.warning("language_detection_failed", error=str(e), text=text[:50])
        # Default to English on failure
        return LanguageInfo(
            code="en",
            name="English",
            confidence=0.5,
            is_english=True,
        )


def detect_language_simple(text: str) -> str:
    """Simple language detection returning just the code.

    Args:
        text: Input text

    Returns:
        ISO 639-1 language code
    """
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def get_language_name(code: str) -> str:
    """Get language name from code.

    Args:
        code: ISO 639-1 language code

    Returns:
        Language name in English
    """
    return LANGUAGE_NAMES.get(code, code.upper())
