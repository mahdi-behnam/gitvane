from typing import Any

import httpx


class NimEmbeddingProvider:
    """Generate embeddings using NVIDIA NIM's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        dimensions: int,
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._dimensions = dimensions
        self.timeout_seconds = timeout_seconds

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts, input_type="passage")

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([text], input_type="query"))[0]

    async def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required for NIM embeddings.")

        payload: dict[str, Any] = {
            "model": self._model_name,
            "input": texts,
            "input_type": input_type,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        data = response.json()["data"]
        return [item["embedding"] for item in data]
