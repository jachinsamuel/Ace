from ace.core.safety import SafetyChecker

def test_destructive_commands():
    destructive_cmds = [
        "git reset --hard",
        "git reset --hard HEAD~1",
        "git push --force",
        "git push -f",
        "git push origin main --force",
        "git clean -fd",
        "git clean -f",
        "git branch -D feature",
    ]
    for cmd in destructive_cmds:
        risk_level, explanation, alt = SafetyChecker.analyze_command(cmd)
        assert risk_level == "destructive", f"Expected '{cmd}' to be destructive"
        assert alt is not None, f"Expected an alternative command for '{cmd}'"

def test_moderate_commands():
    moderate_cmds = [
        "git commit -m 'feat: login'",
        "git push",
        "git merge feature",
        "git checkout main",
        "git rebase main",
        "git cherry-pick a1b2c3d",
        "git reset --soft HEAD~1",
        "git stash",
    ]
    for cmd in moderate_cmds:
        risk_level, explanation, alt = SafetyChecker.analyze_command(cmd)
        assert risk_level == "moderate", f"Expected '{cmd}' to be moderate"
        assert alt is None

def test_safe_commands():
    safe_cmds = [
        "git status",
        "git diff",
        "git log -n 5",
        "git branch",
        "git stash list",
    ]
    for cmd in safe_cmds:
        risk_level, explanation, alt = SafetyChecker.analyze_command(cmd)
        assert risk_level == "safe", f"Expected '{cmd}' to be safe"
        assert alt is None
