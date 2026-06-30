import os
import sys
import json
import socket
import threading
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytest
import git

class MockLLMHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress request logging to keep output clean
        pass

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            messages = payload.get("messages", [])
            full_text = " ".join([m.get("content", "") for m in messages])
            
            response_content = "Default mock response"
            
            # 1. Intent Parser / NL Planner
            if "expert AI Git Copilot" in full_text or "Translate this request into Git commands" in full_text or "IntentParser" in full_text:
                # Find the user's query
                user_msg = ""
                for m in reversed(messages):
                    if m.get("role") == "user":
                        user_msg = m.get("content", "")
                        break
                
                # Check keywords in the user request
                import re
                match = re.search(r'User Request:\s*"(.*)"', user_msg, re.IGNORECASE)
                if match:
                    query_val = match.group(1).lower()
                else:
                    query_val = user_msg.lower()

                if "stage everything and commit" in query_val or "stage and commit" in query_val:
                    response_content = json.dumps({
                        "commands": ["git add .", "ace commit"],
                        "explanation": "Stage all changes and run commit.",
                        "risk_level": "moderate",
                        "alternatives": None
                    })
                elif "status" in query_val:
                    response_content = json.dumps({
                        "commands": ["git status"],
                        "explanation": "Show current repository status.",
                        "risk_level": "safe",
                        "alternatives": None
                    })
                elif "commit" in query_val:
                    response_content = json.dumps({
                        "commands": ["ace commit"],
                        "explanation": "Run smart commit wizard.",
                        "risk_level": "moderate",
                        "alternatives": None
                    })
                elif "nuke" in query_val or "destructive" in query_val or "hard reset" in query_val:
                    response_content = json.dumps({
                        "commands": ["git reset --hard HEAD"],
                        "explanation": "Destructively reset working directory.",
                        "risk_level": "destructive",
                        "alternatives": "git stash"
                    })
                elif "invalid" in query_val or "unrelated" in query_val:
                    response_content = json.dumps({
                        "commands": [],
                        "explanation": "I cannot parse this command.",
                        "risk_level": "safe",
                        "alternatives": None
                    })
                elif "multi" in query_val:
                    response_content = json.dumps({
                        "commands": ["git add .", "git status"],
                        "explanation": "Multiple commands planned.",
                        "risk_level": "moderate",
                        "alternatives": None
                    })
                elif "checkout branch" in query_val or "switch" in query_val:
                    parts = query_val.split()
                    branch_name = parts[-1] if parts else "main"
                    response_content = json.dumps({
                        "commands": [f"git checkout {branch_name}"],
                        "explanation": f"Switch to {branch_name} branch.",
                        "risk_level": "moderate",
                        "alternatives": None
                    })
                elif "create branch" in query_val:
                    parts = query_val.split()
                    branch_name = parts[-1] if len(parts) > 2 else "feature-test"
                    response_content = json.dumps({
                        "commands": [f"git checkout -b {branch_name}"],
                        "explanation": f"Create new branch {branch_name}.",
                        "risk_level": "moderate",
                        "alternatives": None
                    })
                else:
                    response_content = json.dumps({
                        "commands": ["git status"],
                        "explanation": "Default status fallback.",
                        "risk_level": "safe",
                        "alternatives": None
                    })
            
            # 2. Commit Message Generator
            elif "Conventional Commits" in full_text or "commit message" in full_text or "Staged Diff" in full_text:
                if "one-line commit message" in full_text or "SIMPLE_COMMIT_SYSTEM_PROMPT" in full_text:
                    response_content = "Add mock feature"
                elif "detailed, descriptive multi-line commit message" in full_text or "DETAILED_COMMIT_SYSTEM_PROMPT" in full_text:
                    response_content = "Add mock feature\n\nThis is a detailed description of the mock feature."
                else:
                    response_content = "feat(mock): add mock feature\n\n- Implement mock feature details\n- Add mock feature tests"
            
            # 3. Changelog Generator
            elif "release coordinator and technical writer" in full_text or "Markdown changelog from the provided Git commit log" in full_text:
                response_content = "# Changelog\n\n## [1.0.0]\n\n### ✨ Features\n- Add mock feature\n\n### 🐛 Bug Fixes\n- Fix mock bug"
            
            # 4. PR Drafter
            elif "PR_SYSTEM_PROMPT" in full_text or "Pull Request (PR) description" in full_text:
                response_content = json.dumps({
                    "title": "feat(mock): add mock feature",
                    "body": "# Description\nThis PR adds a mock feature.\n\n# Key Changes\n- Add mock code\n- Add mock tests"
                })
            
            # 5. Diagnostics & Recovery (doctor)
            elif "Git Diagnostics Status Report" in full_text or "diagnostics_json" in full_text or "Git Diagnostics" in full_text or "Git diagnostics findings" in full_text or "DOCTOR_SYSTEM_PROMPT" in full_text:
                response_content = "🩺 **Diagnostics Assessment**\n\nFound some issues.\n\n📋 **Recovery Plan**\n\n- Run git clean\n- Run git restore\n\n💡 **Prevention Tip**\n\nCommit more often."
            
            # 6. Smart Undo
            elif "UNDO_SYSTEM_PROMPT" in full_text or "reflog_entries" in full_text:
                if "test_staged.txt" in full_text or "staged_files" in full_text and "None" not in full_text:
                    response_content = json.dumps({
                        "commands": ["git restore --staged ."],
                        "explanation": "Unstage changes.",
                        "risk_level": "moderate",
                        "alternatives": None
                    })
                elif "destructive" in full_text or "hard" in full_text:
                    response_content = json.dumps({
                        "commands": ["git reset --hard ORIG_HEAD"],
                        "explanation": "Destructively undo merge.",
                        "risk_level": "destructive",
                        "alternatives": "git stash"
                    })
                elif "nothing" in full_text or "clean" in full_text:
                    response_content = json.dumps({
                        "commands": [],
                        "explanation": "Nothing to undo.",
                        "risk_level": "safe",
                        "alternatives": None
                    })
                else:
                    response_content = json.dumps({
                        "commands": ["git reset --soft HEAD~1"],
                        "explanation": "Undo last commit.",
                        "risk_level": "moderate",
                        "alternatives": None
                    })
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response_payload = {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "mock-model",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop"
                }]
            }
            self.wfile.write(json.dumps(response_payload).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

@pytest.fixture(scope="session")
def mock_llm_port():
    # Bind to port 0 to get a dynamic port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    
    # Run server in background thread
    server = HTTPServer(('127.0.0.1', port), MockLLMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    
    yield port
    
    server.shutdown()
    server.server_close()

@pytest.fixture
def git_workspace(tmp_path, mock_llm_port):
    temp_git_dir = tmp_path / "repo"
    temp_git_dir.mkdir()
    
    # Initialize git repo
    repo = git.Repo.init(temp_git_dir)
    
    # Configure dummy user info
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "E2E Test User")
        cw.set_value("user", "email", "e2e@example.com")
        
    temp_home_path = tmp_path / "home"
    temp_home_path.mkdir()
    
    class AceRunner:
        def __init__(self, workspace_path, home_path, port, repository):
            self.workspace = workspace_path
            self.home = home_path
            self.port = port
            self.repo = repository
            
        def run(self, args, stdin_data=None):
            cmd = [
                sys.executable,
                "-c",
                "import sys, click; click.getchar = lambda: sys.stdin.read(1); from ace.cli import app; app()",
            ] + args
            env = os.environ.copy()
            env["ACE_PROVIDER"] = "custom"
            env["CUSTOM_API_BASE"] = f"http://127.0.0.1:{self.port}/v1"
            env["CUSTOM_API_KEY"] = "mock-key"
            env["CUSTOM_MODEL"] = "mock-model"
            env["HOME"] = str(self.home)
            env["USERPROFILE"] = str(self.home)
            
            # Avoid picking up any parent git repos
            env["GIT_CEILING_DIRECTORIES"] = str(self.workspace.parent)
            
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace),
                input=stdin_data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                env=env
            )
            return result
            
    return AceRunner(temp_git_dir, temp_home_path, mock_llm_port, repo)
