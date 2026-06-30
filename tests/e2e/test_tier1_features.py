
# Feature 1: NL Planner (5 tests)

def test_nl_planner_status(git_workspace):
    res = git_workspace.run(["show status"])
    assert res.returncode == 0
    assert "Executing: git status" in res.stdout
    assert "Plan executed successfully!" in res.stdout

def test_nl_planner_commit(git_workspace):
    # Stage a file first
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("hello")
    git_workspace.repo.index.add([str(test_file)])
    
    # Run NL planner that invokes commit
    res = git_workspace.run(["-y", "commit changes"], stdin_data="\n")
    assert res.returncode == 0
    assert "Executing: ace commit" in res.stdout
    assert "Committed changes successfully!" in res.stdout

def test_nl_planner_checkout(git_workspace):
    # Create an initial commit so git checkout has refs
    dummy_file = git_workspace.workspace / "dummy.txt"
    dummy_file.write_text("dummy")
    git_workspace.repo.index.add([str(dummy_file)])
    git_workspace.repo.index.commit("initial")
    
    current = git_workspace.repo.active_branch.name
    res = git_workspace.run(["-y", "switch to branch " + current])
    assert res.returncode == 0
    assert "Executing: git checkout" in res.stdout or "Executing: git switch" in res.stdout

def test_nl_planner_create_branch(git_workspace):
    # Create an initial commit so git checkout -b has refs
    dummy_file = git_workspace.workspace / "dummy.txt"
    dummy_file.write_text("dummy")
    git_workspace.repo.index.add([str(dummy_file)])
    git_workspace.repo.index.commit("initial")
    
    res = git_workspace.run(["-y", "create branch feature-test"])
    assert res.returncode == 0
    assert "git checkout -b feature-test" in res.stdout or "git switch -c feature-test" in res.stdout
    assert "feature-test" in git_workspace.repo.branches

def test_nl_planner_multi(git_workspace):
    res = git_workspace.run(["-y", "multi changes"])
    assert res.returncode == 0
    assert "git add ." in res.stdout
    assert "git status" in res.stdout

# Feature 2: Commit Generator (5 tests)

