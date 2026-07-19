import re
import unicodedata

import fitz

from app.services.file_storage import UploadValidationError


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = text.replace("\u2022", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(data: bytes, max_pages: int):
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UploadValidationError("The PDF is corrupt or cannot be opened.") from exc
    try:
        if doc.needs_pass:
            raise UploadValidationError("Encrypted PDFs are not supported.")
        page_count = doc.page_count
        if page_count <= 0:
            raise UploadValidationError("The PDF has no readable pages.")
        if page_count > max_pages:
            raise UploadValidationError(f"The PDF has more than {max_pages} pages.")
        text = "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()
    text = normalize_text(text)
    if len(re.findall(r"[A-Za-z]{3,}", text)) < 35:
        raise UploadValidationError("This looks like an image-only or unreadable PDF. OCR is not enabled.")
    return text, page_count
