from ace.utils.update_checker import check_for_updates, CACHE_FILE, CHECK_INTERVAL_SECONDS
import time
import json


def test_update_checker_no_crash(monkeypatch, tmp_path):
    # Ensure CI check doesn't skip
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    fake_cache = tmp_path / "version_cache.json"
    monkeypatch.setattr("ace.utils.update_checker.CACHE_FILE", fake_cache)

    # Write old cache
    fake_cache.write_text(
        json.dumps({"last_check": time.time(), "latest_version": "0.6.3"}),
        encoding="utf-8",
    )

    # Run check_for_updates
    check_for_updates()
    assert fake_cache.exists()
