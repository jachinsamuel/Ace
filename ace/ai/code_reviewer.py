from typing import Dict, Any, List, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.utils.diff_parser import split_diff_by_file, trim_diff
from ace.ai.llm_factory import get_llm
from ace.ai.prompts.review import REVIEW_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ace.utils.json_utils import extract_json

class CodeReviewerError(Exception):
    """Raised when code review processing fails."""
    pass

class CodeReviewer:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def review_diff(self, diff_text: str, offline: bool = False) -> Tuple[List[Dict[str, Any]], float]:
        """
        Perform a code review on a raw diff string.
        
        Returns a tuple of (findings, overall_score).
        """
        if not diff_text.strip():
            return [], 10.0

        # Split diff by file
        file_diffs = split_diff_by_file(diff_text)
        if not file_diffs:
            return [], 10.0

        all_findings = []
        scores = []
        llm = get_llm(offline_override=offline)

        for filename, diff_content in file_diffs.items():
            # Skip binary diffs or very small metadata updates
            if "Binary files" in diff_content or len(diff_content.strip()) < 20:
                continue

            user_prompt = USER_PROMPT_TEMPLATE.format(
                filename=filename,
                diff_content=trim_diff(diff_content, max_chars=15000)  # Cap file diff size
            )

            from ace.core.config import get_config
            from ace.utils.i18n import get_language_instruction

            lang_inst = get_language_instruction(get_config().ai.language)

            messages = [
                SystemMessage(content=REVIEW_SYSTEM_PROMPT + lang_inst),
                HumanMessage(content=user_prompt)
            ]

            try:
                response = llm.invoke(messages)
                parsed = extract_json(response.content)
                
                raw_score = parsed.get("score") if isinstance(parsed, dict) else 10.0
                if raw_score is None:
                    score = 10.0
                else:
                    try:
                        score_str = str(raw_score).split("/")[0].strip()
                        score = float(score_str)
                    except (ValueError, TypeError):
                        score = 10.0
                scores.append(score)
                
                findings = parsed.get("findings", []) if isinstance(parsed, dict) else []
                if isinstance(findings, list):
                    for finding in findings:
                        # Annotate with the filename
                        finding["file"] = filename
                        all_findings.append(finding)
            except Exception as e:
                # Log or handle exception per file, but don't crash the whole review
                # We can add a fallback warning finding
                all_findings.append({
                    "file": filename,
                    "category": "suggestion",
                    "severity": "info",
                    "line": None,
                    "description": f"AI review failed for this file: {e}",
                    "fix": None
                })
                scores.append(10.0)

        overall_score = sum(scores) / len(scores) if scores else 10.0
        # Round overall score
        overall_score = round(overall_score, 1)

        return all_findings, overall_score
