import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol


TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{1,}")


class EmbeddingProvider(Protocol):
    name: str
    dimensions: int
    warning: str | None

    def embed(self, text: str) -> list[float]: ...


class SentenceTransformersEmbeddingProvider:
    def __init__(self, model_name: str, dimensions: int = 384) -> None:
        self.model_name = model_name
        self.dimensions = dimensions
        self.name = f"sentence-transformers/{model_name}"
        self.warning: str | None = None
        try:
            self._model = _load_sentence_transformer(model_name)
        except Exception as exc:
            self._model = None
            self.name = f"hashing-fallback/{dimensions}"
            self.warning = (
                f"Sentence Transformers model '{model_name}' is unavailable locally "
                f"({exc.__class__.__name__}); using deterministic local fallback embeddings."
            )

    def embed(self, text: str) -> list[float]:
        if self._model is not None:
            vector = self._model.encode(text, normalize_embeddings=True)
            return [float(value) for value in vector]
        return _hash_embed(text, self.dimensions)


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _hash_embed(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    for token in TOKEN_RE.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
