import re
from typing import Dict

def split_diff_by_file(diff_text: str) -> Dict[str, str]:
    """
    Split a combined git diff string into separate diff strings per file.
    
    Returns a dictionary mapping file path to its diff segment.
    """
    if not diff_text.strip():
        return {}

    # Split by the git diff header pattern
    chunks = re.split(r"^(diff --git a/)", diff_text, flags=re.MULTILINE)
    
    file_diffs = {}
    
    # The first element in chunks is everything before the first "diff --git a/" (usually empty)
    # The subsequent elements come in pairs: the separator "diff --git a/" and the actual chunk body
    i = 1
    while i < len(chunks):
        sep = chunks[i]
        body = chunks[i+1] if i + 1 < len(chunks) else ""
        
        full_chunk = sep + body
        
        # Parse the filename from the first line: diff --git a/filename b/filename
        first_line = full_chunk.splitlines()[0]
        # Match 'b/path' from the end of the line
        match = re.search(r" b/(.+)$", first_line)
        if match:
            filename = match.group(1).strip()
            file_diffs[filename] = full_chunk
        else:
            # Fallback regex if first line matches diff --git a/path b/path with quotes/spaces
            match_alt = re.search(r"a/(.+?) b/", first_line)
            if match_alt:
                filename = match_alt.group(1).strip()
                file_diffs[filename] = full_chunk
            else:
                file_diffs[f"unknown_file_{i}"] = full_chunk
                
        i += 2
        
    return file_diffs

def trim_diff(diff_text: str, max_chars: int = 20000) -> str:
    """
    Trims a combined git diff text to a maximum character length.
    Splits by file to avoid truncating in the middle of a file diff where possible.
    """
    if len(diff_text) <= max_chars:
        return diff_text

    file_diffs = split_diff_by_file(diff_text)
    if not file_diffs:
        return diff_text[:max_chars]

    trimmed_chunks = []
    current_size = 0
    omitted_files = []

    for filename, diff_content in file_diffs.items():
        if current_size >= max_chars:
            omitted_files.append(filename)
            continue

        if current_size + len(diff_content) <= max_chars:
            trimmed_chunks.append(diff_content)
            current_size += len(diff_content)
        else:
            # This file diff pushes it over the limit.
            # Truncate lines of this specific file diff to fit the remaining space.
            space_left = max_chars - current_size
            if space_left > 100 or current_size == 0:
                lines = diff_content.splitlines()
                truncated_lines = []
                temp_size = 0
                for line in lines:
                    if temp_size + len(line) + 1 > space_left and current_size + temp_size > 0:
                        break
                    truncated_lines.append(line)
                    temp_size += len(line) + 1
                truncated_lines.append("... (file diff truncated due to size) ...")
                trimmed_chunks.append("\n".join(truncated_lines))
                current_size += temp_size + len("... (file diff truncated due to size) ...") + 1
            else:
                omitted_files.append(filename)

    res = "\n".join(trimmed_chunks)
    if omitted_files:
        res += f"\n\n... (diff truncated, {len(omitted_files)} more file(s) omitted: {', '.join(omitted_files[:3])}{' and others' if len(omitted_files) > 3 else ''}) ..."
    return res

