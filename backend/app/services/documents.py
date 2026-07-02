"""Extract plain text from uploaded clinical-note documents (PDF or TXT)."""

import io

from pypdf import PdfReader

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_TEXT_CHARS = 50_000


class DocumentError(ValueError):
    """User-correctable problem with an uploaded document."""


def extract_text(filename: str, data: bytes) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentError(
            f"Unsupported file type '{ext or filename}'. Upload a .pdf or .txt file."
        )
    if len(data) == 0:
        raise DocumentError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentError(
            f"File is too large ({len(data) / 1_048_576:.1f} MB). Maximum is 10 MB."
        )

    text = _pdf_text(data) if ext == ".pdf" else _txt_text(data)

    if not text.strip():
        raise DocumentError(
            "No extractable text found. If this is a scanned PDF (images of pages), "
            "it has no text layer — OCR is not supported yet."
        )
    if len(text) > MAX_TEXT_CHARS:
        raise DocumentError(
            f"Document text is too long ({len(text):,} characters). "
            f"Maximum is {MAX_TEXT_CHARS:,}."
        )
    return text.strip()


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise DocumentError(f"Could not read the PDF: {exc}") from exc
    return "\n\n".join(pages)


def _txt_text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")
