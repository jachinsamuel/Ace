
def test_workload_feature_lifecycle(git_workspace):
    # Scenario 1: Config -> Branch -> Code Change -> NL Commit -> Doctor check -> PR Draft -> Changelog
    # Create initial commit so HEAD exists
    init_file = git_workspace.workspace / "init.txt"
    init_file.write_text("initial")
    git_workspace.repo.index.add([str(init_file)])
    git_workspace.repo.index.commit("feat: initial commit")

    # 1. Config Setup
    res = git_workspace.run(["setup"], stdin_data="5\nhttp://custom:1234/v1\nkey\nmodel\nconventional\nn\nn\n")
    assert res.returncode == 0
    
    # 2. Branch creation
    base_branch = git_workspace.repo.active_branch.name
    res = git_workspace.run(["-y", "create branch feature-life"])
    assert res.returncode == 0
    
    # 3. Code change
    test_file = git_workspace.workspace / "app.py"
    test_file.write_text("print('hello life')")
    
    # 4. Stage and commit via NL
    res = git_workspace.run(["-y", "stage everything and commit"], stdin_data="\n")
    assert res.returncode == 0
    assert "Committed changes successfully!" in res.stdout
    
    # 5. Doctor checks
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    
    # 6. Draft PR
    res = git_workspace.run(["pr", "--base", base_branch])
    assert res.returncode == 0
    assert "feat(mock): add mock feature" in res.stdout
    
    # 7. Generate changelog
    res = git_workspace.run(["changelog"])
    assert res.returncode == 0
    assert "[1.0.0]" in res.stdout

def test_workload_hotfix_lifecycle(git_workspace):
    # Scenario 2: Doctor (Pre-check) -> Branch -> Hotfix -> Smart Commit -> Config check -> Changelog
    # 1. Doctor precheck
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    
    # 2. Switch to hotfix branch
    res = git_workspace.run(["-y", "create branch hotfix-branch"])
    assert res.returncode == 0
    
    # 3. Hotfix change
    fix_file = git_workspace.workspace / "bug.py"
    fix_file.write_text("resolved = True")
    git_workspace.repo.index.add([str(fix_file)])
    
    # 4. Commit via Ace
    res = git_workspace.run(["commit", "-f", "conventional"], stdin_data="\n")
    assert res.returncode == 0
    
    # 5. Config view
    res = git_workspace.run(["config"])
    assert res.returncode == 0
    
    # 6. Changelog to verify
    res = git_workspace.run(["changelog"])
    assert res.returncode == 0
    assert "[1.0.0]" in res.stdout

def test_workload_multi_developer_rebase_recovery(git_workspace):
    # Scenario 3: Commits -> Staged change -> Doctor (detects staged) -> Undo -> Doctor (clean)
    # 1. Base commit
    test_file = git_workspace.workspace / "base.txt"
    test_file.write_text("base content")
    git_workspace.repo.index.add([str(test_file)])
    git_workspace.repo.index.commit("feat: base commit")
    
    # 2. Make staged changes
    test_file.write_text("developer 1 conflict")
    git_workspace.repo.index.add([str(test_file)])
    
    # 3. Doctor checks
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    assert "staged: 1" in res.stdout
    
    # 4. Recover with Undo (unstages changes)
    res = git_workspace.run(["undo"], stdin_data="\n")
    assert res.returncode == 0
    
    # 5. Confirm repository clean
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    assert "staged: 0" in res.stdout

def test_workload_release_documentation(git_workspace):
    # Scenario 4: Multiple features committed -> Changelog.md -> Release PR.md -> Verification
    # 1. Commit features
    test_file1 = git_workspace.workspace / "feat1.txt"
    test_file1.write_text("feature 1")
    git_workspace.repo.index.add([str(test_file1)])
    git_workspace.repo.index.commit("feat: implement feature 1")
    
    test_file2 = git_workspace.workspace / "feat2.txt"
    test_file2.write_text("feature 2")
    git_workspace.repo.index.add([str(test_file2)])
    git_workspace.repo.index.commit("feat: implement feature 2")
    
    # Create release branch
    base_branch = git_workspace.repo.active_branch.name
    git_workspace.repo.create_head("release-v1.0.0")
    git_workspace.repo.heads["release-v1.0.0"].checkout()
    
    # Commit release note doc
    test_file3 = git_workspace.workspace / "release.txt"
    test_file3.write_text("release note placeholder")
    git_workspace.repo.index.add([str(test_file3)])
    git_workspace.repo.index.commit("chore: prepare release v1.0.0")
    
    # 2. Generate CHANGELOG.md file
    changelog_path = git_workspace.workspace / "CHANGELOG.md"
    res = git_workspace.run(["changelog", "-o", str(changelog_path)])
    assert res.returncode == 0
    assert changelog_path.exists()
    
    # 3. Generate RELEASE_PR.md file
    pr_path = git_workspace.workspace / "RELEASE_PR.md"
    res = git_workspace.run(["pr", "--base", base_branch, "-o", str(pr_path)])
    assert res.returncode == 0
    assert pr_path.exists()
    
    # Verify contents
    assert "## [1.0.0]" in changelog_path.read_text(encoding="utf-8")
    assert "feat(mock): add mock feature" in pr_path.read_text(encoding="utf-8")

def test_workload_destructive_plan_recovery(git_workspace):
    # Scenario 5: Destructive plan -> abort -> confirm files exist -> approve -> confirm deleted
    # 1. Create dirty files
    dirty_file = git_workspace.workspace / "dirty.txt"
    dirty_file.write_text("temporary")
    git_workspace.repo.index.add([str(dirty_file)])
    git_workspace.repo.index.commit("initial commit")
    
    dirty_file.write_text("dirty edit")
    
    # 2. Destructive reset query -> abort first
    res = git_workspace.run(["nuke working tree"], stdin_data="n\n")
    assert res.returncode == 0
    assert "Execution aborted." in res.stdout
    
    # Doctor confirms edit still present
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    assert "unstaged: 1" in res.stdout
    
    # 3. Run again and approve
    res = git_workspace.run(["-y", "nuke working tree"]) # -y skips main confirmation for destructive plan
    assert res.returncode == 0
    
    # Doctor confirms clean
    res = git_workspace.run(["doctor"])
    assert res.returncode == 0
    assert "unstaged: 0" in res.stdout or "clean" in res.stdout.lower()
