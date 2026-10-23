from app.core.config import Settings


def langsmith_status(settings: Settings) -> dict[str, object]:
    configured = bool(settings.langsmith_tracing and settings.langsmith_api_key)
    return {
        "configured": configured,
        "project": settings.langsmith_project if configured else None,
        "mode": "langsmith" if configured else "local_tracing",
    }

