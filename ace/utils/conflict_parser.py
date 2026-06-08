from typing import List, Dict, Any

def parse_conflict_file(content: str) -> List[Dict[str, Any]]:
    """
    Parse file content containing git merge conflicts.
    
    Returns a list of dicts representing each conflict block:
    {
        "full_block": str,         # The raw conflict block text
        "head": str,               # The local changes (HEAD)
        "incoming": str,           # The incoming changes
        "head_branch": str,        # Branch identifier for HEAD
        "incoming_branch": str     # Branch identifier for incoming
    }
    """
    lines = content.splitlines()
    blocks = []
    
    in_conflict = False
    conflict_lines = []
    current_section = None # 'head' or 'incoming'
    head_lines = []
    incoming_lines = []
    
    start_marker = ""
    
    for line in lines:
        if line.startswith("<<<<<<<"):
            in_conflict = True
            current_section = "head"
            start_marker = line
            conflict_lines = [line]
            head_lines = []
            incoming_lines = []
        elif line.startswith("======="):
            if in_conflict:
                current_section = "incoming"
                conflict_lines.append(line)
        elif line.startswith(">>>>>>>"):
            if in_conflict:
                conflict_lines.append(line)
                end_marker = line
                
                blocks.append({
                    "full_block": "\n".join(conflict_lines),
                    "head": "\n".join(head_lines),
                    "incoming": "\n".join(incoming_lines),
                    "head_branch": start_marker.replace("<<<<<<<", "").strip(),
                    "incoming_branch": end_marker.replace(">>>>>>>", "").strip()
                })
                
                in_conflict = False
                current_section = None
        else:
            if in_conflict:
                conflict_lines.append(line)
                if current_section == "head":
                    head_lines.append(line)
                elif current_section == "incoming":
                    incoming_lines.append(line)
                    
    return blocks
