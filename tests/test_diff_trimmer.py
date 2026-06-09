from ace.utils.diff_parser import trim_diff

def test_trim_diff_small():
    diff = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new"
    assert trim_diff(diff, max_chars=1000) == diff

def test_trim_diff_multi_file():
    diff1 = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
    diff2 = "diff --git a/b.txt b/b.txt\n--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-abc\n+xyz\n"
    combined = diff1 + diff2
    
    # Set limit so only the first file fits
    res = trim_diff(combined, max_chars=len(diff1) + 20)
    assert "a.txt" in res
    assert "b.txt" in res
    assert "omitted" in res

def test_trim_diff_single_huge_file():
    large_line = "a" * 100
    lines = [
        "diff --git a/a.txt b/a.txt",
        "--- a/a.txt",
        "+++ b/a.txt",
        "@@ -1,10 +1,10 @@"
    ] + [large_line] * 20
    diff = "\n".join(lines)
    
    # Set limit to truncate line-by-line
    res = trim_diff(diff, max_chars=500)
    assert "file diff truncated due to size" in res
    assert len(res) <= 550
