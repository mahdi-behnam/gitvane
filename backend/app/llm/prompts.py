import json
from typing import Any

SYSTEM_EXPLANATION_PROMPT = """
You are RepoLens' explanation layer.
Explain change impact predictions using only the structured evidence provided.
Do not invent dependencies, changed symbols, files, tests, or certainty.
Never change scores or introduce new rankings.
Use cautious phrases such as "likely impacted" and "evidence suggests".
Keep the answer concise and useful.
"""


def build_impact_explanation_messages(evidence: dict[str, Any]) -> list[dict[str, str]]:
    """Build NIM chat messages for structured impact evidence."""
    return [
        {"role": "system", "content": SYSTEM_EXPLANATION_PROMPT.strip()},
        {
            "role": "user",
            "content": (
                "Summarize this RepoLens impact analysis evidence.\n\n"
                "Return:\n"
                "1. Short summary.\n"
                "2. Top impacted files with reasons.\n"
                "3. Suggested tests.\n"
                "4. Main uncertainty or limitation.\n\n"
                "Structured evidence JSON:\n"
                f"{json.dumps(evidence, indent=2, sort_keys=True)}"
            ),
        },
    ]
