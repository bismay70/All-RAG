from importlib.util import find_spec

from fastapi import APIRouter

from app.core.config import get_settings
from app.generation.providers import GroqClient
from app.observability.langsmith import langsmith_status

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/status")
async def provider_status() -> dict:
    settings = get_settings()
    x_configured = bool(settings.x_bearer_token or (settings.x_api_key and settings.x_api_secret))
    groq_client = GroqClient(settings)
    selected_model, model_warnings = await groq_client.select_chat_model()
    sentence_transformers_available = find_spec("sentence_transformers") is not None
    return {
        "llm": {
            "provider": "groq",
            "configured": settings.is_groq_configured,
            "model": selected_model if settings.is_groq_configured else None,
            "base_url": settings.groq_base_url,
            "status": "configured" if settings.is_groq_configured and not model_warnings else "warning",
            "warnings": model_warnings,
        },
        "embeddings": {
            "provider": "sentence_transformers",
            "configured": sentence_transformers_available,
            "model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
            "status": "configured" if sentence_transformers_available else "package_missing_fallback_active",
        },
        "vector_store": {
            "provider": "sqlite_local",
            "configured": True,
            "status": "local development adapter",
        },
        "x_api": {
            "configured": x_configured,
            "status": "credentials_present_unverified" if x_configured else "disabled_missing_credentials",
            "note": "X retrieval is optional and is not simulated when API access is unavailable.",
        },
        "langsmith": langsmith_status(settings),
    }

