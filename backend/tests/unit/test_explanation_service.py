import pytest

from app.core.config import settings
from app.schemas.impact import (
    ChangedFileInput,
    ChangedSymbolOut,
    ImpactedFileOut,
    ImpactReasonOut,
)
from app.schemas.impact import (
    TestRecommendationOut as RecommendationOut,
)
from app.services.explanation_service import ExplanationService


class _FakeLlmClient:
    def __init__(self, response: str = "LLM explanation") -> None:
        self.response = response
        self.messages: list[dict[str, str]] = []

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return self.response


class _FailingLlmClient:
    async def complete(self, messages: list[dict[str, str]]) -> str:
        raise RuntimeError("service unavailable")


def _evidence() -> tuple[
    list[ChangedFileInput],
    list[ChangedSymbolOut],
    list[ImpactedFileOut],
    list[RecommendationOut],
]:
    changed_files = [ChangedFileInput(path="src/auth/token.py")]
    changed_symbols = [
        ChangedSymbolOut(
            path="src/auth/token.py",
            qualified_name="validate_token",
            symbol_type="function",
            start_line=10,
            end_line=20,
        )
    ]
    predictions = [
        ImpactedFileOut(
            rank=1,
            path="src/api/routes.py",
            score=0.87,
            component_scores={
                "dependency": 1.0,
                "semantic": 0.7,
                "cochange": 0.3,
                "test": 0.0,
                "risk": 0.5,
            },
            reasons=[
                ImpactReasonOut(
                    type="dependency",
                    message="Depends on changed file",
                    confidence=1.0,
                    evidence={"distance": 1},
                )
            ],
        )
    ]
    tests = [
        RecommendationOut(
            path="tests/test_routes.py",
            score=0.91,
            reason="Imports impacted file",
            linked_files=["src/api/routes.py"],
        )
    ]
    return changed_files, changed_symbols, predictions, tests


@pytest.mark.asyncio()
async def test_explanation_service_uses_llm_with_structured_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ENABLE_LLM_EXPLANATIONS", True)
    client = _FakeLlmClient()
    service = ExplanationService(llm_client=client)

    explanation = await service.explain_impact_prediction(*_evidence())

    assert explanation == "LLM explanation"
    assert "only summarize" in client.messages[1]["content"]
    assert "src/api/routes.py" in client.messages[1]["content"]
    assert "Never change scores" in client.messages[0]["content"]


@pytest.mark.asyncio()
async def test_explanation_service_falls_back_when_llm_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ENABLE_LLM_EXPLANATIONS", True)
    service = ExplanationService(llm_client=_FailingLlmClient())

    explanation = await service.explain_impact_prediction(*_evidence())

    assert "Based only on indexed dependency" in explanation
    assert "src/auth/token.py" in explanation


@pytest.mark.asyncio()
async def test_explanation_service_respects_disabled_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ENABLE_LLM_EXPLANATIONS", False)
    client = _FakeLlmClient()
    service = ExplanationService(llm_client=client)

    explanation = await service.explain_impact_prediction(*_evidence())

    assert "Based only on indexed dependency" in explanation
    assert client.messages == []
