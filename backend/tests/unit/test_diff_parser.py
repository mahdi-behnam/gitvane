from app.analysis.diff_parser import DiffParser


def test_diff_parser_extracts_changed_files_and_lines() -> None:
    raw_diff = """diff --git a/src/auth.py b/src/auth.py
index 111..222 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -8,2 +8,4 @@ def validate():
+    check_expiry()
diff --git a/src/new.py b/src/new.py
new file mode 100644
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1,2 @@
+x = 1
"""

    changed = DiffParser().parse(raw_diff)

    assert changed[0].path == "src/auth.py"
    assert changed[0].change_type == "modified"
    assert changed[0].changed_lines == [(8, 11)]
    assert changed[1].path == "src/new.py"
    assert changed[1].change_type == "added"
    assert changed[1].changed_lines == [(1, 2)]


def test_diff_parser_handles_renamed_and_deleted_files() -> None:
    raw_diff = """diff --git a/src/old.py b/src/new.py
similarity index 95%
rename from src/old.py
rename to src/new.py
@@ -1 +1 @@
diff --git a/src/deleted.py b/src/deleted.py
deleted file mode 100644
--- a/src/deleted.py
+++ /dev/null
@@ -1,3 +0,0 @@
"""

    changed = DiffParser().parse(raw_diff)

    assert changed[0].path == "src/new.py"
    assert changed[0].old_path == "src/old.py"
    assert changed[0].change_type == "renamed"
    assert changed[1].path == "src/deleted.py"
    assert changed[1].change_type == "deleted"
