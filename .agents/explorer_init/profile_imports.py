import time
import sys

def profile_import(module_name):
    t0 = time.perf_counter()
    __import__(module_name)
    t1 = time.perf_counter()
    return (t1 - t0) * 1000  # in ms

modules_to_test = [
    "typer",
    "click",
    "rich",
    "git",
    "langchain",
    "langchain_nvidia_ai_endpoints",
    "langchain_ollama",
    "langchain_openai",
    "langchain_anthropic",
    "dotenv",
    "toml"
]

print("Import times for top-level packages:")
for mod in modules_to_test:
    try:
        duration = profile_import(mod)
        print(f"  {mod}: {duration:.2f} ms")
    except Exception as e:
        print(f"  {mod}: Failed ({e})")

# Let's test ace submodules
ace_submodules = [
    "ace.core.config",
    "ace.core.git_ops",
    "ace.ai.commit_generator",
    "ace.ai.llm_factory",
    "ace.ai.intent_parser",
    "ace.core.safety",
    "ace.ui.display",
    "ace.ui.prompts"
]

print("\nImport times for ace submodules:")
# To measure individual import times of ace submodules (including their dependencies if not loaded)
# We will do it in a fresh interpreter or just clear sys.modules.
# But clearing sys.modules is tricky because of transitive imports. Let's run it anyway.
for mod in ace_submodules:
    t0 = time.perf_counter()
    try:
        __import__(mod)
        duration = (time.perf_counter() - t0) * 1000
        print(f"  {mod}: {duration:.2f} ms")
    except Exception as e:
        print(f"  {mod}: Failed ({e})")
