"""AI Extraction Services Package."""
from app.services.ai.gemini_provider import GeminiExtractionProvider
from app.services.ai.heuristic_provider import HeuristicExtractionProvider
from app.services.ai.provider import AIExtractionProvider

_default_ai_provider: AIExtractionProvider | None = None


def get_ai_provider() -> AIExtractionProvider:
    """Returns singleton AI extraction provider instance."""
    global _default_ai_provider
    if _default_ai_provider is None:
        _default_ai_provider = GeminiExtractionProvider()
    return _default_ai_provider


__all__ = [
    "AIExtractionProvider",
    "GeminiExtractionProvider",
    "HeuristicExtractionProvider",
    "get_ai_provider",
]
