"""
Async HTTP client for interfacing with the GitVane REST API.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import httpx

from gitvane_mcp.git_utils import (
    extract_repo_name,
    get_remote_url,
    get_repo_root,
    normalize_repo_url,
)


class GitVaneAPIError(Exception):
    """Exception raised for errors returned by the GitVane REST API."""

    def __init__(self, message: str, status_code: Optional[int] = None, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class GitVaneClient:
    """Asynchronous client communicating with the GitVane backend."""

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._cached_resolved_repo_id: Optional[str] = None

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Perform an async HTTP request to the GitVane API."""
        url = f"{self.server_url}{path}"
        headers = self._get_headers()

        # Clean params (drop None values)
        cleaned_params = {k: v for k, v in (params or {}).items() if v is not None}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=cleaned_params,
                    json=json_data,
                )
            except httpx.ConnectError as exc:
                raise GitVaneAPIError(
                    f"Could not connect to GitVane server at {self.server_url}. Is the backend running? ({exc})"
                ) from exc
            except httpx.TimeoutException as exc:
                raise GitVaneAPIError(
                    f"Request to GitVane server at {self.server_url} timed out after {self.timeout}s."
                ) from exc
            except httpx.HTTPError as exc:
                raise GitVaneAPIError(f"HTTP transport error: {exc}") from exc

        if response.is_success:
            if response.status_code == 204 or not response.content:
                return {}
            try:
                return response.json()
            except Exception as exc:
                raise GitVaneAPIError(
                    f"Invalid JSON response from server: {response.text}"
                ) from exc

        # Error response handling
        status_code = response.status_code
        detail_msg = response.text
        try:
            err_json = response.json()
            if isinstance(err_json, dict) and "detail" in err_json:
                detail_msg = err_json["detail"]
        except Exception:
            pass

        if status_code in (401, 403):
            raise GitVaneAPIError(
                f"Authentication failed ({status_code}): {detail_msg}. Check your GITVANE_API_KEY.",
                status_code=status_code,
                detail=detail_msg,
            )
        if status_code == 404:
            raise GitVaneAPIError(
                f"Resource not found ({status_code}): {detail_msg}",
                status_code=status_code,
                detail=detail_msg,
            )
        if status_code == 422:
            raise GitVaneAPIError(
                f"Validation error ({status_code}): {detail_msg}",
                status_code=status_code,
                detail=detail_msg,
            )

        raise GitVaneAPIError(
            f"GitVane API error ({status_code}): {detail_msg}",
            status_code=status_code,
            detail=detail_msg,
        )

    async def get_repositories(self, skip: int = 0, limit: int = 100) -> dict[str, Any]:
        """Fetch registered repositories from the backend."""
        return await self._request("GET", "/api/v1/repositories", params={"skip": skip, "limit": limit})

    async def resolve_repository(
        self,
        repo_hint: Optional[str] = None,
        workspace_dir: Optional[Path | str] = None,
    ) -> str:
        """
        Resolve a repository UUID from an explicit ID/name/clone_url hint or local git origin.
        Caches the resolved UUID for subsequent calls.
        """
        if self._cached_resolved_repo_id and not repo_hint:
            return self._cached_resolved_repo_id

        # 1. If repo_hint is already a valid UUID
        if repo_hint and UUID_REGEX.match(repo_hint.strip()):
            self._cached_resolved_repo_id = repo_hint.strip()
            return self._cached_resolved_repo_id

        # Fetch available repos from backend
        data = await self.get_repositories()
        items = data.get("items", [])

        if not items:
            raise GitVaneAPIError(
                "No repositories found on GitVane server. Please register and index your repository first."
            )

        # 2. Match explicit hint against ID, name, or clone URL
        if repo_hint:
            hint_norm = normalize_repo_url(repo_hint.strip())
            for r in items:
                r_id = str(r.get("id", ""))
                r_name = str(r.get("name", ""))
                r_clone = str(r.get("clone_url", ""))
                if (
                    repo_hint == r_id
                    or repo_hint.lower() == r_name.lower()
                    or (r_clone and hint_norm == normalize_repo_url(r_clone))
                    or (r_clone and repo_hint.lower() == r_clone.lower())
                ):
                    self._cached_resolved_repo_id = r_id
                    return r_id

        # 3. Detect from local git origin URL or directory name
        local_ws = Path(workspace_dir).resolve() if workspace_dir else Path.cwd()
        remote_url = get_remote_url(local_ws)
        repo_root = get_repo_root(local_ws)
        local_name = repo_root.name if repo_root else local_ws.name

        if remote_url:
            norm_remote = normalize_repo_url(remote_url)
            remote_repo_name = extract_repo_name(remote_url)
            for r in items:
                r_id = str(r.get("id", ""))
                r_name = str(r.get("name", ""))
                r_clone = str(r.get("clone_url", ""))
                if (
                    (r_clone and norm_remote == normalize_repo_url(r_clone))
                    or r_name.lower() == remote_repo_name.lower()
                ):
                    self._cached_resolved_repo_id = r_id
                    return r_id

        # 4. Try matching local directory name
        if local_name:
            for r in items:
                if str(r.get("name", "")).lower() == local_name.lower():
                    r_id = str(r.get("id", ""))
                    self._cached_resolved_repo_id = r_id
                    return r_id

        # 5. If only a single repository is registered on the server, default to it
        if len(items) == 1:
            r_id = str(items[0]["id"])
            self._cached_resolved_repo_id = r_id
            return r_id

        # Ambiguity error with helpful details
        available_names = [f"{r.get('name')} (id: {r.get('id')})" for r in items]
        raise GitVaneAPIError(
            f"Could not automatically resolve repository. Multiple repositories registered on server: "
            f"{', '.join(available_names)}. Specify your repository via --repo or GITVANE_REPO_ID."
        )

    async def analyze_impact(
        self,
        repository_id: str,
        changed_files: Optional[list[dict[str, Any]]] = None,
        raw_diff: Optional[str] = None,
        base_ref: Optional[str] = None,
        head_ref: Optional[str] = None,
        top_k: int = 20,
        include_explanation: bool = True,
        max_dependency_depth: int = 3,
        include_changed_files_in_predictions: bool = False,
    ) -> dict[str, Any]:
        """Call POST /api/v1/impact/analyze."""
        payload: dict[str, Any] = {
            "repository_id": repository_id,
            "top_k": top_k,
            "include_explanation": include_explanation,
            "max_dependency_depth": max_dependency_depth,
            "include_changed_files_in_predictions": include_changed_files_in_predictions,
        }
        if raw_diff:
            payload["raw_diff"] = raw_diff
        if changed_files is not None:
            payload["changed_files"] = changed_files
        if base_ref:
            payload["base_ref"] = base_ref
        if head_ref:
            payload["head_ref"] = head_ref

        return await self._request("POST", "/api/v1/impact/analyze", json_data=payload)

    async def recommend_tests(
        self,
        repository_id: str,
        changed_files: Optional[list[dict[str, Any]]] = None,
        impacted_files: Optional[list[str]] = None,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Call POST /api/v1/tests/recommend."""
        payload: dict[str, Any] = {
            "repository_id": repository_id,
            "changed_files": changed_files or [],
            "impacted_files": impacted_files or [],
            "top_k": top_k,
        }
        return await self._request("POST", "/api/v1/tests/recommend", json_data=payload)

    async def get_file_risk(
        self,
        repository_id: str,
        file_path: Optional[str] = None,
        top_k: int = 20,
        language: Optional[str] = None,
        include_tests: bool = False,
    ) -> dict[str, Any]:
        """Call GET /api/v1/risk/repositories/{repository_id}/files."""
        params: dict[str, Any] = {
            "top_k": top_k,
            "include_tests": include_tests,
        }
        if language:
            params["language"] = language
        if file_path:
            params["path_search"] = file_path

        return await self._request(
            "GET", f"/api/v1/risk/repositories/{repository_id}/files", params=params
        )
