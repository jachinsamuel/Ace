from ace.utils.string_utils import strip_emojis

def test_strip_emojis():
    # Test cases with different kinds of emojis and text
    assert strip_emojis("🎨 style(ui): update hover effects") == "style(ui): update hover effects"
    assert strip_emojis("🚀 feat(app): implement loader") == "feat(app): implement loader"
    assert strip_emojis("🤖 feat: implement robot") == "feat: implement robot"
    assert strip_emojis("📝 docs: update readme") == "docs: update readme"
    assert strip_emojis("Normal message without emoji") == "Normal message without emoji"
    assert strip_emojis("Multiple emojis 🎨 🚀 test") == "Multiple emojis test"
    assert strip_emojis("") == ""
    assert strip_emojis(None) is None

    # Test multi-line text
    multi_line = "🎨 First line\n🚀 Second line"
    expected = "First line\nSecond line"
    assert strip_emojis(multi_line) == expected
