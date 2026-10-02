"""
Text extraction + normalization for project documents.

Output is a list of Page objects. Headings are marked as lines starting with
"## " so the chunker can track which section each sentence belongs to, and
tables are rendered as "cell | cell | cell" rows so their content is searchable
(requirement specs are full of tables).
"""
import io
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from app.core.config import settings

ALLOWED_TYPES = ("pdf", "docx", "txt", "md")


class DocumentError(Exception):
    """A problem with the uploaded file itself (bad type, corrupt, empty) — shown to the user, never retried."""


@dataclass
class Page:
    number: int | None   # 1-based page number; None when the format has no pages (docx/txt/md)
    text: str


# ── Validation ────────────────────────────────────────────────────────────────

def detect_file_type(filename: str, data: bytes) -> str:
    """Return pdf/docx/txt/md after checking BOTH the extension and the file's magic bytes."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_TYPES:
        raise DocumentError(f"Unsupported file type '.{extension}'. Upload PDF, DOCX, TXT or MD.")
    if not data:
        raise DocumentError("The file is empty.")
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise DocumentError(f"File is larger than the {settings.MAX_UPLOAD_MB} MB limit.")

    # Magic bytes: a renamed .exe must not be parsed as a PDF just because of its name
    if extension == "pdf" and not data.startswith(b"%PDF-"):
        raise DocumentError("File has a .pdf extension but is not a PDF.")
    if extension == "docx" and not data.startswith(b"PK\x03\x04"):
        raise DocumentError("File has a .docx extension but is not a Word document.")
    if extension in ("txt", "md"):
        if b"\x00" in data[:4096]:
            raise DocumentError("Text file contains binary data.")
        try:
            data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise DocumentError("Text files must be UTF-8 encoded.")
    return extension


# ── Extraction ────────────────────────────────────────────────────────────────

def _table_rows(rows: list[list]) -> list[str]:
    """Render table rows as 'a | b | c' lines, skipping empty rows."""
    lines = []
    for row in rows:
        cells = [re.sub(r"\s+", " ", str(c or "")).strip() for c in row]
        if any(cells):
            lines.append(" | ".join(cells))
    return lines


def _extract_pdf(data: bytes) -> list[Page]:
    """Extract each PDF page: body text outside tables, then the tables as pipe-separated rows."""
    import pdfplumber

    pages: list[Page] = []
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as exc:
        raise DocumentError(f"Could not open PDF: {type(exc).__name__}. The file may be corrupt or encrypted.")
    with pdf:
        if len(pdf.pages) > settings.MAX_PDF_PAGES:
            raise DocumentError(f"PDF has {len(pdf.pages)} pages; the limit is {settings.MAX_PDF_PAGES}.")
        for number, page in enumerate(pdf.pages, start=1):
            tables = page.find_tables()
            bboxes = [t.bbox for t in tables]

            def outside_tables(obj, bboxes=bboxes):
                """Keep a character only if its centre is not inside any table."""
                cx = (obj.get("x0", 0) + obj.get("x1", 0)) / 2
                cy = (obj.get("top", 0) + obj.get("bottom", 0)) / 2
                return not any(x0 <= cx <= x1 and top <= cy <= bottom for x0, top, x1, bottom in bboxes)

            body = (page.filter(outside_tables) if bboxes else page).extract_text() or ""
            table_lines = [line for t in tables for line in _table_rows(t.extract())]
            pages.append(Page(number, "\n".join([body, *table_lines]).strip()))
    return pages


def _extract_docx(data: bytes) -> list[Page]:
    """Walk the .docx body in order: Heading-styled paragraphs become '## ' lines, tables become pipe rows."""
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise DocumentError(f"Could not open Word document: {type(exc).__name__}. The file may be corrupt.")

    lines = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            para = Paragraph(child, document)
            text = para.text.strip()
            if not text:
                continue
            style = (para.style.name if para.style is not None else "") or ""
            lines.append(f"## {text}" if style.startswith(("Heading", "Title")) else text)
        elif tag == "tbl":
            table = Table(child, document)
            lines.extend(_table_rows([[cell.text for cell in row.cells] for row in table.rows]))
    return [Page(None, "\n".join(lines))]


def _extract_text_file(data: bytes, file_type: str) -> list[Page]:
    """Decode a UTF-8 text/markdown file; markdown '#' headings become '## ' markers."""
    text = data.decode("utf-8-sig")
    if file_type == "md":
        text = re.sub(r"^#{1,6}\s+", "## ", text, flags=re.MULTILINE)
    return [Page(None, text)]


def extract_pages(data: bytes, file_type: str) -> list[Page]:
    """Extract pages from a validated file, normalize them, and fail clearly if no text was found."""
    if file_type == "pdf":
        pages = _extract_pdf(data)
    elif file_type == "docx":
        pages = _extract_docx(data)
    elif file_type in ("txt", "md"):
        pages = _extract_text_file(data, file_type)
    else:
        raise DocumentError(f"Unsupported file type '{file_type}'.")

    pages = normalize_pages(pages)
    if sum(len(p.text.split()) for p in pages) < 5:
        hint = " It may be a scanned image — OCR is not supported." if file_type == "pdf" else ""
        raise DocumentError(f"No readable text found in the document.{hint}")
    return pages


# ── Normalization ─────────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    """Unicode NFKC, join words hyphenated across line breaks, collapse spaces, drop blank lines."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("­", "")                     # soft hyphen
    text = re.sub(r"\(cid:\d+\)", " ", text)               # unmapped PDF glyphs (often bullets) from pdfplumber
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # "require-\nment" -> "requirement"
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _repeated_lines(pages: list[Page]) -> set[str]:
    """Lines that appear on more than half of the pages — running headers/footers, not content."""
    if len(pages) < 3:
        return set()
    counts = Counter(line for p in pages for line in set(p.text.splitlines()))
    # A page number on its own ("Page 3 of 10", "3") differs per page, so normalize digits first
    digit_counts = Counter(
        re.sub(r"\d+", "#", line) for p in pages for line in set(p.text.splitlines())
    )
    threshold = len(pages) / 2
    repeated = {line for line, n in counts.items() if n > threshold}
    repeated |= {
        line for p in pages for line in p.text.splitlines()
        if len(line) < 40 and digit_counts[re.sub(r"\d+", "#", line)] > threshold
    }
    return repeated


def normalize_pages(pages: list[Page]) -> list[Page]:
    """Normalize every page and strip running headers/footers repeated across pages."""
    pages = [Page(p.number, _normalize_text(p.text)) for p in pages]
    noise = _repeated_lines(pages)
    if noise:
        pages = [Page(p.number, "\n".join(l for l in p.text.splitlines() if l not in noise)) for p in pages]
    return pages
