import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader

from app.core.exceptions import RAGLabError


@dataclass
class ParsedSection:
    text: str
    page: int | None = None
    section: str | None = None


SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".html", ".htm", ".docx", ".csv"}


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_bytes(filename: str, content: bytes) -> list[ParsedSection]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise RAGLabError(
            "Unsupported file type",
            status_code=415,
            detail={"supported_extensions": sorted(SUPPORTED_EXTENSIONS)},
        )

    if suffix in {".txt", ".md", ".markdown"}:
        text = content.decode("utf-8", errors="replace")
        return _split_markdown_sections(text) if suffix in {".md", ".markdown"} else [ParsedSection(normalize_text(text))]

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        sections: list[ParsedSection] = []
        for index, page in enumerate(reader.pages, start=1):
            sections.append(ParsedSection(normalize_text(page.extract_text() or ""), page=index))
        return [section for section in sections if section.text]

    if suffix in {".html", ".htm"}:
        soup = BeautifulSoup(content.decode("utf-8", errors="replace"), "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return [ParsedSection(normalize_text(soup.get_text("\n")))]

    if suffix == ".docx":
        doc = DocxDocument(io.BytesIO(content))
        paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        return [ParsedSection(normalize_text("\n".join(paragraphs)))]

    if suffix == ".csv":
        decoded = content.decode("utf-8", errors="replace")
        rows = csv.reader(io.StringIO(decoded))
        lines = [" | ".join(cell.strip() for cell in row) for row in rows]
        return [ParsedSection(normalize_text("\n".join(lines)), section="csv")]

    raise RAGLabError("Unsupported file type", status_code=415)


def _split_markdown_sections(text: str) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    current_heading = None
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append(ParsedSection(normalize_text("\n".join(current_lines)), section=current_heading))
                current_lines = []
            current_heading = line.lstrip("#").strip() or None
        current_lines.append(line)
    if current_lines:
        sections.append(ParsedSection(normalize_text("\n".join(current_lines)), section=current_heading))
    return [section for section in sections if section.text]

