import os
import toml
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_DIR = Path.home() / ".ace"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "ai": {
        "provider": "nvidia",
        "nvidia_api_key": "",
        "nvidia_model": "meta/llama-3.3-70b-instruct",
        "ollama_model": "qwen2.5-coder:7b",
        "ollama_url": "http://localhost:11434",
    },
    "commit": {
        "format": "conventional",
        "sign": False,
        "emoji": True,
    },
    "review": {
        "severity": "medium",
    },
    "safety": {
        "confirm_destructive": True,
        "auto_stash": True,
    }
}

class ConfigSection:
    def __init__(self, data: Dict[str, Any]):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, ConfigSection):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result

class Config:
    def __init__(self, data: Dict[str, Any]):
        self.ai = ConfigSection(data.get("ai", {}))
        self.commit = ConfigSection(data.get("commit", {}))
        self.review = ConfigSection(data.get("review", {}))
        self.safety = ConfigSection(data.get("safety", {}))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai": self.ai.to_dict(),
            "commit": self.commit.to_dict(),
            "review": self.review.to_dict(),
            "safety": self.safety.to_dict(),
        }

def load_config_file() -> Dict[str, Any]:
    """Load config from ~/.ace/config.toml, creating it with defaults if it doesn't exist."""
    if not DEFAULT_CONFIG_PATH.exists():
        try:
            DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
                toml.dump(DEFAULT_CONFIG, f)
        except Exception:
            # Silently fallback if unable to write config (e.g. read-only system)
            pass
        return DEFAULT_CONFIG.copy()

    try:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            file_data = toml.load(f)
        
        # Deep merge defaults with file config
        merged = DEFAULT_CONFIG.copy()
        for section, values in file_data.items():
            if section in merged and isinstance(merged[section], dict) and isinstance(values, dict):
                merged[section] = {**merged[section], **values}
            else:
                merged[section] = values
        return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

def get_config() -> Config:
    """Load configuration with file settings and environment overrides."""
    data = load_config_file()

    # Apply environment variable overrides
    # Provider
    env_provider = os.getenv("ACE_PROVIDER")
    if env_provider:
        data["ai"]["provider"] = env_provider

    # Nvidia API Key
    env_nvidia_key = os.getenv("NVIDIA_API_KEY")
    if env_nvidia_key:
        data["ai"]["nvidia_api_key"] = env_nvidia_key

    # Nvidia Model
    env_nvidia_model = os.getenv("NVIDIA_MODEL")
    if env_nvidia_model:
        data["ai"]["nvidia_model"] = env_nvidia_model

    # Ollama Model
    env_ollama_model = os.getenv("OLLAMA_MODEL")
    if env_ollama_model:
        data["ai"]["ollama_model"] = env_ollama_model

    # Ollama URL
    env_ollama_url = os.getenv("OLLAMA_URL")
    if env_ollama_url:
        data["ai"]["ollama_url"] = env_ollama_url

    return Config(data)

def save_config(config: Config) -> None:
    """Save the current configuration back to ~/.ace/config.toml."""
    try:
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
            toml.dump(config.to_dict(), f)
    except Exception as e:
        raise IOError(f"Could not save configuration: {e}")
