from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings
from app.observability.langsmith import langsmith_status
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.app_env,
        database="sqlite" if settings.database_url.startswith("sqlite") else "configured",
        grok_configured=settings.is_grok_configured,
        langsmith_configured=bool(langsmith_status(settings)["configured"]),
        configured_secret_names=settings.configured_secret_names,
        checked_at=datetime.now(timezone.utc),
    )

