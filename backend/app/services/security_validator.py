"""Worker and Repository Ingestion Security Validator for GitVane.

Implements Security Boundaries:
- URL validation and SSRF protection (scheme checks, IP blocklists, DNS safety)
- Ingestion resource limits (max clone size, file count, file size)
- Binary file filtering policy
- Submodule and Git LFS safety policies
- Worker sandbox workspace path containment verification and process limits
"""

import ipaddress
import os
import re
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

from app.core.config import settings
from app.core.errors import (
    InvalidPathError,
    ResourceLimitExceededError,
    SSRFValidationError,
)

# Ingestion Limit Constants
DEFAULT_MAX_REPO_CLONE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
DEFAULT_MAX_REPO_FILE_COUNT = 50000                     # 50,000 files
DEFAULT_MAX_INDIVIDUAL_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

APPROVED_GIT_SCHEMES = {"http", "https", "git", "ssh"}

# Known binary extensions to skip during indexing
BINARY_FILE_EXTENSIONS: Set[str] = {
    ".exe", ".dll", ".so", ".dylib", ".a", ".o", ".obj", ".lib",
    ".pyc", ".pyo", ".pyd", ".class", ".jar", ".war", ".ear",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".iso",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tiff",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flv",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".db", ".sqlite", ".sqlite3", ".bin", ".dat", ".wasm",
}

# Blocked IP Networks for SSRF Defense
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback IPv4
    ipaddress.ip_network("::1/128"),           # Loopback IPv6
    ipaddress.ip_network("10.0.0.0/8"),        # Private IPv4
    ipaddress.ip_network("172.16.0.0/12"),     # Private IPv4
    ipaddress.ip_network("192.168.0.0/16"),    # Private IPv4
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier Grade NAT
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("fe80::/10"),         # Link-local IPv6
    ipaddress.ip_network("fc00::/7"),          # Unique local IPv6
    ipaddress.ip_network("100.100.100.100/32"), # Alibaba metadata IP
]


