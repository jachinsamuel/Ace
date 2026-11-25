import json
import re
from typing import Dict, Any

class JSONExtractError(Exception):
    """Raised when JSON extraction fails."""

def extract_json(text: str) -> Any:
    """
    Extract and parse a JSON object or array from a string, handling optional markdown code blocks.
    
    Raises JSONExtractError if parsing fails.
    """
    cleaned = text.strip()
    
    # 1. Search for markdown code block anywhere in response
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Use JSONDecoder.raw_decode starting from each '{' or '[' so nested JSON
        # objects/arrays with surrounding prose parse accurately.
        decoder = json.JSONDecoder()
        for idx, ch in enumerate(cleaned):
            if ch in ("{", "["):
                try:
                    obj, _ = decoder.raw_decode(cleaned[idx:])
                    return obj
                except json.JSONDecodeError:
                    continue

        raise JSONExtractError(f"Could not parse response as JSON. Raw text:\n{text}")
