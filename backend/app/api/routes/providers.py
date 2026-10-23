from fastapi import APIRouter

from app.core.config import get_settings
from app.observability.langsmith import langsmith_status

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/status")
def provider_status() -> dict:
    settings = get_settings()
    x_configured = bool(settings.x_bearer_token or (settings.x_api_key and settings.x_api_secret))
    return {
        "llm": {
            "provider": "xai",
            "configured": settings.is_grok_configured,
            "model": settings.grok_model if settings.is_grok_configured else None,
            "status": "configured" if settings.is_grok_configured else "missing_api_key",
        },
        "embeddings": {
            "provider": "local_hashing",
            "configured": True,
            "dimensions": settings.embedding_dimensions,
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

