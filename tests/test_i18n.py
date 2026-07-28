import pytest
from ace.utils.i18n import (
    normalize_language_code,
    get_language_name,
    get_language_instruction,
)
from ace.core.config import Config

def test_normalize_language_code():
    assert normalize_language_code("en") == "en"
    assert normalize_language_code("zh") == "zh-CN"
    assert normalize_language_code("zh-cn") == "zh-CN"
    assert normalize_language_code("chinese") == "zh-CN"
    assert normalize_language_code("zh-tw") == "zh-TW"
    assert normalize_language_code("es") == "es"
    assert normalize_language_code("") == "en"

def test_get_language_name():
    assert get_language_name("en") == "English"
    assert "Simplified Chinese" in get_language_name("zh-CN")
    assert "Spanish" in get_language_name("es")
    assert "Hindi" in get_language_name("hi")
    assert get_language_name("custom_lang") == "CUSTOM_LANG"

def test_get_language_instruction():
    # English returns empty directive
    assert get_language_instruction("en") == ""
    
    # Non-English returns directive with language name
    instruction_zh = get_language_instruction("zh-CN")
    assert "IMPORTANT LANGUAGE DIRECTIVE" in instruction_zh
    assert "Simplified Chinese" in instruction_zh
    
    instruction_es = get_language_instruction("es")
    assert "Spanish" in instruction_es

def test_config_language_default_and_override():
    config = Config({"ai": {"provider": "nvidia"}})
    assert hasattr(config.ai, "language")
    assert config.ai.language == "en"
    
    config_zh = Config({"ai": {"provider": "ollama", "language": "zh-CN"}})
    assert config_zh.ai.language == "zh-CN"
