import os
import tempfile
import json
import sys
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.ai.llm_factory import get_llm
from ace.ai.prompts.rebase import REBASE_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ace.utils.json_utils import extract_json

class RebaseHelper:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def get_local_commits(self, base_branch: str) -> List[Dict[str, Any]]:
        """Get list of local commits not merged into the base branch, in chronological order."""
        try:
            log_data = self.git_ops.execute(f"log {base_branch}..HEAD --reverse --format=%H|%an|%s")
        except Exception:
            return []
            
        commits = []
        for line in log_data.splitlines():
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    commits.append({
                        "hexsha": parts[0],
                        "author": parts[1],
                        "summary": parts[2].strip()
                    })
        return commits

    def analyze_commits(self, commits: List[Dict[str, Any]], offline: bool = False) -> Dict[str, Any]:
        """Ask LLM to recommend squash/reword actions for the local commits."""
        commit_lines = []
        for c in commits:
            commit_lines.append(f"- {c['hexsha'][:7]} - {c['summary']} (by {c['author']})")
        commit_list_text = "\n".join(commit_lines)

        usr_prompt = USER_PROMPT_TEMPLATE.format(commit_list_text=commit_list_text)
        
        messages = [
            SystemMessage(content=REBASE_SYSTEM_PROMPT),
            HumanMessage(content=usr_prompt)
        ]

        llm = get_llm(offline_override=offline)
        response = llm.invoke(messages)
        
        return extract_json(response.content)

    def run_auto_rebase(self, base_branch: str, recommendations: List[Dict[str, Any]]) -> str:
        """Execute programmatic interactive rebase using Python sequence and message editors."""
        action_map = {}
        reword_messages = {}
        for rec in recommendations:
            sha = rec["hexsha"][:7].lower()
            action_map[sha] = rec["action"].lower()
            if rec["action"].lower() == "reword" and rec.get("new_message"):
                reword_messages[rec["summary"].strip()] = rec["new_message"]

        # Create mapping JSON
        map_data = {
            "actions": action_map,
            "rewords": reword_messages
        }
        
        fd, map_path = tempfile.mkstemp(suffix=".json")
        editor_path = None
        reword_editor_path = None
        
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(map_data, f)

            # Sequence editor: edits git-rebase-todo
            seq_code = f"""import sys, json
with open({repr(map_path)}, 'r') as f:
    data = json.load(f)
actions = data['actions']

todo_path = sys.argv[1]
with open(todo_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = []
for line in content.splitlines():
    if not line.strip() or line.startswith('#'):
        lines.append(line)
        continue
    parts = line.split()
    if len(parts) >= 2 and parts[0] == 'pick':
        sha = parts[1][:7].lower()
        if sha in actions:
            action = actions[sha]
            lines.append(action + ' ' + ' '.join(parts[1:]))
            continue
    lines.append(line)

with open(todo_path, 'w', encoding='utf-8') as f:
    f.write('\\n'.join(lines) + '\\n')
"""
            editor_fd, editor_path = tempfile.mkstemp(suffix=".py")
            with os.fdopen(editor_fd, 'w', encoding='utf-8') as f:
                f.write(seq_code)

            # Commit msg editor: edits COMMIT_EDITMSG for reword actions
            reword_code = f"""import sys, json
with open({repr(map_path)}, 'r') as f:
    data = json.load(f)
rewords = data['rewords']

msg_path = sys.argv[1]
with open(msg_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
if lines:
    subject = lines[0].strip()
    if subject in rewords:
        new_msg = rewords[subject]
        comments = [l for l in lines[1:] if l.strip().startswith('#')]
        with open(msg_path, 'w', encoding='utf-8') as f_out:
            f_out.write(new_msg + '\\n\\n' + '\\n'.join(comments))
"""
            reword_fd, reword_editor_path = tempfile.mkstemp(suffix=".py")
            with os.fdopen(reword_fd, 'w', encoding='utf-8') as f:
                f.write(reword_code)

            # Execute rebase with environment variables
            env = os.environ.copy()
            python_exe = sys.executable
            env["GIT_SEQUENCE_EDITOR"] = f'"{python_exe}" "{editor_path}"'
            env["GIT_EDITOR"] = f'"{python_exe}" "{reword_editor_path}"'
            
            # Execute command directly using GitPython
            # Run rebase -i base_branch
            # GitPython execute method wraps repo.git
            return self.git_ops.repo.git.rebase("-i", base_branch, env=env)
        finally:
            # Clean up temp files
            try:
                os.unlink(map_path)
            except Exception:
                pass
            if editor_path:
                try:
                    os.unlink(editor_path)
                except Exception:
                    pass
            if reword_editor_path:
                try:
                    os.unlink(reword_editor_path)
                except Exception:
                    pass
