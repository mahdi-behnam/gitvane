from typing import Any

import numpy as np


_MODEL_CACHE: dict[tuple[str, str | None, str | None], Any] = {}


class LocalSentenceTransformerProvider:
    """Generate embeddings locally using sentence-transformers."""

    def __init__(
        self,
        model_name: str,
        dimensions: int,
        batch_size: int = 16,
        use_cuda_if_available: bool = True,
        revision: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._dimensions = dimensions
        self.batch_size = batch_size
        self.use_cuda_if_available = use_cuda_if_available
        self.revision = revision
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
        # Truncate raw text chunks to 2048 characters (~512 tokens) to prevent quadratic O(N^2) attention stalls
        # and ensure non-empty strings to prevent zero-norm division NaNs
        safe_texts = [
            (t[:2048] if len(t) > 2048 else t) if (t and t.strip()) else " "
            for t in texts
        ]
        model = self._load_model()
        try:
            import torch

            with torch.inference_mode():
                embeddings = model.encode(
                    safe_texts,
                    batch_size=self.batch_size,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
        except Exception:
            embeddings = model.encode(
                safe_texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        return self._as_float_lists(embeddings)

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        device = None
        if self.use_cuda_if_available:
            try:
                import torch

                if torch.cuda.is_available():
                    device = "cuda"
            except Exception:
                device = None

        cache_key = (self._model_name, self.revision, device)
        if cache_key in _MODEL_CACHE:
            self._model = _MODEL_CACHE[cache_key]
            return self._model

        from sentence_transformers import SentenceTransformer

        try:
            # Try loading cached weights from local disk first without remote network roundtrips
            model = SentenceTransformer(
                self._model_name,
                device=device,
                revision=self.revision,
                model_kwargs={"attn_implementation": "eager"},
                local_files_only=True,
            )
        except Exception:
            # Fallback to downloading if weights are not yet cached locally
            model = SentenceTransformer(
                self._model_name,
                device=device,
                revision=self.revision,
                model_kwargs={"attn_implementation": "eager"},
            )
        _MODEL_CACHE[cache_key] = model
        self._model = model
        return self._model

    def _as_float_lists(self, embeddings: Any) -> list[list[float]]:
        array = np.asarray(embeddings, dtype=float)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        array = np.nan_to_num(array, nan=0.0, posinf=1.0, neginf=-1.0)
        return array.tolist()
