import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChangedFile:
    path: str
    change_type: str = "modified"
    changed_lines: list[tuple[int, int]] = field(default_factory=list)
    old_path: str | None = None


class DiffParser:
    """Parse unified diffs into changed files and changed line ranges."""

    DIFF_HEADER = re.compile(r"^diff --git a/(.*?) b/(.*)$")
    HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    def parse(self, raw_diff: str) -> list[ChangedFile]:
        files: list[ChangedFile] = []
        current_path: str | None = None
        old_path: str | None = None
        change_type = "modified"
        changed_lines: list[tuple[int, int]] = []

        def flush() -> None:
            if current_path is None:
                return
            files.append(
                ChangedFile(
                    path=current_path,
                    change_type=change_type,
                    changed_lines=list(changed_lines),
                    old_path=old_path,
                )
            )

        for line in raw_diff.splitlines():
            header = self.DIFF_HEADER.match(line)
            if header:
                flush()
                old_path = header.group(1)
                current_path = header.group(2)
                change_type = "modified"
                changed_lines = []
                continue

            if current_path is None:
                continue

            if line.startswith("new file mode"):
                change_type = "added"
            elif line.startswith("deleted file mode"):
                change_type = "deleted"
                current_path = old_path
            elif line.startswith("rename from "):
                old_path = line.removeprefix("rename from ").strip()
                change_type = "renamed"
            elif line.startswith("rename to "):
                current_path = line.removeprefix("rename to ").strip()
            elif hunk := self.HUNK_HEADER.match(line):
                start = int(hunk.group(1))
                length = int(hunk.group(2) or "1")
                if length > 0:
                    changed_lines.append((start, start + length - 1))

        flush()
        return files
