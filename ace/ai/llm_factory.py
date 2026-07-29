from typing import Optional
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
            payload = json.dumps({"name": model_name, "stream": True}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            
            with spinner(f"Initiating download of model '{model_name}'..."):
                pass
            
            with urllib.request.urlopen(req, timeout=60) as response:
                import sys
                for line in response:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line.decode("utf-8"))
                        status = data.get("status", "")
                        completed = data.get("completed", 0)
                        total = data.get("total", 0)
                        if total > 0:
                            pct = (completed / total) * 100
                            sys.stdout.write(f"\r\033[K[Ollama] {status} ({pct:.1f}%)")
                            sys.stdout.flush()
                        else:
                            sys.stdout.write(f"\r\033[K[Ollama] {status}")
                            sys.stdout.flush()
                    except Exception:
                        pass
                sys.stdout.write("\n")
                sys.stdout.flush()
            print_success(f"Successfully downloaded '{model_name}'!\n")
        except Exception as e:
            print_error(f"Failed to pull model: {e}")
            print_info(f"Please run 'ollama pull {model_name}' manually in your shell.\n")

def _get_ollama_llm(config) -> BaseChatModel:
    from langchain_ollama import ChatOllama
    base_url = config.ai.ollama_url or "http://localhost:11434"
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

class DummyMissingKeyLLM:
    def __init__(self, provider: str, error_msg: str):
        self.provider = provider
        self.error_msg = error_msg

    def invoke(self, input_data, config=None, **kwargs):
        raise LLMConfigurationError(self.error_msg)

class HeuristicFallbackResponse:
    def __init__(self, content: str):
        self.content = content

class FallbackChatModel:
    """Wrapper that attempts primary online LLM invocation, falls back to local Ollama, and finally smart heuristics."""
    def __init__(self, primary_llm: BaseChatModel, fallback_llm: Optional[BaseChatModel] = None):
        self.primary_llm = primary_llm
        self.fallback_llm = fallback_llm

    def invoke(self, input_data, config=None, **kwargs):
        try:
            return self.primary_llm.invoke(input_data, config=config, **kwargs)
        except Exception as primary_err:
            if self.fallback_llm and self.fallback_llm != self.primary_llm:
                from ace.ui.display import print_warning
                print_warning(f"Online AI provider failed ({primary_err}). Automatically falling back to local Ollama...")
                try:
                    return self.fallback_llm.invoke(input_data, config=config, **kwargs)
                except Exception:
                    print_warning("Local Ollama service unavailable. Using Smart Heuristic Fallback...")
                    return self._generate_heuristic_response(input_data)
            
            from ace.ui.display import print_warning
            print_warning(f"Online AI provider failed ({primary_err}). Using Smart Heuristic Fallback...")
            return self._generate_heuristic_response(input_data)

    def _generate_heuristic_response(self, input_data) -> HeuristicFallbackResponse:
        user_text = ""
        if isinstance(input_data, list):
            for msg in input_data:
                if hasattr(msg, "content"):
                    user_text += str(msg.content) + "\n"
        else:
            user_text = str(input_data)
            
        user_lower = user_text.lower()
        
        # 1. Intent Parsing
        if "translate this request into git commands" in user_lower or "risk_level" in user_lower:
            if "commit" in user_lower and "add" in user_lower:
                json_str = '{"commands": ["git add .", "ace commit"], "explanation": "Stage all changes and run smart commit.", "risk_level": "moderate", "alternatives": null}'
            elif "push" in user_lower:
                json_str = '{"commands": ["git push"], "explanation": "Push local commits to remote.", "risk_level": "moderate", "alternatives": null}'
            elif "status" in user_lower:
                json_str = '{"commands": ["git status"], "explanation": "Display working tree status.", "risk_level": "safe", "alternatives": null}'
            elif "log" in user_lower or "history" in user_lower:
                json_str = '{"commands": ["git log --oneline -n 10"], "explanation": "Display recent commit history.", "risk_level": "safe", "alternatives": null}'
            elif "undo" in user_lower or "reset" in user_lower:
                json_str = '{"commands": ["git reset --soft HEAD~1"], "explanation": "Undo last commit, keeping changes staged.", "risk_level": "moderate", "alternatives": null}'
            else:
                json_str = '{"commands": ["git add ."], "explanation": "Stage working directory changes.", "risk_level": "moderate", "alternatives": null}'
            return HeuristicFallbackResponse(json_str)
            
        # 2. Commit Message Generation
        if "conventional_commit" in user_lower or "staged changes" in user_lower or "diff" in user_lower:
            if "readme" in user_lower or "docs" in user_lower or ".md" in user_lower:
                commit_msg = "docs: update documentation and project readme"
            elif "test" in user_lower or "tests/" in user_lower:
                commit_msg = "test: add and update test suite coverage"
            elif "pyproject.toml" in user_lower or "package.json" in user_lower:
                commit_msg = "chore(deps): update project dependencies and metadata"
            else:
                commit_msg = "feat: update staged project files"
            return HeuristicFallbackResponse(commit_msg)

        return HeuristicFallbackResponse("feat: update project files")


