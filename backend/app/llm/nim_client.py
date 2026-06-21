from typing import Any

import httpx


class NimLlmClient:
    """Call NVIDIA NIM chat completions for explanation text."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required for LLM explanations.")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 700,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
