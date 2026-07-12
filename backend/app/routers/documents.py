from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import DocumentMapResponse
from app.services.document_service import create_document_map

router = APIRouter(prefix="/documents", tags=["documents"])

_EXTENSION_TO_SOURCE = {"docx": "docx", "pdf": "pdf", "txt": "pasted", "md": "pasted"}


# POST /documents
# Two accepted request shapes:
#   multipart/form-data with a "file" field (.docx / .pdf / .txt / .md)
#   application/json: {"text": "pasted document text", "filename": "my-sdd"}
# Example response: DocumentMapResponse — full map + document_id + chunk_count
@router.post("", response_model=DocumentMapResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(request: Request, db: Session = Depends(get_db)):
    """Upload a document (file or pasted text), build a grounded concept map, return it."""
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        body = await request.json()
        text = (body.get("text") or "").strip()
        if not text:
            raise HTTPException(status_code=422, detail="JSON body must include a non-empty 'text' field.")
        filename = (body.get("filename") or "pasted-text").strip()
        return create_document_map(text, filename, "pasted", db)

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None or isinstance(upload, str):
            raise HTTPException(status_code=422, detail="Multipart body must include a 'file' field.")
        extension = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        source_type = _EXTENSION_TO_SOURCE.get(extension)
        if source_type is None:
            raise HTTPException(status_code=400, detail=f"Unsupported file type '.{extension}'. Use .docx, .pdf, .txt, or .md.")
        data = await upload.read()
        if source_type == "pasted":  # plain-text files skip binary parsing
            data = data.decode("utf-8", errors="replace")
        return create_document_map(data, upload.filename, source_type, db)

    raise HTTPException(status_code=415, detail="Send multipart/form-data with a file, or application/json with text.")
