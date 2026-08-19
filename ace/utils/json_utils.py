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
        # Try to find a JSON object {...} or JSON array [...] substring
        obj_match = re.search(r"(\{.*?\})", cleaned, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except json.JSONDecodeError:
                pass
        
        arr_match = re.search(r"(\[.*?\])", cleaned, re.DOTALL)
        if arr_match:
            try:
                return json.loads(arr_match.group(1))
            except json.JSONDecodeError:
                pass

        raise JSONExtractError(f"Could not parse response as JSON. Raw text:\n{text}")
