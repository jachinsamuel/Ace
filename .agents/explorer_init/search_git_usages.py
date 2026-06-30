with open("d:\\Projects\\Ace\\ace\\core\\git_ops.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if "git." in line and "import" not in line:
            print(f"Line {i+1}: {line.strip()}")
