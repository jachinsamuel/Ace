from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.ai.llm_factory import get_llm
from ace.ai.prompts.pr import PR_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ace.utils.json_utils import extract_json

class PRDrafter:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def draft_pr(self, base_branch: str, offline: bool = False) -> Dict[str, Any]:
        """
        Gathers branch commits and code differences between base_branch and current HEAD,
        and generates a pull request description including a title and a Markdown body.
        """
        current_branch = self.git_ops.get_current_branch() or "HEAD"

        # Get commits between base_branch and HEAD
        try:
            commits_text = self.git_ops.execute(f"log {base_branch}..HEAD --oneline")
        except Exception as e:
            raise Exception(f"Failed to fetch commits between {base_branch} and {current_branch}: {e}")

        if not commits_text.strip():
            raise Exception(f"No commits found between {base_branch} and {current_branch}.")

        # Get diff between base_branch and HEAD
        try:
            diff_text = self.git_ops.get_branch_diff(base_branch)
        except Exception as e:
            raise Exception(f"Failed to fetch diff between {base_branch} and {current_branch}: {e}")

        if not diff_text.strip():
            raise Exception(f"No differences found between {base_branch} and {current_branch}.")

        llm = get_llm(offline_override=offline)
        
        # Limit diff text size to prevent exceeding LLM context window (approx 25k chars)
        if len(diff_text) > 25000:
            diff_text = diff_text[:25000] + "\n\n... (diff truncated due to size) ..."

        usr_prompt = USER_PROMPT_TEMPLATE.format(
            current_branch=current_branch,
            base_branch=base_branch,
            commits=commits_text.strip(),
            diff=diff_text.strip()
        )

        messages = [
            SystemMessage(content=PR_SYSTEM_PROMPT),
            HumanMessage(content=usr_prompt)
        ]

        response = llm.invoke(messages)
        parsed = extract_json(response.content)
        
        if "title" not in parsed or "body" not in parsed:
            raise Exception("AI response JSON missing 'title' or 'body' keys.")
            
        return parsed
