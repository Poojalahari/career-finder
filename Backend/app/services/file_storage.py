import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import current_app
from werkzeug.utils import secure_filename


PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


class UploadValidationError(ValueError):
    pass


class StorageError(RuntimeError):
    pass


def validate_pdf_upload(file_storage):
    if file_storage is None or not file_storage.filename:
        raise UploadValidationError("Choose one PDF resume.")
    safe_original = secure_filename(file_storage.filename)
    if not safe_original.lower().endswith(".pdf"):
        raise UploadValidationError("Only PDF files are accepted.")
    if file_storage.mimetype not in PDF_MIME_TYPES:
        raise UploadValidationError("The uploaded file must be a PDF document.")
    data = file_storage.read()
    file_storage.seek(0)
    if not data:
        raise UploadValidationError("The uploaded PDF is empty.")
    if not data.startswith(b"%PDF-"):
        raise UploadValidationError("The file is not a valid PDF.")
    if len(data) > current_app.config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024):
        raise UploadValidationError("The PDF exceeds the configured size limit.")
    return safe_original, data, hashlib.sha256(data).hexdigest()


def _storage_request(path: str, access_token: str, *, data: bytes | None = None, method: str = "POST", content_type: str = "application/json"):
    base_url = current_app.config.get("SUPABASE_URL", "")
    publishable_key = current_app.config.get("SUPABASE_PUBLISHABLE_KEY", "")
    secret_key = current_app.config.get("SUPABASE_SECRET_KEY", "")
    api_key = secret_key or publishable_key
    if not base_url or not api_key or (not secret_key and not access_token):
        raise StorageError("Resume storage is not configured.")
    headers = {"apikey": api_key, "Content-Type": content_type}
    if not secret_key:
        headers["Authorization"] = f"Bearer {access_token}"
    request = Request(
        f"{base_url}/storage/v1/{path.lstrip('/')}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        current_app.logger.warning("Supabase Storage request failed with status %s", exc.code)
        raise StorageError("The resume storage service rejected the request.") from exc
    except (URLError, TimeoutError) as exc:
        raise StorageError("The resume storage service is temporarily unavailable.") from exc


def upload_resume(storage_path: str, data: bytes, access_token: str) -> None:
    bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "career-documents")
    object_path = quote(storage_path, safe="/")
    _storage_request(f"object/{bucket}/{object_path}", access_token, data=data, content_type="application/pdf")


def delete_resume(storage_path: str, access_token: str) -> None:
    bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "career-documents")
    payload = json.dumps({"prefixes": [storage_path]}).encode("utf-8")
    _storage_request(f"object/{bucket}", access_token, data=payload, method="DELETE")


def signed_resume_url(storage_path: str, access_token: str, expires_in: int = 300) -> str:
    bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "career-documents")
    object_path = quote(storage_path, safe="/")
    payload = json.dumps({"expiresIn": expires_in}).encode("utf-8")
    result = _storage_request(f"object/sign/{bucket}/{object_path}", access_token, data=payload)
    signed_path = result.get("signedURL") or result.get("signedUrl")
    if not signed_path:
        raise StorageError("A secure resume link could not be created.")
    if signed_path.startswith("http"):
        return signed_path
    return f"{current_app.config['SUPABASE_URL']}/storage/v1{signed_path}"
