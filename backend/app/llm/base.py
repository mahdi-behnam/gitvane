from typing import Protocol


class BaseLlmClient(Protocol):
    """Interface for LLM explanation generation clients."""

    async def complete(self, messages: list[dict[str, str]]) -> str:
        """Return a chat completion for the provided messages."""
        ...
