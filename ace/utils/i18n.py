"""i18n utilities and localization support for Ace CLI."""

from typing import Dict

SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "zh": "Simplified Chinese (简体中文)",
    "zh-CN": "Simplified Chinese (简体中文)",
    "zh-TW": "Traditional Chinese (繁體中文)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "ru": "Russian (Русский)",
    "hi": "Hindi (हिन्दी)",
}

def normalize_language_code(code: str) -> str:
    """Normalize language code string."""
    if not code:
        return "en"
    clean = code.strip().lower()
    if clean in ("zh", "zh-cn", "cn", "chinese"):
        return "zh-CN"
    if clean in ("zh-tw", "tw"):
        return "zh-TW"
    return clean

def get_language_name(code: str) -> str:
    """Get human-readable language name from code."""
    norm = normalize_language_code(code)
    return SUPPORTED_LANGUAGES.get(norm, code.upper() if code else "English")

def get_language_instruction(code: str) -> str:
    """
    Returns an explicit system prompt instruction for the specified language.
    If the language is English, returns an empty string.
    """
    norm = normalize_language_code(code)
    if norm == "en":
        return ""
    
    lang_name = get_language_name(norm)
    return (
        f"\n\nIMPORTANT LANGUAGE DIRECTIVE:\n"
        f"You MUST generate all response content, messages, comments, descriptions, and explanations in {lang_name}. "
        f"Keep technical variable names, git command keywords, and code syntax intact in English."
    )
