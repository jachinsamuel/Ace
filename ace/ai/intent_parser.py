from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.core.context import RepoContext
from ace.ai.llm_factory import get_llm
from ace.ai.prompts.intent import INTENT_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ace.utils.json_utils import extract_json, JSONExtractError

class IntentParserError(Exception):
    """Raised when intent parsing fails."""
    pass

class IntentParser:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops
        self.context_builder = RepoContext(git_ops)

    def parse_intent(self, query: str, offline: bool = False) -> Dict[str, Any]:
        """
        Convert a natural language query into structured Git commands.
        
        Returns a dict:
        {
            "commands": List[str],
            "explanation": str,
            "risk_level": "safe" | "moderate" | "destructive",
            "alternatives": Optional[str]
        }
        """
        # Fetch current context
        repo_context = self.context_builder.format_context_for_prompt()
        
        user_prompt = USER_PROMPT_TEMPLATE.format(
            repo_context=repo_context,
            query=query
        )
        
        messages = [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]
        
        # Initialize and call LLM
        llm = get_llm(offline_override=offline)
        response = llm.invoke(messages)
        
        raw_content = response.content.strip()
        
        # Parse the output using shared utility
        try:
            parsed = extract_json(raw_content)
        except JSONExtractError as e:
            raise IntentParserError(str(e))
        
        # Validate keys and default types
        commands = parsed.get("commands", [])
        if not isinstance(commands, list):
            commands = [str(commands)] if commands else []
            
        return {
            "commands": [cmd.strip() for cmd in commands],
            "explanation": str(parsed.get("explanation", "No explanation provided.")),
            "risk_level": str(parsed.get("risk_level", "safe")).lower(),
            "alternatives": parsed.get("alternatives", None)
        }
