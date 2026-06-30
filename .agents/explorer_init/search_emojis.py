import os
import re

# Find all python files in ace/
py_files = []
for root, dirs, files in os.walk("d:\\Projects\\Ace\\ace"):
    if "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            py_files.append(os.path.join(root, file))

# Regex to match emojis (unicode ranges for emojis)
emoji_pattern = re.compile(r"[\U00010000-\U0010ffff\u2600-\u27bf\u2b50]")

out_lines = []
for path in py_files:
    rel_path = os.path.relpath(path, "d:\\Projects\\Ace")
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            matches = emoji_pattern.findall(line)
            if matches:
                clean_line = line.strip()
                out_lines.append(f"  {rel_path}:{i+1} -> {list(set(matches))} in line: {clean_line}")

with open("d:\\Projects\\Ace\\.agents\\explorer_init\\emojis_list.txt", "w", encoding="utf-8") as out:
    out.write("\n".join(out_lines))
print(f"Wrote {len(out_lines)} lines containing emojis to emojis_list.txt")
