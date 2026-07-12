"""
Phase B4 eyeball test — chunk a real document and print the first 3 chunks.
Run from the backend folder:  python scripts/test_chunking.py [path-to-text-or-docx]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.services.document_service import extract_text, chunk_text

DEFAULT_DOC = Path(__file__).parents[2] / "idea-atlas-docs" / "CLAUDE_CLI_V2_MASTER_PROMPT.md"

if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DOC
    if path.suffix == ".docx":
        text = extract_text(path.read_bytes(), "docx")
    elif path.suffix == ".pdf":
        text = extract_text(path.read_bytes(), "pdf")
    else:
        text = extract_text(path.read_text(encoding="utf-8"), "pasted")

    chunks = chunk_text(text)
    total_words = len(text.split())
    print(f"Document: {path.name} — {total_words} words -> {len(chunks)} chunks\n")

    for chunk in chunks[:3]:
        print(f"--- chunk {chunk['chunk_index']} | section: {chunk['section_hint']!r} | {len(chunk['content'].split())} words ---")
        print(chunk["content"][:300] + " ...")
        print()
