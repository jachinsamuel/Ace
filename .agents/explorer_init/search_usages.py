with open("d:\\Projects\\Ace\\ace\\cli.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    line_num = i + 1
    # look for classes/functions being called/referenced
    for name in ["CommitGenerator", "IntentParser", "get_llm", "GitOps", "SafetyChecker"]:
        if name in line and "import" not in line:
            print(f"Line {line_num:4d}: {line.strip()}")
