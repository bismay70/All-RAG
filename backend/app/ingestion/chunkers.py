from dataclasses import dataclass

from app.ingestion.parsers import ParsedSection, normalize_text


@dataclass
class TextChunk:
    text: str
    page: int | None
    section: str | None
    token_count: int


def chunk_sections(sections: list[ParsedSection], chunk_size: int, overlap: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    step = max(1, chunk_size - overlap)
    for section in sections:
        words = section.text.split()
        if not words:
            continue
        for start in range(0, len(words), step):
            piece = words[start : start + chunk_size]
            if not piece:
                continue
            chunks.append(
                TextChunk(
                    text=normalize_text(" ".join(piece)),
                    page=section.page,
                    section=section.section,
                    token_count=len(piece),
                )
            )
            if start + chunk_size >= len(words):
                break
    return chunks

