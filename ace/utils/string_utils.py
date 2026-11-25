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

    leading_emoji_re = re.compile(r"^\s*" + emoji_pattern.pattern)
    lines = []
    for raw_line in text.splitlines():
        had_leading_emoji = bool(leading_emoji_re.match(raw_line))
        cleaned_line = emoji_pattern.sub("", raw_line)
        # Collapse multiple inline spaces after stripping emojis while keeping leading indentation intact
        if had_leading_emoji or not raw_line.startswith((" ", "\t")):
            cleaned_line = re.sub(r" +", " ", cleaned_line).strip()
        else:
            indent_match = re.match(r"^([ \t]*)(.*)$", cleaned_line)
            if indent_match:
                indent, rest = indent_match.groups()
                cleaned_line = indent + re.sub(r" +", " ", rest).strip()
            else:
                cleaned_line = cleaned_line.rstrip()
        lines.append(cleaned_line)
    return "\n".join(lines).strip()