def test_commit_conventional(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("hello conventional")
    git_workspace.repo.index.add([str(test_file)])
    
    res = git_workspace.run(["commit", "-f", "conventional"], stdin_data="\n")
    assert res.returncode == 0
    assert "Committed changes successfully!" in res.stdout
    
    last_commit = list(git_workspace.repo.iter_commits(max_count=1))[0]
    assert "feat(mock): add mock feature" in last_commit.message

def test_commit_simple(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("hello simple")
    git_workspace.repo.index.add([str(test_file)])
    
    res = git_workspace.run(["commit", "-f", "simple"], stdin_data="\n")
    assert res.returncode == 0
    assert "Committed changes successfully!" in res.stdout
    
    last_commit = list(git_workspace.repo.iter_commits(max_count=1))[0]
    assert last_commit.message.strip() == "Add mock feature"

def test_commit_detailed(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("hello detailed")
    git_workspace.repo.index.add([str(test_file)])
    
    res = git_workspace.run(["commit", "-f", "detailed"], stdin_data="\n")
    assert res.returncode == 0
    assert "Committed changes successfully!" in res.stdout
    
    last_commit = list(git_workspace.repo.iter_commits(max_count=1))[0]
    assert "Add mock feature" in last_commit.message
    assert "This is a detailed description of the mock feature." in last_commit.message

def test_commit_skip(git_workspace):
    # Initial commit so HEAD exists
    dummy_file = git_workspace.workspace / "dummy.txt"
    dummy_file.write_text("dummy")
    git_workspace.repo.index.add([str(dummy_file)])
    git_workspace.repo.index.commit("initial")

    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("hello skip")
    git_workspace.repo.index.add([str(test_file)])
    
    res = git_workspace.run(["commit"], stdin_data="s\n")
    assert res.returncode == 0
    assert "Commit aborted." in res.stdout
    assert len(list(git_workspace.repo.iter_commits())) == 1

def test_commit_hook_mode(git_workspace):
    # Initial commit so HEAD exists
    dummy_file = git_workspace.workspace / "dummy.txt"
    dummy_file.write_text("dummy")
    git_workspace.repo.index.add([str(dummy_file)])
    git_workspace.repo.index.commit("initial")

    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("hello hook")
    git_workspace.repo.index.add([str(test_file)])
    
    msg_file = git_workspace.workspace / "commit_msg.txt"
    res = git_workspace.run(["commit", "--prepare", str(msg_file)])
    assert res.returncode == 0
    assert msg_file.exists()
    assert "feat(mock): add mock feature" in msg_file.read_text()

# Feature 3: Config Wizard / Display (5 tests)

def test_config_display(git_workspace):
    res = git_workspace.run(["config"])
    assert res.returncode == 0
    assert "Ace Active Configuration" in res.stdout
    assert "custom" in res.stdout

def test_setup_wizard_nvidia(git_workspace):
    # Setup nvidia: select 1, key, model, commit format, sign, emoji
    stdin_data = "1\nnvidia-key\nnvidia/llama-model\nconventional\ny\ny\n"
    res = git_workspace.run(["setup"], stdin_data=stdin_data)
    assert res.returncode == 0
    assert "Configuration saved successfully" in res.stdout

def test_setup_wizard_ollama(git_workspace):
    stdin_data = "2\nhttp://localhost:11434\nqwen-model\nsimple\nn\nn\n"
    res = git_workspace.run(["setup"], stdin_data=stdin_data)
    assert res.returncode == 0
    assert "Configuration saved successfully" in res.stdout

def test_setup_wizard_openai(git_workspace):
    stdin_data = "3\nopenai-key\ngpt-4o-mini\ndetailed\ny\nn\n"
    res = git_workspace.run(["setup"], stdin_data=stdin_data)
    assert res.returncode == 0
    assert "Configuration saved successfully" in res.stdout

def test_setup_wizard_custom(git_workspace):
    stdin_data = "5\nhttp://custom-url/v1\ncustom-key\ncustom-model\nconventional\nn\ny\n"
    res = git_workspace.run(["setup"], stdin_data=stdin_data)
    assert res.returncode == 0
    assert "Configuration saved successfully" in res.stdout

# Feature 4: Changelog Generator (5 tests)

def test_changelog_display(git_workspace):
    # Needs at least one commit
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("changelog content")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: initial changelog commit")
    
    res = git_workspace.run(["changelog"])
    assert res.returncode == 0
    assert "## [1.0.0]" in res.stdout
    assert "### ✨ Features" in res.stdout

def test_changelog_output_file(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("changelog content 2")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: second changelog commit")
    
    out_file = git_workspace.workspace / "CHANGELOG.md"
    res = git_workspace.run(["changelog", "-o", str(out_file)])
    assert res.returncode == 0
    assert out_file.exists()
    assert "## [1.0.0]" in out_file.read_text()

def test_changelog_range(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("changelog content 3")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: third commit")
    
    res = git_workspace.run(["changelog", "--from", "HEAD~1", "--to", "HEAD"])
    assert res.returncode == 0
    assert "## [1.0.0]" in res.stdout

def test_changelog_offline(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("changelog content 4")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: fourth commit")
    
    res = git_workspace.run(["changelog", "--offline"])
    assert res.returncode == 0
    assert "## [1.0.0]" in res.stdout

def test_changelog_empty(git_workspace):
    # Fresh repository with no commits
    res = git_workspace.run(["changelog"])
    assert res.returncode == 0
    assert "No commits found" in res.stdout or "empty" in res.stdout.lower() or res.stdout == ""

# Feature 5: PR Drafter (5 tests)

def test_pr_drafter_display(git_workspace):
    # Setup base and head
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    # Create branch
    base_branch = git_workspace.repo.active_branch.name
    git_workspace.repo.create_head("feature-pr")
    git_workspace.repo.heads["feature-pr"].checkout()
    
    test_file.write_text("changed")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: update test.txt")
    
    res = git_workspace.run(["pr", "--base", base_branch])
    assert res.returncode == 0
    assert "feat(mock): add mock feature" in res.stdout
    assert "This PR adds a mock feature." in res.stdout

def test_pr_drafter_output_file(git_workspace):
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
    
    out_file = git_workspace.workspace / "PR.md"
    res = git_workspace.run(["pr", "--base", base_branch, "-o", str(out_file)])
    assert res.returncode == 0
    assert out_file.exists()
    assert "feat(mock): add mock feature" in out_file.read_text()

def test_pr_drafter_offline(git_workspace):
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
    
    res = git_workspace.run(["pr", "--base", base_branch, "--offline"])
    assert res.returncode == 0
    assert "feat(mock): add mock feature" in res.stdout

def test_pr_drafter_explicit_base(git_workspace):
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
    
    # Pass explicit base
    res = git_workspace.run(["pr", "--base", base_branch])
    assert res.returncode == 0
    assert "feat(mock): add mock feature" in res.stdout

def test_pr_drafter_no_commits(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    base_branch = git_workspace.repo.active_branch.name
    git_workspace.repo.create_head("feature-pr")
    git_workspace.repo.heads["feature-pr"].checkout()
    
    # Running 'pr' with no commits on feature-pr compared to base should fail
    res = git_workspace.run(["pr", "--base", base_branch])
    assert res.returncode != 0
    assert "No commits found" in res.stderr or "No commits found" in res.stdout

# Feature 6: Diagnostics & Recovery (5 tests)

def test_doctor_healthy(git_workspace):
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    assert "All checks passed!" in res.stdout or "Diagnostics Assessment" in res.stdout

def test_doctor_untracked_large_file(git_workspace):
    # Create large untracked file (> 50 MB)
    large_file = git_workspace.workspace / "large_file.zip"
    with open(large_file, "wb") as f:
        f.seek(51 * 1024 * 1024 - 1)
        f.write(b"\0")
        
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    assert "Large Untracked Files" in res.stdout
    assert "Large files detected" in res.stdout or "Diagnostics Assessment" in res.stdout

def test_undo_commit(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    test_file.write_text("update")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("update commit")
    
    # We should have 2 commits
    assert len(list(git_workspace.repo.iter_commits())) == 2
    
    # Run undo, accept
    res = git_workspace.run(["undo"], stdin_data="\n")
    assert res.returncode == 0
    assert "Undo plan executed successfully!" in res.stdout
    
    # Commit should be undone, leaving 1 commit and changes staged
    assert len(list(git_workspace.repo.iter_commits())) == 1
    assert "test.txt" in git_workspace.repo.index.diff("HEAD")

def test_undo_staged(git_workspace):
    test_file = git_workspace.workspace / "test_staged.txt"
    test_file.write_text("staged content")
    git_workspace.repo.index.add([str(test_file)])
    
    # Run undo, accept
    res = git_workspace.run(["undo"], stdin_data="\n")
    assert res.returncode == 0
    assert "Undo plan executed successfully!" in res.stdout
    
    # File should be unstaged
    assert "test_staged.txt" not in [diff.a_path for diff in git_workspace.repo.index.diff("HEAD")]

def test_undo_skip(git_workspace):
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    test_file.write_text("update")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("update commit")
    
    # Run undo, skip
    res = git_workspace.run(["undo"], stdin_data="s\n")
    assert res.returncode == 0
    assert "Undo aborted." in res.stdout
    
    # Commit is still there
    assert len(list(git_workspace.repo.iter_commits())) == 2
