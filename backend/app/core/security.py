import os
from pathlib import Path

from app.core.config import settings
from app.core.errors import InvalidPathError


def validate_and_resolve_path(
    user_path: str | Path, sandbox_dir: str | Path | None = None
) -> Path:
    """
    Resolve user_path fully and verify it is strictly inside the sandbox directory.

    Default sandbox directory is settings.GITVANE_WORKSPACE.
    """
    if sandbox_dir is None:
        sandbox_dir = settings.GITVANE_WORKSPACE

    resolved_sandbox = Path(sandbox_dir).resolve()
    resolved_user = Path(user_path).resolve()

    # Ensure the sandbox prefix ends with a separator to prevent partial-prefix
    # bypasses, e.g. sandbox=/workspace/repos, user=/workspace/repos-malicious.
    sandbox_prefix = str(resolved_sandbox)
    if not sandbox_prefix.endswith(os.sep):
        sandbox_prefix += os.sep

    user_str = str(resolved_user)

    # Check if the user path is exactly the sandbox directory or sits inside it.
    if user_str != str(resolved_sandbox) and not user_str.startswith(sandbox_prefix):
        # We raise a custom error that gets handled globally
        raise InvalidPathError(
            "Access denied: target path lies outside allowed sandbox boundary."
        )

    return resolved_user