def get_llm(offline_override: bool = False) -> BaseChatModel:
    """
    Get the configured LLM client.
    
    If offline_override is True, it will ignore the provider setting and force Ollama.
    When using an online provider, it automatically wraps the client in a FallbackChatModel
    to gracefully fall back to local Ollama if network connection or API calls fail.
    """
    config = get_config()
    
    # Determine provider (override if offline requested)
    provider = "ollama" if offline_override else config.ai.provider
    
    if provider == "ollama":
        return _get_ollama_llm(config)

    # Build primary LLM
    primary_llm = None
    if provider == "nvidia":
        api_key = config.ai.nvidia_api_key or os.getenv("NVIDIA_API_KEY")
        if not api_key:
            primary_llm = DummyMissingKeyLLM("nvidia", "NVIDIA API Key not found. Please set NVIDIA_API_KEY or run 'ace setup'.")
        else:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            primary_llm = ChatNVIDIA(
                model=config.ai.nvidia_model,
                api_key=api_key,
                base_url="https://integrate.api.nvidia.com/v1",
                temperature=0.0,
                max_tokens=2048,
            )
        
    elif provider == "openai":
        api_key = config.ai.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            primary_llm = DummyMissingKeyLLM("openai", "OpenAI API Key not found. Please set OPENAI_API_KEY or run 'ace setup'.")
        else:
            from langchain_openai import ChatOpenAI
            primary_llm = ChatOpenAI(
                model=config.ai.openai_model or "gpt-4o-mini",
                api_key=api_key,
                temperature=0.0,
                max_tokens=2048,
            )

    elif provider == "anthropic":
        api_key = config.ai.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            primary_llm = DummyMissingKeyLLM("anthropic", "Anthropic API Key not found. Please set ANTHROPIC_API_KEY or run 'ace setup'.")
        else:
            from langchain_anthropic import ChatAnthropic
            primary_llm = ChatAnthropic(
                model=config.ai.anthropic_model or "claude-3-5-sonnet-latest",
                api_key=api_key,
                temperature=0.0,
                max_tokens=2048,
            )

    elif provider in ("google", "gemini"):
        api_key = getattr(config.ai, "google_api_key", None) or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            primary_llm = DummyMissingKeyLLM(provider, "Google/Gemini API Key not found. Please set GOOGLE_API_KEY or GEMINI_API_KEY.")
        else:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                model_name = getattr(config.ai, "google_model", None) or "gemini-1.5-flash"
                primary_llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=api_key,
                    temperature=0.0,
                    max_output_tokens=2048,
                )
            except ImportError:
                primary_llm = DummyMissingKeyLLM(provider, "langchain-google-genai is not installed. Run 'pip install langchain-google-genai'.")

    elif provider == "custom":
        api_key = config.ai.custom_api_key or os.getenv("CUSTOM_API_KEY")
        base_url = config.ai.custom_api_base or os.getenv("CUSTOM_API_BASE")
        model_name = config.ai.custom_model or os.getenv("CUSTOM_MODEL")
        if not base_url:
            primary_llm = DummyMissingKeyLLM("custom", "Custom API Base URL not found. Please set CUSTOM_API_BASE or run 'ace setup'.")
        else:
            from langchain_openai import ChatOpenAI
            primary_llm = ChatOpenAI(
                model=model_name or "custom-model",
                api_key=api_key or "no-key",
                base_url=base_url,
                temperature=0.0,
                max_tokens=2048,
            )
    else:
        primary_llm = DummyMissingKeyLLM(provider, f"Unsupported AI provider: '{provider}'.")

    # Attempt to construct local Ollama fallback LLM
    fallback_llm = None
    try:
        fallback_llm = _get_ollama_llm(config)
    except Exception:
        pass

    return FallbackChatModel(primary_llm=primary_llm, fallback_llm=fallback_llm)

