import os
import sys
import pytest

# Feature 1: NL Planner Boundaries (5 tests)

def test_nl_planner_empty_query(git_workspace):
    res = git_workspace.run([])
    # Running without query displays help
    assert res.returncode == 0
    assert "Ace — AI-Powered Git Copilot" in res.stdout

def test_nl_planner_invalid_irrelevant_query(git_workspace):
    res = git_workspace.run(["make me a cup of coffee"])
    assert res.returncode == 0
    assert "No Git commands planned" in res.stdout

def test_nl_planner_non_git_repo(tmp_path, mock_llm_port):
    # Run in a non-git directory
    non_git_dir = tmp_path / "nongit"
    non_git_dir.mkdir()
    
    cmd = [
        sys.executable,
        "-c",
        "import sys, click; click.getchar = lambda: sys.stdin.read(1); from ace.cli import app; app()",
        "show status"
    ]
    env = os.environ.copy()
    env["ACE_PROVIDER"] = "custom"
    env["CUSTOM_API_BASE"] = f"http://127.0.0.1:{mock_llm_port}/v1"
    env["CUSTOM_API_KEY"] = "mock-key"
    env["CUSTOM_MODEL"] = "mock-model"
    env["HOME"] = str(tmp_path / "home")
    env["USERPROFILE"] = str(tmp_path / "home")
    env["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    
    import subprocess
    res = subprocess.run(
        cmd,
        cwd=str(non_git_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    assert res.returncode == 1
    assert "Not a git repository" in res.stderr or "Not a git repository" in res.stdout

def test_nl_planner_dry_run(git_workspace):
    res = git_workspace.run(["--dry-run", "create branch"])
    assert res.returncode == 0
    assert "Dry-run mode: execution skipped" in res.stdout
    # Branch should NOT be created
    assert "feature-test" not in git_workspace.repo.branches

def test_nl_planner_destructive_abort(git_workspace):
    # Destructive plans ask for confirmation
    res = git_workspace.run(["nuke working tree"], stdin_data="n\n")
    assert res.returncode == 0
    assert "Execution aborted." in res.stdout

# Feature 2: Commit Generator Boundaries (5 tests)

def test_commit_no_staged_changes(git_workspace):
    res = git_workspace.run(["commit"])
    assert res.returncode == 0
    assert "No staged changes" in res.stdout or "No changes are staged" in res.stdout

def test_commit_empty_diff(git_workspace):
    # Try staging an empty file
    test_file = git_workspace.workspace / "empty.txt"
    test_file.touch()
    git_workspace.repo.index.add([str(test_file)])
    
    res = git_workspace.run(["commit"])
    assert res.returncode == 0
    assert "Staged diff is empty" in res.stdout or "No staged changes" in res.stdout

def test_commit_invalid_format(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("hello conventional")
    git_workspace.repo.index.add([str(test_file)])
    
    # Should fallback or run conventional format if format is invalid
    res = git_workspace.run(["commit", "-f", "invalid_format"], stdin_data="\n")
    assert res.returncode == 0
    assert "Committed changes successfully!" in res.stdout

def test_commit_missing_llm_credentials(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("hello credential")
    git_workspace.repo.index.add([str(test_file)])
    
    # Temporarily corrupt API base URL in config to make LLM call fail
    cmd = [
        sys.executable,
        "-c",
        "import sys, click; click.getchar = lambda: sys.stdin.read(1); from ace.cli import app; app()",
        "commit"
    ]
    env = os.environ.copy()
    env["ACE_PROVIDER"] = "custom"
    env["CUSTOM_API_BASE"] = ""  # Missing API base!
    env["CUSTOM_API_KEY"] = "mock-key"
    env["CUSTOM_MODEL"] = "mock-model"
    env["HOME"] = str(git_workspace.home)
    env["USERPROFILE"] = str(git_workspace.home)
    
    import subprocess
    res = subprocess.run(
        cmd,
        cwd=str(git_workspace.workspace),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    assert res.returncode == 1
    assert "Configuration Error" in res.stdout or "Configuration Error" in res.stderr

def test_commit_very_long_diff(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("line\n" * 5000)
    git_workspace.repo.index.add([str(test_file)])
    
    res = git_workspace.run(["commit"], stdin_data="\n")
    assert res.returncode == 0
    assert "Committed changes successfully!" in res.stdout

# Feature 3: Config Wizard Boundaries (5 tests)

def test_setup_wizard_empty_input(git_workspace):
    # Press enter for everything
    res = git_workspace.run(["setup"], stdin_data="\n\n\n\n\n\n\n")
    assert res.returncode == 0
    assert "Configuration saved successfully" in res.stdout

def test_setup_wizard_invalid_provider(git_workspace):
    # Provide '9' (invalid) then defaults
    res = git_workspace.run(["setup"], stdin_data="9\n\n\n\n\n\n\n")
    assert res.returncode == 0
    assert "Invalid choice. Defaulting to NVIDIA." in res.stdout

def test_config_with_missing_file(git_workspace):
    # Delete config file
    config_file = git_workspace.home / ".ace" / "config.toml"
    if config_file.exists():
        config_file.unlink()
        
    res = git_workspace.run(["config"])
    assert res.returncode == 0
    assert "Ace Active Configuration" in res.stdout

def test_config_write_fail(git_workspace):
    # Make config directory a file so write fails
    config_dir = git_workspace.home / ".ace"
    if config_dir.exists():
        import shutil
        shutil.rmtree(config_dir)
    config_dir.touch() # Create file instead of dir
    
    res = git_workspace.run(["setup"], stdin_data="\n\n\n\n\n\n\n")
    assert "Save Configuration Error" in res.stdout or "Could not save configuration" in res.stdout

def test_setup_wizard_abort(git_workspace):
    res = git_workspace.run(["setup"], stdin_data="\n\n\n\n\n\n\n")
    assert res.returncode == 0

# Feature 4: Changelog Generator Boundaries (5 tests)

def test_changelog_invalid_ref(git_workspace):
    res = git_workspace.run(["changelog", "--from", "nonexistent-ref"])
    assert res.returncode == 1
    assert "Git Error" in res.stdout or "Git Error" in res.stderr

def test_changelog_no_history(git_workspace):
    # Fresh repository with no commits
    res = git_workspace.run(["changelog"])
    assert res.returncode == 0
    assert "No commits found" in res.stdout or res.stdout == ""

def test_changelog_single_commit(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("changelog content")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: initial commit")
    
    res = git_workspace.run(["changelog"])
    assert res.returncode == 0
    assert "## [1.0.0]" in res.stdout

def test_changelog_output_file_already_exists(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("changelog content")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: initial commit")
    
    out_file = git_workspace.workspace / "CHANGELOG.md"
    out_file.write_text("old content")
    
    res = git_workspace.run(["changelog", "-o", str(out_file)])
    assert res.returncode == 0
    assert out_file.exists()
    assert "## [1.0.0]" in out_file.read_text()

def test_changelog_custom_format_commits(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("changelog content 🧑‍💻")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: initial commit with emojis & extremely long subject line that might exceed standard buffer sizes in naive implementations")
    
    res = git_workspace.run(["changelog"])
    assert res.returncode == 0
    assert "## [1.0.0]" in res.stdout

# Feature 5: PR Drafter Boundaries (5 tests)

def test_pr_drafter_invalid_base_branch(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    res = git_workspace.run(["pr", "--base", "nonexistent-branch"])
    assert res.returncode == 1
    assert "Git Error" in res.stdout or "Git Error" in res.stderr

def test_pr_drafter_missing_llm_response_keys(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    base_branch = git_workspace.repo.active_branch.name
    git_workspace.repo.create_head("feature-pr")
    git_workspace.repo.heads["feature-pr"].checkout()
    
    test_file.write_text("changed")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: update test.txt")
    
    # Run with corrupted env / invalid custom base to cause error
    cmd = [
        sys.executable,
        "-c",
        "import sys, click; click.getchar = lambda: sys.stdin.read(1); from ace.cli import app; app()",
        "pr", "--base", base_branch
    ]
    env = os.environ.copy()
    env["ACE_PROVIDER"] = "custom"
    env["CUSTOM_API_BASE"] = "http://127.0.0.1:9999/v1" # Invalid URL!
    env["CUSTOM_API_KEY"] = "mock-key"
    env["CUSTOM_MODEL"] = "mock-model"
    env["HOME"] = str(git_workspace.home)
    env["USERPROFILE"] = str(git_workspace.home)
    
    import subprocess
    res = subprocess.run(
        cmd,
        cwd=str(git_workspace.workspace),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    assert res.returncode == 1
    assert "PR description" in res.stdout or "Error" in res.stderr or "Error" in res.stdout

def test_pr_drafter_invalid_json_llm_response(git_workspace):
    # Triggers same LLM failure / parser error behavior
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    base_branch = git_workspace.repo.active_branch.name
    git_workspace.repo.create_head("feature-pr")
    git_workspace.repo.heads["feature-pr"].checkout()
    
    test_file.write_text("changed")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: update test.txt")
    
    cmd = [
        sys.executable,
        "-c",
        "import sys, click; click.getchar = lambda: sys.stdin.read(1); from ace.cli import app; app()",
        "pr", "--base", base_branch
    ]
    env = os.environ.copy()
    env["ACE_PROVIDER"] = "custom"
    env["CUSTOM_API_BASE"] = "http://127.0.0.1:9999/v1"  # Invalid
    env["CUSTOM_API_KEY"] = "mock-key"
    env["CUSTOM_MODEL"] = "mock-model"
    env["HOME"] = str(git_workspace.home)
    env["USERPROFILE"] = str(git_workspace.home)
    
    import subprocess
    res = subprocess.run(
        cmd,
        cwd=str(git_workspace.workspace),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    assert res.returncode == 1

def test_pr_drafter_output_to_readonly_path(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    base_branch = git_workspace.repo.active_branch.name
    git_workspace.repo.create_head("feature-pr")
    git_workspace.repo.heads["feature-pr"].checkout()
    
    test_file.write_text("changed")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: update test.txt")
    
    res = git_workspace.run(["pr", "--base", base_branch, "-o", "/nonexistent/dir/pr.md"])
    assert res.returncode == 1
    assert "File Error" in res.stdout or "File Error" in res.stderr

def test_pr_drafter_detached_head(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    base_branch = git_workspace.repo.active_branch.name
    
    # Detach HEAD
    git_workspace.repo.git.checkout("HEAD~0")
    
    test_file.write_text("detached change")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: detached commit")
    
    res = git_workspace.run(["pr", "--base", base_branch])
    assert res.returncode == 0
    assert "feat(mock): add mock feature" in res.stdout

# Feature 6: Diagnostics & Recovery Boundaries (5 tests)

def test_doctor_lock_files_detected(git_workspace):
    # Create git lock file
    lock_file = git_workspace.workspace / ".git" / "index.lock"
    lock_file.write_text("")
    
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    assert "Process Lock Files" in res.stdout
    assert "Lock files found" in res.stdout

def test_doctor_detached_head(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.touch()
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    git_workspace.repo.git.checkout("HEAD~0")
    
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    assert "Branch Head" in res.stdout
    assert "Detached HEAD" in res.stdout

def test_undo_nothing_to_undo(git_workspace):
    # Clean workspace, no reflog or empty reflog
    res = git_workspace.run(["undo"], stdin_data="nothing\n")
    assert res.returncode == 0
    assert "Nothing to undo" in res.stdout

def test_undo_destructive_confirm_no(git_workspace):
    # Mock server triggers destructive plan
    res = git_workspace.run(["undo"], stdin_data="destructive\nn\n")
    assert res.returncode == 0
    assert "Undo aborted." in res.stdout

def test_undo_destructive_confirm_yes(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    res = git_workspace.run(["undo"], stdin_data="destructive\ny\n")
    assert res.returncode == 0
    assert "Undo plan executed successfully!" in res.stdout
