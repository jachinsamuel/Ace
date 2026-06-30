import os
import sys
import pytest

def test_combo_setup_then_commit(git_workspace):
    # Pairwise: Config Wizard & Commit Generator
    # 1. Run setup to select 'simple' commit format (choice 2)
    stdin_data = "2\nhttp://localhost:11434\nqwen-model\nsimple\nn\nn\n"
    res_setup = git_workspace.run(["setup"], stdin_data=stdin_data)
    assert res_setup.returncode == 0
    
    # 2. Stage changes and commit
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("combo test")
    git_workspace.repo.index.add([str(test_file)])
    
    res_commit = git_workspace.run(["commit"], stdin_data="\n")
    assert res_commit.returncode == 0
    
    # 3. Verify format override was respected (simple format -> "Add mock feature")
    last_commit = list(git_workspace.repo.iter_commits(max_count=1))[0]
    assert last_commit.message.strip() == "Add mock feature"

def test_combo_commit_then_changelog(git_workspace):
    # Pairwise: Commit Generator & Changelog Generator
    # 1. Commit a change using Ace
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("combo test commit-changelog")
    git_workspace.repo.index.add([str(test_file)])
    res_commit = git_workspace.run(["commit", "-f", "simple"], stdin_data="\n")
    assert res_commit.returncode == 0
    
    # 2. Generate changelog
    res_changelog = git_workspace.run(["changelog"])
    assert res_changelog.returncode == 0
    assert "## [1.0.0]" in res_changelog.stdout
    assert "### ✨ Features" in res_changelog.stdout

def test_combo_commit_then_pr(git_workspace):
    # Pairwise: Commit Generator & PR Drafter
    # 1. Set up base commit
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("initial")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("initial commit")
    
    base_branch = git_workspace.repo.active_branch.name
    git_workspace.repo.create_head("feature-combo")
    git_workspace.repo.heads["feature-combo"].checkout()
    
    # 2. Commit on branch using Ace
    test_file.write_text("updated combo pr")
    git_workspace.repo.index.add([str(test_file)])
    res_commit = git_workspace.run(["commit", "-f", "simple"], stdin_data="\n")
    assert res_commit.returncode == 0
    
    # 3. Draft PR
    res_pr = git_workspace.run(["pr", "--base", base_branch])
    assert res_pr.returncode == 0
    assert "feat(mock): add mock feature" in res_pr.stdout

def test_combo_doctor_then_undo(git_workspace):
    # Pairwise: Diagnostics & Recovery (doctor and undo)
    # 1. Stage changes
    test_file = git_workspace.workspace / "test.txt"
    test_file.write_text("dirty content")
    git_workspace.repo.index.add([str(test_file)])
    
    # 2. Run doctor to verify dirty state is reported
    res_doctor_before = git_workspace.run(["doctor"])
    assert res_doctor_before.returncode == 0
    assert "staged: 1" in res_doctor_before.stdout
    
    # 3. Run undo to unstage changes
    res_undo = git_workspace.run(["undo"], stdin_data="\n")
    assert res_undo.returncode == 0
    assert "Undo plan executed successfully!" in res_undo.stdout
    
    # 4. Run doctor again to confirm clean working tree
    res_doctor_after = git_workspace.run(["doctor"])
    assert res_doctor_after.returncode == 0
    assert "staged: 0" in res_doctor_after.stdout

def test_combo_nl_planner_then_config(git_workspace):
    # Pairwise: NL Planner & Config Display
    # Run NL Planner query requesting to show configuration
    # The IntentParser maps this to 'ace config'
    res = git_workspace.run(["-y", "show config"])
    assert res.returncode == 0
    assert "Executing: ace config" in res.stdout
    assert "Ace Active Configuration" in res.stdout

def test_combo_nl_planner_then_doctor(git_workspace):
    # Pairwise: NL Planner & Diagnostics
    # Run NL Planner query requesting diagnostics
    # The IntentParser maps this to 'ace doctor' or equivalent
    res = git_workspace.run(["-y", "doctor diagnosis"])
    assert res.returncode == 0
    assert "Executing: ace doctor" in res.stdout or "Executing: git status" in res.stdout
