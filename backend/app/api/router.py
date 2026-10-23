from fastapi import APIRouter

from app.api.routes import chat, documents, evaluation, health, providers, traces

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(traces.router)
api_router.include_router(evaluation.router)
api_router.include_router(providers.router)

