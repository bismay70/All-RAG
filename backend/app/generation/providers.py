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


class LLMProvider:
    async def generate(self, question: str, evidence: list[SearchResult]) -> GenerationResult:
        raise NotImplementedError


class XAIProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(self, question: str, evidence: list[SearchResult]) -> GenerationResult:
        if not self.settings.grok_api_key:
            return _extractive_answer(question, evidence, ["Grok/xAI key is not configured; used local extractive synthesis."])

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
        payload = {
            "model": self.settings.grok_model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }
        url = f"{self.settings.xai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.grok_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        last_error = ""
        for attempt in range(self.settings.provider_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.settings.provider_timeout_seconds) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                answer = data["choices"][0]["message"]["content"]
                return GenerationResult(
                    answer=answer.strip(),
                    usage=data.get("usage", {}),
                    warnings=[],
                    provider="xai",
                )
            except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
                last_error = exc.__class__.__name__
                if attempt < self.settings.provider_max_retries:
                    await asyncio.sleep(0.35 * (attempt + 1))

        return _extractive_answer(
            question,
            evidence,
            [f"Grok/xAI request did not complete successfully ({last_error}); used local extractive synthesis."],
        )


def _extractive_answer(question: str, evidence: list[SearchResult], warnings: list[str] | None = None) -> GenerationResult:
    if not evidence or evidence[0].score < 0.05:
        return GenerationResult(
            answer="I do not have enough indexed evidence to answer that question reliably.",
            warnings=warnings or [],
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
    )

