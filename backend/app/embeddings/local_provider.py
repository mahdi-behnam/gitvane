from typing import Any

import numpy as np


class LocalSentenceTransformerProvider:
    """Generate embeddings locally using sentence-transformers."""

    def __init__(
        self,
        model_name: str,
        dimensions: int,
        batch_size: int = 16,
        use_cuda_if_available: bool = True,
    ) -> None:
        self._model_name = model_name
        self._dimensions = dimensions
        self.batch_size = batch_size
        self.use_cuda_if_available = use_cuda_if_available
        self._model: Any | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    async def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return self._as_float_lists(embeddings)

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        from sentence_transformers import SentenceTransformer

        device = None
        if self.use_cuda_if_available:
            try:
                import torch

                if torch.cuda.is_available():
                    device = "cuda"
            except Exception:
                device = None

        self._model = SentenceTransformer(
            self._model_name,
            device=device,
            model_kwargs={"attn_implementation": "eager"}
        )
        return self._model

    def _as_float_lists(self, embeddings: Any) -> list[list[float]]:
        array = np.asarray(embeddings, dtype=float)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        return array.tolist()
