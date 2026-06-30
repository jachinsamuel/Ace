import os
import re

# Find all python files in ace/
ace_files = []
for root, dirs, files in os.walk("d:\\Projects\\Ace\\ace"):
    if "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            rel_path = os.path.relpath(os.path.join(root, file), "d:\\Projects\\Ace")
            # Convert to module name
            mod_name = rel_path.replace(os.sep, ".").replace(".__init__.py", "").replace(".py", "")
            ace_files.append((rel_path, mod_name))

# Scan all python files in ace/ and tests/ for imports
import_patterns = [
    re.compile(r"import\s+([\w\.]+)"),
    re.compile(r"from\s+([\w\.]+)\s+import")
]

imported_modules = set()
for folder in ["d:\\Projects\\Ace\\ace", "d:\\Projects\\Ace\\tests"]:
    for root, dirs, files in os.walk(folder):
        if "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    for line in f:
                        for pattern in import_patterns:
                            for match in pattern.finditer(line):
                                imported_modules.add(match.group(1))

print("Unused modules (files that are never imported anywhere in ace or tests):")
found_any = False
for rel_path, mod_name in ace_files:
    if mod_name == "ace" or mod_name == "ace.__main__" or mod_name == "ace.cli":
        continue
    # Check if mod_name or any parent is in imported_modules
    is_imported = False
    for imp in imported_modules:
        if imp == mod_name or imp.startswith(mod_name + "."):
            is_imported = True
            break
    if not is_imported:
        print(f"  {rel_path} ({mod_name})")
        found_any = True

if not found_any:
    print("  None")
