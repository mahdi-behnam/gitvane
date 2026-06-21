from app.schemas.impact import (
    ChangedFileInput,
    ChangedSymbolOut,
    ImpactedFileOut,
    TestRecommendationOut,
)


class ExplanationService:
    """Generate deterministic fallback explanations for impact predictions."""

    async def explain_impact_prediction(
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
