import time
import sys
from unittest.mock import patch, MagicMock

# Make sure ace is in path
sys.path.insert(0, "d:\\Projects\\Ace")

from ace.core.config import Config

mock_config = Config({
    "ai": {
        "provider": "anthropic",
        "anthropic_api_key": "anthropic-key-test",
        "anthropic_model": "claude-3-5-sonnet-latest",
    }
})

print("Profiling test_get_llm_anthropic steps:")

t0 = time.perf_counter()
import langchain_anthropic
print(f"1. import langchain_anthropic: {(time.perf_counter() - t0)*1000:.2f} ms")

t0 = time.perf_counter()
from ace.ai.llm_factory import get_llm
print(f"2. import get_llm: {(time.perf_counter() - t0)*1000:.2f} ms")

t0 = time.perf_counter()
with patch("ace.ai.llm_factory.get_config", return_value=mock_config):
    print(f"3. patch get_config setup: {(time.perf_counter() - t0)*1000:.2f} ms")
    
    t0_patch = time.perf_counter()
    with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
        print(f"4. patch ChatAnthropic setup: {(time.perf_counter() - t0_patch)*1000:.2f} ms")
        
        t0_call = time.perf_counter()
        res = get_llm()
        print(f"5. get_llm() call: {(time.perf_counter() - t0_call)*1000:.2f} ms")
