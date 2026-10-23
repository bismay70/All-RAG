import math
from collections import Counter

from app.retrieval.embeddings import TOKEN_RE


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def lexical_scores(query: str, documents: dict[str, str]) -> dict[str, float]:
    query_terms = tokenize(query)
    if not query_terms or not documents:
        return {chunk_id: 0.0 for chunk_id in documents}

    doc_tokens = {chunk_id: tokenize(text) for chunk_id, text in documents.items()}
    doc_freq: Counter[str] = Counter()
    for tokens in doc_tokens.values():
        doc_freq.update(set(tokens))

    total_docs = len(documents)
    avg_len = sum(len(tokens) for tokens in doc_tokens.values()) / max(total_docs, 1)
    scores: dict[str, float] = {}
    k1 = 1.5
    b = 0.75
    for chunk_id, tokens in doc_tokens.items():
        counts = Counter(tokens)
        score = 0.0
        doc_len = len(tokens) or 1
        for term in query_terms:
            if counts[term] == 0:
                continue
            idf = math.log(1 + (total_docs - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            denom = counts[term] + k1 * (1 - b + b * doc_len / max(avg_len, 1))
            score += idf * (counts[term] * (k1 + 1)) / denom
        scores[chunk_id] = score
    max_score = max(scores.values(), default=0.0) or 1.0
    return {chunk_id: score / max_score for chunk_id, score in scores.items()}

