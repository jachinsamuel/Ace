import os
import json
import urllib.request
import urllib.error
from langchain_core.language_models import BaseChatModel
from ace.core.config import get_config

class LLMConfigurationError(Exception):
    """Raised when there is a configuration error with the AI provider."""
    pass

_checked_ollama_models = set()

def ensure_ollama_model(base_url: str, model_name: str) -> None:
    """Checks if the configured model is available locally in Ollama; if not, pulls it."""
    cache_key = (base_url, model_name)
    if cache_key in _checked_ollama_models:
        return

    _checked_ollama_models.add(cache_key)

    # 1. Fetch local models list from /api/tags
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            local_models = [m["name"] for m in data.get("models", [])]
            
            norm_model = model_name
            if ":" not in norm_model:
                norm_model = f"{norm_model}:latest"
            
            model_exists = False
            for m in local_models:
                if m == model_name or m == norm_model or m.split(":")[0] == model_name.split(":")[0]:
                    model_exists = True
                    break
                    
            if model_exists:
                return
    except Exception:
        return

    # 2. Prompt user and pull model
    from ace.ui.display import console, spinner, print_warning, print_success, print_error, print_info
    from ace.ui.prompts import confirm
    
    console.print()
    print_warning(f"Ollama model '{model_name}' is not downloaded locally.")
    if confirm(f"Would you like Ace to automatically pull '{model_name}' from the Ollama registry?", default=True):
        try:
            url = f"{base_url.rstrip('/')}/api/pull"
            payload = json.dumps({"name": model_name, "stream": False}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            
            with spinner(f"Downloading model '{model_name}' (this may take a few minutes)..."):
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    if res_data.get("status") == "success" or "success" in str(res_data):
                        print_success(f"Successfully downloaded '{model_name}'!\n")
                    else:
                        print_info(f"Ollama response: {res_data}\n")
        except Exception as e:
            print_error(f"Failed to pull model: {e}")
            print_info(f"Please run 'ollama pull {model_name}' manually in your shell.\n")

def get_llm(offline_override: bool = False) -> BaseChatModel:
    """
    Get the configured LLM client.
    
    If offline_override is True, it will ignore the provider setting and force Ollama.
    """
    config = get_config()
    
    # Determine provider (override if offline requested)
    provider = "ollama" if offline_override else config.ai.provider
    
    if provider == "nvidia":
        api_key = config.ai.nvidia_api_key or os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise LLMConfigurationError(
                "NVIDIA API Key not found. Please set the NVIDIA_API_KEY environment variable "
                "or configure it using 'ace setup'."
            )
            
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(
            model=config.ai.nvidia_model,
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            temperature=0.0,
            max_tokens=2048,
        )
        
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        base_url = config.ai.ollama_url or "http://localhost:11434"
        
        # Pull model if not available
        try:
            ensure_ollama_model(base_url, config.ai.ollama_model)
        except Exception:
            pass
            
        return ChatOllama(
            model=config.ai.ollama_model,
            base_url=base_url,
            temperature=0.0,
            num_predict=2048,
        )
        
    elif provider == "openai":
        api_key = config.ai.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMConfigurationError(
                "OpenAI API Key not found. Please set the OPENAI_API_KEY environment variable "
                "or configure it using 'ace setup'."
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.ai.openai_model or "gpt-4o-mini",
            api_key=api_key,
            temperature=0.0,
            max_tokens=2048,
        )

    elif provider == "anthropic":
        api_key = config.ai.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMConfigurationError(
                "Anthropic API Key not found. Please set the ANTHROPIC_API_KEY environment variable "
                "or configure it using 'ace setup'."
            )
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.ai.anthropic_model or "claude-3-5-sonnet-latest",
            api_key=api_key,
            temperature=0.0,
            max_tokens=2048,
        )

    elif provider == "custom":
        api_key = config.ai.custom_api_key or os.getenv("CUSTOM_API_KEY")
        base_url = config.ai.custom_api_base or os.getenv("CUSTOM_API_BASE")
        model_name = config.ai.custom_model or os.getenv("CUSTOM_MODEL")
        if not base_url:
            raise LLMConfigurationError(
                "Custom API Base URL not found. Please set the CUSTOM_API_BASE environment variable "
                "or configure it using 'ace setup'."
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name or "custom-model",
            api_key=api_key or "no-key",
            base_url=base_url,
            temperature=0.0,
            max_tokens=2048,
        )

    else:
        raise LLMConfigurationError(
            f"Unsupported AI provider: '{provider}'. Supported providers are: nvidia, ollama, openai, anthropic, custom."
        )
