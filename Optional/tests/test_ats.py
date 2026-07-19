from app.ats.analyzer import important_keywords, normalize_keyword
from app.ats.scorer import JD_WEIGHTS, GENERAL_WEIGHTS, score_resume
import io
import json

import fitz
from werkzeug.datastructures import MultiDict

from app.models import ResumeScan
from app.services.file_storage import StorageError
from app.services.file_storage import _storage_request
from tests.conftest import create_user, login_session, make_pdf


RESUME_TEXT = """
Jane Doe jane@example.com +1 555 123 4567 linkedin.com/in/jane
Summary Python backend developer.
Skills Python SQL Flask PostgreSQL Docker AWS testing
Experience Built APIs and improved latency by 30% for 100 users.
Education BS Computer Science
Projects Resume scanner
Certifications AWS Cloud Practitioner
"""


def upload(client, fileobj, name="resume.pdf", mimetype="application/pdf"):
    return client.post(
        "/ats/scan",
        data={
            "resume": (fileobj, name, mimetype),
            "job_title": "Backend Developer",
            "job_description": "Python Flask PostgreSQL Docker AWS APIs testing",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_valid_pdf_accepted(auth_client, app, monkeypatch):
    monkeypatch.setattr("app.ats.routes.upload_resume", lambda *args: None)
    response = upload(auth_client, make_pdf(RESUME_TEXT))
    assert b"ATS result" in response.data
    with app.app_context():
        scan = ResumeScan.query.one()
        assert scan.file_sha256
        assert scan.storage_path.startswith(f"{scan.user_id}/resumes/")
        assert scan.status == "completed"


def test_legacy_stored_filename_migration_is_present():
    migration = (__import__("pathlib").Path(__file__).parents[2] / "Backend" / "migrations" / "versions" / "0011_drop_legacy_resume_filename.py").read_text()
    assert 'drop_column("stored_filename")' in migration


def test_missing_max_pages_uses_safe_default(auth_client, app, monkeypatch):
    app.config.pop("MAX_PDF_PAGES", None)
    monkeypatch.setattr("app.ats.routes.upload_resume", lambda *args: None)
    assert b"ATS result" in upload(auth_client, make_pdf(RESUME_TEXT)).data


def test_storage_failure_rolls_back_to_failed_status(auth_client, app, monkeypatch):
    monkeypatch.setattr("app.ats.routes.upload_resume", lambda *args: (_ for _ in ()).throw(StorageError("private detail")))
    response = upload(auth_client, make_pdf(RESUME_TEXT))
    assert b"could not be stored safely" in response.data
    assert b"private detail" not in response.data
    with app.app_context():
        scan = ResumeScan.query.one()
        assert scan.status == "failed"
        assert scan.overall_score is None


def test_storage_uses_server_secret_without_user_token(app, monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps({"ok": True}).encode()

    def open_request(request, timeout):
        captured["headers"] = dict(request.header_items())
        return Response()

    app.config["SUPABASE_SECRET_KEY"] = "server-secret"
    monkeypatch.setattr("app.services.file_storage.urlopen", open_request)
    with app.app_context():
        assert _storage_request("bucket", "") == {"ok": True}
    assert captured["headers"]["Apikey"] == "server-secret"
    assert "Authorization" not in captured["headers"]


def test_fake_pdf_rejected(auth_client, app):
    response = upload(auth_client, __import__("io").BytesIO(b"not pdf"))
    assert b"not a valid PDF" in response.data
    with app.app_context():
        assert ResumeScan.query.count() == 0


def test_extension_and_mime_rejected(auth_client):
    response = upload(auth_client, make_pdf(RESUME_TEXT), "resume.txt", "application/pdf")
    assert b"Only PDF" in response.data
    response = upload(auth_client, make_pdf(RESUME_TEXT), "resume.pdf", "text/plain")
    assert b"must be a PDF" in response.data


def test_multiple_and_oversized_uploads_rejected(auth_client, app):
    response = auth_client.post(
        "/ats/scan",
        data=MultiDict([
            ("resume", (make_pdf(RESUME_TEXT), "one.pdf", "application/pdf")),
            ("resume", (make_pdf(RESUME_TEXT), "two.pdf", "application/pdf")),
        ]),
        content_type="multipart/form-data",
    )
    assert b"exactly one PDF" in response.data
    app.config["MAX_CONTENT_LENGTH"] = 100
    response = upload(auth_client, io.BytesIO(b"%PDF-" + b"x" * 200))
    assert response.status_code == 413 or b"exceeds" in response.data


def test_encrypted_too_many_pages_and_image_only_are_rejected(auth_client, app):
    document = fitz.open()
    document.new_page().insert_text((72, 72), RESUME_TEXT)
    encrypted = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
    document.close()
    assert b"Encrypted PDFs" in upload(auth_client, io.BytesIO(encrypted)).data

    app.config["MAX_PDF_PAGES"] = 1
    document = fitz.open()
    document.new_page().insert_text((72, 72), RESUME_TEXT)
    document.new_page().insert_text((72, 72), RESUME_TEXT)
    too_long = document.tobytes()
    document.close()
    assert b"more than 1 pages" in upload(auth_client, io.BytesIO(too_long)).data

    assert b"image-only or unreadable" in upload(auth_client, make_pdf()).data
    with app.app_context():
        assert {scan.status for scan in ResumeScan.query.all()} == {"failed"}


def test_scan_report_and_delete(auth_client, app, monkeypatch):
    deleted = []
    monkeypatch.setattr("app.ats.routes.upload_resume", lambda *args: None)
    monkeypatch.setattr("app.ats.routes.delete_resume", lambda path, token: deleted.append(path))
    upload(auth_client, make_pdf(RESUME_TEXT))
    report = auth_client.get("/ats/report/1")
    assert report.status_code == 200
    assert report.mimetype == "application/pdf"
    response = auth_client.post("/ats/delete/1", follow_redirects=True)
    assert b"deleted" in response.data
    with app.app_context():
        assert ResumeScan.query.count() == 0
    assert deleted and "/resumes/" in deleted[0]


def test_one_user_cannot_access_another_users_scan(auth_client, client, app, monkeypatch):
    monkeypatch.setattr("app.ats.routes.upload_resume", lambda *args: None)
    upload(auth_client, make_pdf(RESUME_TEXT))
    other_id = "4f386548-3b21-4ee1-9be0-7c43d078841e"
    create_user(app, user_id=other_id, email="other@example.com")
    login_session(client, other_id)
    assert client.get("/ats/result/1").status_code == 404
    assert client.get("/ats/report/1").status_code == 404


def test_scoring_bounds_aliases_and_weights():
    assert normalize_keyword("js") == "javascript"
    assert "python" in important_keywords("Python python python")
    assert sum(JD_WEIGHTS.values()) == 100
    assert sum(GENERAL_WEIGHTS.values()) == 100
    result = score_resume(RESUME_TEXT, 1, "Python Flask Docker")
    assert 0 <= result["overall_score"] <= 100
    assert "python" in result["matched_keywords"]
