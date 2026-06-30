with open("d:\\Projects\\Ace\\ace\\cli.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if "banner" in line:
            print(f"Line {i+1}: {line.strip()}")
