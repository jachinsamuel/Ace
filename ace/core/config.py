import copy
import os
import toml
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG_DIR = Path.home() / ".ace"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "ai": {
        "provider": "nvidia",
        "nvidia_api_key": "",
        "nvidia_model": "meta/llama-3.1-8b-instruct",
        "ollama_model": "qwen2.5-coder:7b",
        "ollama_url": "http://localhost:11434",
        "openai_api_key": "",
        "openai_model": "gpt-4o-mini",
        "anthropic_api_key": "",
        "anthropic_model": "claude-3-5-sonnet-latest",
        "custom_api_key": "",
        "custom_api_base": "",
        "custom_model": "",
        "language": "en",
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
    },
    "aliases": {
        "ship": "git add . && ace commit -y && git push",
        "wip": "git add . && ace commit -f simple",
        "sync": "git pull --rebase && git push",
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
        merged_ai = {**DEFAULT_CONFIG.get("ai", {}), **(data.get("ai") if isinstance(data.get("ai"), dict) else {})}
        merged_commit = {**DEFAULT_CONFIG.get("commit", {}), **(data.get("commit") if isinstance(data.get("commit"), dict) else {})}
        merged_review = {**DEFAULT_CONFIG.get("review", {}), **(data.get("review") if isinstance(data.get("review"), dict) else {})}
        merged_safety = {**DEFAULT_CONFIG.get("safety", {}), **(data.get("safety") if isinstance(data.get("safety"), dict) else {})}

        self.ai = ConfigSection(merged_ai)
        self.commit = ConfigSection(merged_commit)
        self.review = ConfigSection(merged_review)
        self.safety = ConfigSection(merged_safety)
        self.aliases: Dict[str, str] = data.get("aliases", DEFAULT_CONFIG.get("aliases", {})) if isinstance(data.get("aliases"), dict) else DEFAULT_CONFIG.get("aliases", {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai": self.ai.to_dict(),
            "commit": self.commit.to_dict(),
            "review": self.review.to_dict(),
            "safety": self.safety.to_dict(),
            "aliases": self.aliases,
        }

    def get_alias(self, name: str) -> Optional[str]:
        return self.aliases.get(name)

    def set_alias(self, name: str, command: str) -> None:
        self.aliases[name] = command

    def remove_alias(self, name: str) -> bool:
        if name in self.aliases:
            del self.aliases[name]
            return True
        return False

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
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            file_data = toml.load(f)
        
        # Deep merge defaults with file config
        merged = copy.deepcopy(DEFAULT_CONFIG)
        if isinstance(file_data, dict):
            for section, values in file_data.items():
                if section in merged and isinstance(merged[section], dict) and isinstance(values, dict):
                    merged[section].update(values)
                else:
                    merged[section] = values
        return merged
    except Exception:
        return copy.deepcopy(DEFAULT_CONFIG)

def get_config() -> Config:
    """Load configuration with file settings and environment overrides."""
    data = load_config_file()

    # Apply environment variable overrides
    # Provider
    env_provider = os.getenv("ACE_PROVIDER")
    if env_provider:
        data["ai"]["provider"] = env_provider

    # Language
    env_language = os.getenv("ACE_LANGUAGE")
    if env_language:
        data["ai"]["language"] = env_language

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

    # OpenAI API Key & Model
    env_openai_key = os.getenv("OPENAI_API_KEY")
    if env_openai_key:
        data["ai"]["openai_api_key"] = env_openai_key
    env_openai_model = os.getenv("OPENAI_MODEL")
    if env_openai_model:
        data["ai"]["openai_model"] = env_openai_model

    # Anthropic API Key & Model
    env_anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if env_anthropic_key:
        data["ai"]["anthropic_api_key"] = env_anthropic_key
    env_anthropic_model = os.getenv("ANTHROPIC_MODEL")
    if env_anthropic_model:
        data["ai"]["anthropic_model"] = env_anthropic_model

    # Custom API Key, Base, & Model
    env_custom_key = os.getenv("CUSTOM_API_KEY")
    if env_custom_key:
        data["ai"]["custom_api_key"] = env_custom_key
    env_custom_base = os.getenv("CUSTOM_API_BASE")
    if env_custom_base:
        data["ai"]["custom_api_base"] = env_custom_base
    env_custom_model = os.getenv("CUSTOM_MODEL")
    if env_custom_model:
        data["ai"]["custom_model"] = env_custom_model

    return Config(data)

def save_config(config: Config) -> None:
    """Save the current configuration back to ~/.ace/config.toml atomically."""
    import tempfile
    import os
    try:
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=DEFAULT_CONFIG_DIR, prefix="config-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                toml.dump(config.to_dict(), f)
            os.replace(temp_path, DEFAULT_CONFIG_PATH)
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    except Exception as e:
        raise IOError(f"Could not save configuration: {e}")
