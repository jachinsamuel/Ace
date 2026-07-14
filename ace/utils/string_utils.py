import re

def strip_emojis(text: str) -> str:
    """
    Strip Unicode emojis from text to keep the terminal UI clean.
    """
    if not text:
        return text

    # Unicode emoji ranges:
    # - \U0001f600-\U0001f64f (emoticons)
    # - \U0001f300-\U0001f5ff (symbols & pictographs)
    # - \U0001f680-\U0001f6ff (transport & map symbols)
    # - \U0001f1e0-\U0001f1ff (flags)
    # - \U00002700-\U000027bf (dingbats)
    # - \U00002600-\U000026ff (miscellaneous symbols)
    # - \U0001f900-\U0001f9ff (supplemental symbols)
    # - \U0001fa00-\U0001faff (symbols and pictographs extended)
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"
        "\U0001f300-\U0001f5ff"
        "\U0001f680-\U0001f6ff"
        "\U0001f1e0-\U0001f1ff"
        "\U00002700-\U000027bf"
        "\U00002600-\U000026ff"
        "\U0001f900-\U0001f9ff"
        "\U0001fa00-\U0001faff"
        "]+",
        re.UNICODE
    )

    cleaned = emoji_pattern.sub("", text)
    # Replace multiple spaces/newlines with a single space (while preserving newlines if multi-line)
    # To be safe for markdown summaries, we can just strip emojis and keep other formatting intact.
    # Let's do a simple strip of double spaces that result from removing the emoji.
    cleaned = re.sub(r' +', ' ', cleaned)
    # Also clean up trailing/leading spaces on lines
    lines = [line.strip() for line in cleaned.splitlines()]
    return "\n".join(lines).strip()
