"""
V2 Phase 2 — validation, extraction, normalization, chunking and the upload → process pipeline.
Run from backend/: pytest tests/test_ingestion.py -v
"""
import io

import pytest

from app.services.chunking import chunk_pages, is_heading
from app.services.extraction import DocumentError, Page, detect_file_type, extract_pages, normalize_pages


# ── Sample documents built in memory ──────────────────────────────────────────

def make_docx() -> bytes:
    """A small Word spec with a heading, paragraphs and a table."""
    import docx

    document = docx.Document()
    document.add_heading("Authentication", level=1)
    document.add_paragraph("The system must issue JWT access tokens. Access tokens expire after 15 minutes.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text, table.cell(0, 1).text = "Token", "Lifetime"
    table.cell(1, 0).text, table.cell(1, 1).text = "Refresh token", "30 days"
    document.add_heading("Audit Logging", level=1)
    document.add_paragraph("Every login attempt must be written to the audit log with a timestamp.")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def make_pdf(pages: int = 3) -> bytes:
    """A multi-page PDF with a running header/footer on every page and a ruled table on page 2."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    pdf.set_auto_page_break(False)   # footer is placed manually; keep exactly one PDF page per loop
    for n in range(1, pages + 1):
        pdf.add_page()
        pdf.cell(0, 8, "ACME Corp - Confidential", new_x="LMARGIN", new_y="NEXT")
        line = dict(new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 6, f"{n}. Section {n}", **line)
        pdf.multi_cell(0, 6, f"Requirement text for section {n}. The service must respond within {n * 100} ms "
                             f"for ninety-five percent of requests under normal load.", **line)
        if n == 2:
            with pdf.table() as table:
                for row in (("Endpoint", "Limit"), ("/login", "5 per minute"), ("/token", "60 per minute")):
                    r = table.row()
                    for cell in row:
                        r.cell(cell)
        pdf.set_y(-20)
        pdf.cell(0, 8, f"Page {n} of {pages}")
    return bytes(pdf.output())


# ── Validation ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("filename, data, message", [
    ("evil.exe", b"MZ...", "Unsupported file type"),
    ("fake.pdf", b"not a pdf at all", "not a PDF"),
    ("fake.docx", b"%PDF-1.4", "not a Word document"),
    ("binary.txt", b"abc\x00def", "binary data"),
    ("latin1.txt", "café".encode("latin-1"), "UTF-8"),
    ("empty.md", b"", "empty"),
])
def test_detect_file_type_rejects_bad_files(filename, data, message):
    """Extension AND magic bytes must agree; binary/odd encodings are refused with a clear message."""
    with pytest.raises(DocumentError, match=message):
        detect_file_type(filename, data)


def test_detect_file_type_accepts_real_files():
    """Real PDF/DOCX/TXT/MD bytes are accepted."""
    assert detect_file_type("spec.PDF", make_pdf(1)) == "pdf"
    assert detect_file_type("spec.docx", make_docx()) == "docx"
    assert detect_file_type("notes.md", b"# Title\nBody") == "md"


# ── Extraction & normalization ───────────────────────────────────────────────

def test_docx_extraction_keeps_headings_and_tables():
    """Word headings become '## ' markers and table rows become pipe-separated lines."""
    text = extract_pages(make_docx(), "docx")[0].text
    assert "## Authentication" in text and "## Audit Logging" in text
    assert "Refresh token | 30 days" in text


def test_pdf_extraction_pages_tables_and_header_footer_removal():
    """PDF pages keep their numbers, tables are rendered as rows, running headers/footers are removed."""
    pages = extract_pages(make_pdf(3), "pdf")
    assert [p.number for p in pages] == [1, 2, 3]
    joined = "\n".join(p.text for p in pages)
    assert "ACME Corp - Confidential" not in joined
    assert "Page 2 of 3" not in joined
    assert "/login | 5 per minute" in pages[1].text
    assert "respond within 200 ms" in pages[1].text


def test_normalization_joins_hyphenated_words():
    """'require-\\nment' across a line break becomes 'requirement'."""
    assert "requirement" in normalize_pages([Page(1, "This require-\nment is key.")])[0].text


def test_corrupt_and_empty_documents_fail_clearly():
    """Corrupt PDFs and text-free documents raise DocumentError, not a crash."""
    with pytest.raises(DocumentError, match="Could not open PDF"):
        extract_pages(b"%PDF-1.4 garbage", "pdf")
    with pytest.raises(DocumentError, match="No readable text"):
        extract_pages(b"   \n  ", "txt")


# ── Chunking ──────────────────────────────────────────────────────────────────

def test_heading_detection():
    """Numbered and title-case headings are detected; sentences and table rows are not."""
    assert is_heading("## Authentication")
    assert is_heading("4.2 Token Refresh")
    assert is_heading("Non Functional Requirements")
    assert not is_heading("The system must log every request.")
    assert not is_heading("Endpoint | Limit")


def test_chunks_respect_size_sections_and_pages():
    """No chunk exceeds the word budget, sections never mix, and page ranges are tracked."""
    sentence = "The platform must validate every incoming payload against the published schema."  # 11 words
    pages = [
        Page(1, "## Validation\n" + " ".join([sentence] * 30)),
        Page(2, " ".join([sentence] * 10) + "\n## Logging\nAll errors must be logged with a correlation id."),
    ]
    chunks = chunk_pages(pages, max_words=60, overlap_words=15)

    assert all(c.word_count <= 60 for c in chunks)
    assert {c.section for c in chunks} == {"Validation", "Logging"}
    logging_chunk = [c for c in chunks if c.section == "Logging"]
    assert len(logging_chunk) == 1 and logging_chunk[0].content.startswith("All errors")
    assert any(c.page_start == 1 and c.page_end == 2 for c in chunks)   # a chunk spanning the page break
    # overlap: consecutive chunks in the same section share whole sentences
    first, second = chunks[0], chunks[1]
    assert second.content.split(". ")[0] in first.content


def test_oversized_sentence_is_split():
    """A single 'sentence' longer than the budget (e.g. a run-on list) is split into windows."""
    chunks = chunk_pages([Page(None, " ".join(["word"] * 250))], max_words=100, overlap_words=0)
    assert [c.word_count for c in chunks] == [100, 100, 50]


# ── Upload → process pipeline (API, Celery eager) ─────────────────────────────

def _project(client) -> str:
    """Create a project and return its id."""
    return client.post("/api/v1/projects", json={"name": "Ingestion test"}).json()["id"]


def test_upload_docx_is_processed_to_indexed(client):
    """Upload returns 201; the background task extracts and chunks it; status ends 'indexed'."""
    pid = _project(client)
    resp = client.post(f"/api/v1/projects/{pid}/documents", data={"role": "reference"},
                       files={"file": ("auth-spec.docx", make_docx())})
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]

    doc = client.get(f"/api/v1/documents/{doc_id}").json()
    assert doc["status"] == "indexed" and doc["chunk_count"] >= 2 and doc["error_message"] is None

    chunks = client.get(f"/api/v1/documents/{doc_id}/chunks").json()
    assert {c["section"] for c in chunks} >= {"Authentication", "Audit Logging"}


def test_upload_pasted_text(client):
    """Pasted text is stored as a .txt document and processed the same way."""
    pid = _project(client)
    resp = client.post(f"/api/v1/projects/{pid}/documents",
                       data={"role": "existing", "title": "Resume", "text": "Built REST APIs with FastAPI and PostgreSQL for five years."})
    assert resp.status_code == 201
    assert resp.json()["filename"] == "Resume.txt"
    assert client.get(f"/api/v1/documents/{resp.json()['id']}").json()["status"] == "indexed"


def test_duplicate_upload_returns_existing_document(client):
    """Same bytes uploaded twice → 200 with the same document, no second copy."""
    pid = _project(client)
    pdf = make_pdf(2)
    first = client.post(f"/api/v1/projects/{pid}/documents", data={"role": "reference"}, files={"file": ("a.pdf", pdf)})
    second = client.post(f"/api/v1/projects/{pid}/documents", data={"role": "reference"}, files={"file": ("b.pdf", pdf)})
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get(f"/api/v1/projects/{pid}/documents").json()) == 1


def test_bad_upload_rejected_and_corrupt_pdf_marked_failed(client):
    """A fake PDF is rejected at upload (422); a real-looking but corrupt PDF ends 'failed' with a reason."""
    pid = _project(client)
    bad = client.post(f"/api/v1/projects/{pid}/documents", data={"role": "reference"}, files={"file": ("x.pdf", b"hello")})
    assert bad.status_code == 422

    corrupt = client.post(f"/api/v1/projects/{pid}/documents", data={"role": "reference"},
                          files={"file": ("broken.pdf", b"%PDF-1.4 this is not really a pdf")})
    assert corrupt.status_code == 201
    doc = client.get(f"/api/v1/documents/{corrupt.json()['id']}").json()
    assert doc["status"] == "failed" and "Could not open PDF" in doc["error_message"]


def test_reprocess_is_idempotent(client):
    """Reprocessing replaces chunks instead of duplicating them."""
    pid = _project(client)
    doc_id = client.post(f"/api/v1/projects/{pid}/documents", data={"role": "reference"},
                         files={"file": ("spec.pdf", make_pdf(3))}).json()["id"]
    before = client.get(f"/api/v1/documents/{doc_id}/chunks").json()

    assert client.post(f"/api/v1/documents/{doc_id}/reprocess").status_code == 202
    after = client.get(f"/api/v1/documents/{doc_id}/chunks").json()
    assert len(after) == len(before)
    assert [c["chunk_index"] for c in after] == list(range(len(after)))
    assert client.get(f"/api/v1/documents/{doc_id}").json()["page_count"] == 3


def test_missing_role_or_content_rejected(client):
    """role is required and either a file or text must be sent."""
    pid = _project(client)
    assert client.post(f"/api/v1/projects/{pid}/documents", data={"text": "x"}).status_code == 422
    assert client.post(f"/api/v1/projects/{pid}/documents", data={"role": "reference"}).status_code == 422
