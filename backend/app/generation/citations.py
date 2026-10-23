from app.retrieval.store import SearchResult
from app.schemas.common import Citation


def build_citations(results: list[SearchResult]) -> list[Citation]:
    citations: list[Citation] = []
    for index, result in enumerate(results, start=1):
        quote = result.text.strip().replace("\n", " ")
        if len(quote) > 320:
            quote = quote[:317].rsplit(" ", 1)[0] + "..."
        citations.append(
            Citation(
                source_id=f"S{index}",
                document_id=result.document_id,
                filename=result.filename,
                page=result.page,
                section=result.section,
                chunk_id=result.chunk_id,
                quote=quote,
            )
        )
    return citations

