from pathlib import Path
from typing import Dict, Any, List, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.utils.conflict_parser import parse_conflict_file
from ace.ai.llm_factory import get_llm
from ace.ai.prompts.conflict import CONFLICT_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ace.utils.json_utils import extract_json

class ConflictResolverError(Exception):
    """Raised when conflict resolution fails."""
    pass

class ConflictResolver:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def get_suggestions(self, file_path: str, offline: bool = False) -> List[Dict[str, Any]]:
        """
        Scan a file for conflicts and return AI resolution suggestions for each.
        
        Returns a list of dicts:
        [
            {
                "full_block": str,
                "head": str,
                "incoming": str,
                "suggested_merged": str,
                "explanation": str
            }
        ]
        """
        full_path = Path(self.git_ops.working_dir) / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ConflictResolverError(f"Failed to read file {file_path}: {e}")

        blocks = parse_conflict_file(content)
        if not blocks:
            return []

        llm = get_llm(offline_override=offline)
        suggestions = []

        for block in blocks:
            sys_prompt = CONFLICT_SYSTEM_PROMPT.format(filename=file_path)
            usr_prompt = USER_PROMPT_TEMPLATE.format(
                head_content=block["head"],
                incoming_content=block["incoming"]
            )

            messages = [
                SystemMessage(content=sys_prompt),
                HumanMessage(content=usr_prompt)
            ]

            try:
                response = llm.invoke(messages)
                parsed = extract_json(response.content)
                
                suggestions.append({
                    "full_block": block["full_block"],
                    "head": block["head"],
                    "incoming": block["incoming"],
                    "suggested_merged": parsed.get("merged_content", block["head"]), # Fallback to head
                    "explanation": parsed.get("explanation", "AI suggested resolution.")
                })
            except Exception as e:
                # Fallback in case of AI failures
                suggestions.append({
                    "full_block": block["full_block"],
                    "head": block["head"],
                    "incoming": block["incoming"],
                    "suggested_merged": block["head"], # Keep head as fallback
                    "explanation": f"AI suggestion failed: {e}. Keeping local branch version as default suggestion."
                })

        return suggestions

    def apply_resolution(self, file_path: str, block_replacements: List[Tuple[str, str]]) -> None:
        """
        Apply resolutions to a conflicted file.
        
        block_replacements: List of tuples (full_conflict_block, replacement_content)
        """
        full_path = Path(self.git_ops.working_dir) / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = full_path.read_text(encoding="utf-8")
        
        for full_block, replacement in block_replacements:
            if full_block in content:
                content = content.replace(full_block, replacement)
            else:
                # Try with normalized line endings
                norm_block = full_block.replace("\r\n", "\n")
                norm_content = content.replace("\r\n", "\n")
                if norm_block in norm_content:
                    norm_content = norm_content.replace(norm_block, replacement)
                    # Restore Windows line endings if they were originally present
                    if "\r\n" in content:
                        content = norm_content.replace("\n", "\r\n")
                    else:
                        content = norm_content
                else:
                    raise ConflictResolverError(
                        "Conflict block not found in file. Has it been edited already?"
                    )

        full_path.write_text(content, encoding="utf-8")
