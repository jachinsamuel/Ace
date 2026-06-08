import os
from langchain_core.language_models import BaseChatModel
from ace.core.config import get_config

class LLMConfigurationError(Exception):
    """Raised when there is a configuration error with the AI provider."""
    pass

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
        return ChatOllama(
            model=config.ai.ollama_model,
            base_url=base_url,
            temperature=0.0,
            num_predict=2048,
        )
        
    else:
        raise LLMConfigurationError(
            f"Unsupported AI provider: '{provider}'. Supported providers are 'nvidia' and 'ollama'."
        )
