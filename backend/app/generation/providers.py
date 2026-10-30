import asyncio
import re
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
                    "Do not paste raw chunks. Return concise Markdown in exactly this shape:\n\n"
                    "## Answer\n"
                    "- One useful point with an inline citation like [S1].\n"
                    "- Another useful point with an inline citation.\n\n"
                    "## Sources\n"
                    "- [S1] Short source label.\n\n"
                    "## Caveats\n"
                    "- Mention missing or weak evidence only when relevant.\n\n"
                    "If the evidence is insufficient, say so plainly under Answer."
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

    question_terms = _content_terms(question)
    candidates: list[tuple[float, int, str]] = []
    for source_index, item in enumerate(evidence[:5], start=1):
        source_weight = max(0.0, item.score) + (0.1 / source_index)
        for sentence_index, sentence in enumerate(_candidate_sentences(item.text)):
            terms = _content_terms(sentence)
            overlap = len(question_terms.intersection(terms))
            has_signal = overlap > 0 or sentence_index < 2
            if not has_signal:
                continue
            score = source_weight + (overlap * 0.4) - (sentence_index * 0.02)
            candidates.append((score, source_index, sentence))

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[int, str]] = []
    seen: set[str] = set()
    for _, source_index, sentence in candidates:
        key = _dedupe_key(sentence)
        if key in seen:
            continue
        seen.add(key)
        selected.append((source_index, sentence))
        if len(selected) == 4:
            break

    if not selected:
        selected = [
            (index, _shorten(_clean_evidence_text(item.text), 240))
            for index, item in enumerate(evidence[:3], start=1)
            if _clean_evidence_text(item.text)
        ]

    bullets = "\n".join(f"- {sentence} [S{source_index}]" for source_index, sentence in selected)
    source_names = "; ".join(
        f"[S{index}] {item.filename}{f' p.{item.page}' if item.page else ''}"
        for index, item in enumerate(evidence[: min(len(evidence), 3)], start=1)
    )
    source_bullets = "\n".join(
        f"- [S{index}] {item.filename}{f' p.{item.page}' if item.page else ''}"
        for index, item in enumerate(evidence[: min(len(evidence), 3)], start=1)
    )
    caveat = (
        "- Groq was unavailable, so this was generated with local extractive synthesis."
        if warnings
        else "- None."
    )
    return GenerationResult(
        answer=(
            "## Answer\n\n"
            f"{bullets}\n\n"
            "## Sources\n\n"
            f"{source_bullets or f'- {source_names}'}\n\n"
            "## Caveats\n\n"
            f"{caveat}"
        ),
        warnings=warnings or [],
        model=model,
    )


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "with",
}


def _content_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
        if token not in _STOPWORDS
    }


def _candidate_sentences(text: str) -> list[str]:
    cleaned = _clean_evidence_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+|(?:\s+-\s+)|(?:\s+#{1,6}\s+)", cleaned)
    sentences: list[str] = []
    for part in parts:
        sentence = _shorten(_clean_sentence(part), 260)
        word_count = len(sentence.split())
        if 6 <= word_count <= 55 and not _is_low_value_sentence(sentence):
            sentences.append(sentence)
    return sentences


def _clean_evidence_text(text: str) -> str:
    cleaned = re.sub(r"【\d+†[^】]+】", "", text)
    cleaned = re.sub(r"[/\\](?:envel|linkedin|github|code|gl|phone)[^\s]*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"#{1,6}\s*", " ", cleaned)
    cleaned = cleaned.replace("�", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _clean_sentence(text: str) -> str:
    cleaned = text.strip(" -:;")
    cleaned = re.sub(r"^(?:Q\d+[.)]?\s*)+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(?:Ans(?:wer)?|A)[.:]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -:;")


def _is_low_value_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    if sentence.endswith("?"):
        return True
    if re.match(r"^q\d+[.)]?\b", lowered):
        return True
    if any(token in lowered for token in ("youtube.com", "linkedin.com", "github.com", "leetcode", "codeforces")):
        return True
    if re.search(r"\bpage\s+\d+\b", lowered) and len(sentence.split()) < 24:
        return True
    if "complete notes" in lowered and len(sentence.split()) < 28:
        return True
    if len(re.findall(r"\b(?:http|www\.|\.com|\.in)\b", lowered)) >= 1:
        return True
    return False


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    shortened = text[: limit - 3].rsplit(" ", 1)[0]
    return f"{shortened}..."


def _dedupe_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())[:96]