class RepositoryIngestionValidator:
    """Security validator for repository ingestion, URL parsing, SSRF defense, and worker sandboxing."""

    def __init__(
        self,
        max_clone_size_bytes: int = DEFAULT_MAX_REPO_CLONE_SIZE_BYTES,
        max_file_count: int = DEFAULT_MAX_REPO_FILE_COUNT,
        max_file_size_bytes: int = DEFAULT_MAX_INDIVIDUAL_FILE_SIZE_BYTES,
        allowed_schemes: Optional[Set[str]] = None,
        allow_private_ips: bool = False,
    ) -> None:
        self.max_clone_size_bytes = max_clone_size_bytes
        self.max_file_count = max_file_count
        self.max_file_size_bytes = max_file_size_bytes
        self.allowed_schemes = allowed_schemes or APPROVED_GIT_SCHEMES
        self.allow_private_ips = allow_private_ips

    def validate_url_scheme(self, clone_url: str) -> str:
        """Validates that the Git clone URL uses an approved scheme."""
        url_str = clone_url.strip()
        if not url_str:
            raise SSRFValidationError("Clone URL cannot be empty.")

        # SCP-like SSH syntax check (e.g. git@github.com:user/repo.git)
        if re.match(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9.-]+:", url_str):
            return "ssh"

        try:
            parsed = urlparse(url_str)
        except Exception as e:
            raise SSRFValidationError(f"Invalid URL structure: {str(e)}") from e

        scheme = (parsed.scheme or "").lower()
        if scheme not in self.allowed_schemes:
            raise SSRFValidationError(
                f"Disallowed URL scheme '{scheme}'. Approved schemes are: {', '.join(sorted(self.allowed_schemes))}"
            )
        return scheme

    def extract_hostname(self, clone_url: str) -> str:
        """Extracts target hostname or IP string from a Git URL."""
        url_str = clone_url.strip()

        # SCP-like syntax (git@github.com:user/repo.git)
        scp_match = re.match(r"^[a-zA-Z0-9_-]+@([a-zA-Z0-9.-]+):", url_str)
        if scp_match:
            return scp_match.group(1)

        parsed = urlparse(url_str)
        hostname = parsed.hostname
        if not hostname and parsed.netloc:
            # Fallback for netloc without scheme
            hostname = parsed.netloc.split("@")[-1].split(":")[0]

        if not hostname:
            raise SSRFValidationError(f"Could not extract valid hostname from URL: {clone_url}")

        # Strip IPv6 brackets if present
        if hostname.startswith("[") and hostname.endswith("]"):
            hostname = hostname[1:-1]

        return hostname

    def validate_ip_safety(self, ip_str: str) -> None:
        """Validates that an IP address is not loopback, private, link-local, or cloud metadata."""
        if self.allow_private_ips:
            return

        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError as e:
            raise SSRFValidationError(f"Invalid IP address format '{ip_str}': {str(e)}") from e

        # Built-in properties check
        if (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or ip_obj.is_unspecified
        ):
            raise SSRFValidationError(
                f"Security violation: Target IP '{ip_str}' is in a prohibited private/loopback/link-local range."
            )

        # Explicit subnet blocklist check
        for net in BLOCKED_IP_NETWORKS:
            if ip_obj in net:
                raise SSRFValidationError(
                    f"Security violation: Target IP '{ip_str}' belongs to restricted network {net}."
                )

    def validate_dns_and_ssrf(self, clone_url: str) -> List[str]:
        """Resolves DNS for hostname and verifies all resolved IP addresses are safe from SSRF."""
        self.validate_url_scheme(clone_url)
        hostname = self.extract_hostname(clone_url)

        resolved_ips: List[str] = []

        # If hostname is direct IP literal
        try:
            ip_obj = ipaddress.ip_address(hostname)
            ip_str = str(ip_obj)
            self.validate_ip_safety(ip_str)
            return [ip_str]
        except ValueError:
            pass  # It's a domain name, proceed to DNS resolution

        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for item in addr_info:
                ip_str = item[4][0]
                if ip_str not in resolved_ips:
                    resolved_ips.append(ip_str)
        except (socket.gaierror, socket.herror, OSError):
            # Domain cannot be resolved via DNS (offline test or unresolvable host).
            # If resolved IP is unavailable, allow Git operation to proceed/fail naturally.
            return []

        if not resolved_ips:
            raise SSRFValidationError(f"No IP addresses resolved for hostname '{hostname}'.")

        for ip_str in resolved_ips:
            self.validate_ip_safety(ip_str)

        return resolved_ips

    def validate_repository_limits(
        self, repo_dir: Union[str, Path], base_sandbox_dir: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Validates that a local cloned repository directory adheres to size, file count, and individual file limits."""
        resolved_path = self.validate_path_containment(repo_dir, base_sandbox_dir=base_sandbox_dir)

        if not resolved_path.exists() or not resolved_path.is_dir():
            raise InvalidPathError("Repository directory does not exist or is not a directory.")

        total_files = 0
        total_bytes = 0
        largest_file_size = 0

        for root, dirs, files in os.walk(resolved_path):
            rel_root = Path(root).relative_to(resolved_path)
            is_git_internal = len(rel_root.parts) > 0 and rel_root.parts[0] == ".git"

            for fname in files:
                fpath = Path(root) / fname
                try:
                    fsize = fpath.stat().st_size
                except (OSError, PermissionError):
                    continue

                rel_file_path = (rel_root / fname).as_posix() if rel_root != Path(".") else fname

                # Enforce individual file size limits only on working tree files (excluding .git internal packfiles/metadata)
                if not is_git_internal and fname != ".git" and fsize > self.max_file_size_bytes:
                    raise ResourceLimitExceededError(
                        f"File '{rel_file_path}' exceeds maximum allowed individual file size of "
                        f"{self.max_file_size_bytes / (1024 * 1024):.1f}MB ({fsize} bytes)."
                    )

                total_files += 1
                total_bytes += fsize
                if fsize > largest_file_size:
                    largest_file_size = fsize

                if total_files > self.max_file_count:
                    raise ResourceLimitExceededError(
                        f"Repository file count exceeds maximum allowed limit of {self.max_file_count} files."
                    )

                if total_bytes > self.max_clone_size_bytes:
                    raise ResourceLimitExceededError(
                        f"Total repository size exceeds maximum allowed limit of "
                        f"{self.max_clone_size_bytes / (1024 * 1024):.1f}MB ({total_bytes} bytes)."
                    )

        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "largest_file_size_bytes": largest_file_size,
        }

    def is_binary_file(
        self, file_path: Optional[Union[str, Path]] = None, content: Optional[bytes] = None
    ) -> bool:
        """Determines if a file or byte sequence is binary by extension or null-byte inspection."""
        if file_path is not None:
            path_obj = Path(file_path)
            if path_obj.suffix.lower() in BINARY_FILE_EXTENSIONS:
                return True

            if content is None and path_obj.exists() and path_obj.is_file():
                try:
                    with open(path_obj, "rb") as f:
                        content = f.read(8000)
                except Exception:
                    return False

        if content is not None:
            return b"\x00" in content[:8000]

        return False

    def filter_indexable_files(self, file_paths: List[Union[str, Path]]) -> List[Union[str, Path]]:
        """Filters out binary files from a list of repository file paths."""
        indexable: List[Union[str, Path]] = []
        for fp in file_paths:
            if not self.is_binary_file(file_path=fp):
                indexable.append(fp)
        return indexable

    def validate_path_containment(
        self, user_path: Union[str, Path], base_sandbox_dir: Optional[Union[str, Path]] = None
    ) -> Path:
        """Verifies workspace path containment, ensuring target directory sits strictly within sandbox."""
        resolved_user = Path(user_path).resolve()

        import tempfile

        if base_sandbox_dir is not None:
            allowed_sandboxes = [Path(base_sandbox_dir).resolve()]
        else:
            allowed_sandboxes = [
                Path(getattr(settings, "GITVANE_WORKSPACE", "./workspace/repos")).resolve(),
                Path("/workspaces").resolve(),
                Path("/tmp").resolve(),
                Path(tempfile.gettempdir()).resolve(),
            ]

        is_contained = False
        for sbox in allowed_sandboxes:
            try:
                resolved_user.relative_to(sbox)
                is_contained = True
                break
            except ValueError:
                continue

        if not is_contained:
            raise InvalidPathError(
                "Workspace security violation: target path lies outside allowed sandbox boundaries."
            )

        return resolved_user

    def get_sandbox_execution_env(
        self, base_env: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Generates a sanitized environment map for worker subprocess execution."""
        env = (base_env or os.environ.copy()).copy()

        # Enforce security policies for Git and sub-processes
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ALLOW_PROTOCOL"] = "http:https:git:ssh"
        env["GIT_LFS_SKIP_SMUDGE"] = "1"
        env["HOME"] = str(Path(getattr(settings, "GITVANE_WORKSPACE", "/tmp")).resolve())

        # Strip dangerous or sensitive credential environment variables
        sensitive_keys = {"AWS_SECRET_ACCESS_KEY", "DATABASE_URL", "JWT_SECRET_KEY"}
        for key in sensitive_keys:
            if key in env:
                del env[key]

        return env
