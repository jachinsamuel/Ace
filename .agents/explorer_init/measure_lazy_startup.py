import sys
from unittest.mock import MagicMock
import time

# Mock the submodules in sys.modules to simulate lazy loading
sys.modules["ace.core.git_ops"] = MagicMock()
sys.modules["ace.ai.commit_generator"] = MagicMock()
sys.modules["ace.ai.llm_factory"] = MagicMock()
sys.modules["ace.ai.intent_parser"] = MagicMock()
sys.modules["ace.core.safety"] = MagicMock()
sys.modules["ace.ui.prompts"] = MagicMock()

t0 = time.perf_counter()
import ace.cli
t1 = time.perf_counter()

print(f"Startup import time with lazy-loaded modules: {(t1 - t0)*1000:.2f} ms")
