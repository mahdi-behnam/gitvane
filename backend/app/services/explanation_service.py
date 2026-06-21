from typing import Any

from app.core.config import settings
from app.llm.base import BaseLlmClient
from app.llm.nim_client import NimLlmClient
from app.llm.prompts import build_impact_explanation_messages
from app.schemas.impact import (
    ChangedFileInput,
    ChangedSymbolOut,
    ImpactedFileOut,
    TestRecommendationOut,
)


class ExplanationService:
    """Generate LLM explanations from computed evidence with deterministic fallback."""

    def __init__(self, llm_client: BaseLlmClient | None = None) -> None:
        self.llm_client = llm_client

    async def explain_impact_prediction(
        self,
        changed_files: list[ChangedFileInput],
        changed_symbols: list[ChangedSymbolOut],
        predictions: list[ImpactedFileOut],
        recommended_tests: list[TestRecommendationOut],
    ) -> str:
        evidence = self._build_evidence(
            changed_files,
            changed_symbols,
            predictions,
            recommended_tests,
        )
        if settings.ENABLE_LLM_EXPLANATIONS:
            try:
                client = self.llm_client or self._build_default_client()
                return await client.complete(build_impact_explanation_messages(evidence))
            except Exception:
                pass
        return self._fallback_explanation(
            changed_files,
            changed_symbols,
            predictions,
            recommended_tests,
        )

    def _build_default_client(self) -> BaseLlmClient:
        return NimLlmClient(
            api_key=settings.NVIDIA_API_KEY or "",
            base_url=settings.NVIDIA_BASE_URL,
            model=settings.NVIDIA_LLM_MODEL,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )

    def _build_evidence(
        self,
        changed_files: list[ChangedFileInput],
        changed_symbols: list[ChangedSymbolOut],
        predictions: list[ImpactedFileOut],
        recommended_tests: list[TestRecommendationOut],
    ) -> dict[str, Any]:
        return {
            "instruction": (
                "This evidence was computed before the LLM step. The LLM may only "
                "summarize it and must not alter scores, add files, or add tests."
            ),
            "changed_files": [item.model_dump() for item in changed_files],
            "changed_symbols": [item.model_dump() for item in changed_symbols],
            "predictions": [
                {
                    "rank": item.rank,
                    "path": item.path,
                    "score": item.score,
                    "component_scores": item.component_scores,
                    "reasons": [reason.model_dump() for reason in item.reasons],
                    "recommended_tests": [
                        test.model_dump() for test in item.recommended_tests
                    ],
                }
                for item in predictions
            ],
            "recommended_tests": [item.model_dump() for item in recommended_tests],
        }

    def _fallback_explanation(
        self,
        changed_files: list[ChangedFileInput],
        changed_symbols: list[ChangedSymbolOut],
        predictions: list[ImpactedFileOut],
        recommended_tests: list[TestRecommendationOut],
    ) -> str:
        changed = ", ".join(item.path for item in changed_files) or "unknown files"
        top_files = ", ".join(item.path for item in predictions[:3]) or "no files"
        tests = ", ".join(item.path for item in recommended_tests[:3]) or "no tests"
        symbol_note = (
            f" Changed symbols: {', '.join(item.qualified_name for item in changed_symbols[:5])}."
            if changed_symbols
            else ""
        )
        return (
            "Based only on indexed dependency, semantic, co-change, test, and "
            f"risk evidence, changes in {changed} likely impact {top_files}."
            f"{symbol_note} Suggested tests: {tests}. Scores are heuristic and "
            "should be reviewed with the underlying reasons."
        )
