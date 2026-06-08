import json
import re
from typing import Dict, Any

class JSONExtractError(Exception):
    """Raised when JSON extraction fails."""
    pass

def extract_json(text: str) -> Dict[str, Any]:
    """
    Extract and parse a JSON object from a string, handling optional markdown code blocks.
    
    Raises JSONExtractError if parsing fails.
    """
    cleaned = text.strip()
    
    # Remove markdown code block wrappers
    if cleaned.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        else:
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find a JSON-like substring between { and }
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        raise JSONExtractError(f"Could not parse response as JSON. Raw text:\n{text}")
