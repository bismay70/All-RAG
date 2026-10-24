import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings
from app.retrieval.store import SearchResult


@dataclass
class GenerationResult:
    answer: str
    usage: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    provider: str = "extractive"
    model: str | None = None


class LLMProvider:
    async def generate(self, question: str, evidence: list[SearchResult]) -> GenerationResult:
        raise NotImplementedError


class GroqClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.groq_base_url.rstrip("/")

    @property
    def configured(self) -> bool:
        return self.settings.is_groq_configured

    def _headers(self) -> dict[str, str]:
        if not self.settings.groq_api_key:
            return {}
        return {
            "Authorization": f"Bearer {self.settings.groq_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        async with httpx.AsyncClient(timeout=self.settings.provider_timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/models", headers=self._headers())
            response.raise_for_status()
            data = response.json()
        models = data.get("data", [])
        return models if isinstance(models, list) else []

    async def select_chat_model(self) -> tuple[str, list[str]]:
        warnings: list[str] = []
        configured_model = self.settings.groq_model.strip()
        candidate = configured_model or self.settings.groq_default_model

        if not self.configured:
            return candidate, ["GROQ_API_KEY is not configured; used local extractive synthesis."]

        try:
            models = await self.list_models()
        except httpx.HTTPStatusError as exc:
            return candidate, [_groq_http_error_message(exc)]
        except httpx.HTTPError as exc:
            return candidate, [f"Groq model discovery failed due to a network error ({exc.__class__.__name__})."]

        model_ids = {str(model.get("id")) for model in models if model.get("id")}
        if not model_ids:
            warnings.append("Groq model discovery returned no models; using configured default.")
            return candidate, warnings

        if candidate not in model_ids:
            if configured_model:
                warnings.append(f"Configured GROQ_MODEL '{configured_model}' is unavailable to this API key.")
            if self.settings.groq_default_model in model_ids:
                return self.settings.groq_default_model, warnings
            chat_like = sorted(model_id for model_id in model_ids if _looks_like_chat_model(model_id))
            if chat_like:
                warnings.append(f"Selected available Groq chat-capable model '{chat_like[0]}'.")
                return chat_like[0], warnings
            warnings.append("No available Groq model looked chat-capable; using local extractive synthesis.")
            return candidate, warnings

        return candidate, warnings

    async def chat_completion(self, messages: list[dict[str, str]], model: str) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.settings.provider_timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

    async def extract_graph_entities(self, text: str, model: str | None = None) -> dict[str, Any]:
        selected_model = model or (await self.select_chat_model())[0]
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract a compact JSON object with keys entities and relationships. "
                    "Each entity should have name and type. Each relationship should have source, target, and label."
                ),
            },
            {"role": "user", "content": text[:6000]},
        ]
        data = await self.chat_completion(messages, selected_model)
        content = data["choices"][0]["message"]["content"]
        return {"model": selected_model, "raw": content}


class GroqProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = GroqClient(settings)

    async def generate(self, question: str, evidence: list[SearchResult]) -> GenerationResult:
        selected_model, warnings = await self.client.select_chat_model()
        if warnings and any("GROQ_API_KEY" in warning or "No available Groq model" in warning for warning in warnings):
            return _extractive_answer(question, evidence, warnings, selected_model)

        sources = "\n\n".join(
            f"[S{index}] {item.filename} chunk={item.chunk_id} score={item.score:.3f}\n{item.text[:1600]}"
            for index, item in enumerate(evidence, start=1)
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are RAGLab AI. Answer only from the supplied evidence. "
                    "Use inline citations like [S1]. If the evidence is insufficient, say so plainly."
                ),
            },
            {"role": "user", "content": f"Question: {question}\n\nEvidence:\n{sources}"},
        ]

        last_warning = ""
        for attempt in range(self.settings.provider_max_retries + 1):
            try:
                data = await self.client.chat_completion(messages, selected_model)
                answer = data["choices"][0]["message"]["content"]
                return GenerationResult(
                    answer=answer.strip(),
                    usage=data.get("usage", {}),
                    warnings=warnings,
                    provider="groq",
                    model=selected_model,
                )
            except httpx.HTTPStatusError as exc:
                last_warning = _groq_http_error_message(exc)
                if exc.response.status_code in {401, 403, 404, 429}:
                    break
            except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
                last_warning = f"Groq request failed due to {exc.__class__.__name__}."
            if attempt < self.settings.provider_max_retries:
                await asyncio.sleep(0.35 * (attempt + 1))

        return _extractive_answer(question, evidence, [*warnings, f"{last_warning} Used local extractive synthesis."], selected_model)


def _looks_like_chat_model(model_id: str) -> bool:
    lowered = model_id.lower()
    exclusions = ("whisper", "tts", "embedding", "guard")
    return not any(excluded in lowered for excluded in exclusions)


def _groq_http_error_message(exc: httpx.HTTPStatusError) -> str:
    status = exc.response.status_code
    if status in {401, 403}:
        return "Groq API key was rejected. Check GROQ_API_KEY without exposing it."
    if status == 404:
        return "Groq model or endpoint was not found. Check GROQ_MODEL and model availability."
    if status == 429:
        return "Groq rate limit was reached. Try again later or reduce request volume."
    if 500 <= status:
        return "Groq service is temporarily unavailable."
    return f"Groq request failed with HTTP {status}."


def _extractive_answer(
    question: str,
    evidence: list[SearchResult],
    warnings: list[str] | None = None,
    model: str | None = None,
) -> GenerationResult:
    if not evidence or evidence[0].score < 0.05:
        return GenerationResult(
            answer="I do not have enough indexed evidence to answer that question reliably.",
            warnings=warnings or [],
            model=model,
        )
    selected = []
    for index, item in enumerate(evidence[:3], start=1):
        snippet = item.text.strip().replace("\n", " ")
        if len(snippet) > 420:
            snippet = snippet[:417].rsplit(" ", 1)[0] + "..."
        selected.append(f"[S{index}] {snippet}")
    return GenerationResult(
        answer="Based on the indexed evidence: " + " ".join(selected),
        warnings=warnings or [],
        model=model,
    )
