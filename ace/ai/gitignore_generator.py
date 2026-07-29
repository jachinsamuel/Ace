import os
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.ai.llm_factory import get_llm
from ace.ai.prompts.ignore import IGNORE_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ace.utils.json_utils import extract_json

class GitignoreGenerator:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def generate_rules(self, query: str, offline: bool = False) -> Dict[str, Any]:
        """
        Reads the current .gitignore file (if any), queries the LLM with the user's
        ignore request, and returns generated rules to append along with an explanation.
        """
        gitignore_path = os.path.join(self.git_ops.working_dir, ".gitignore")
        current_content = ""
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    current_content = f.read()
            except Exception:
                current_content = ""

        llm = get_llm(offline_override=offline)
        
        usr_prompt = USER_PROMPT_TEMPLATE.format(
            query=query,
            current_gitignore=current_content.strip() or "(empty)"
        )

        from ace.core.config import get_config
        from ace.utils.i18n import get_language_instruction
        lang_inst = get_language_instruction(get_config().ai.language)

        messages = [
            SystemMessage(content=IGNORE_SYSTEM_PROMPT + lang_inst),
            HumanMessage(content=usr_prompt)
        ]

        try:
            response = llm.invoke(messages)
            parsed = extract_json(response.content)
        except Exception as e:
            raise Exception(f"AI gitignore generation failed: {e}")
        
        if not isinstance(parsed, dict) or "rules" not in parsed or "explanation" not in parsed:
            raise Exception("AI response JSON missing 'rules' or 'explanation' keys.")
            
        return parsed
