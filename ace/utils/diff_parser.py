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
