"""API tests that don't require a database connection."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_models_lists_all_frameworks():
    res = client.get("/models")
    assert res.status_code == 200
    body = res.json()
    assert {m["framework"] for m in body} == {"pytorch", "tensorflow", "jax"}
    for m in body:
        assert m["model_name"]
        # each framework is "available" when its ml/ pipeline deps are installed
        assert m["status"] in {"placeholder", "available"}


def test_analyze_note_rejects_unknown_framework():
    res = client.post("/analyze-note", json={"note": "x", "framework": "keras"})
    assert res.status_code == 422


def test_analyze_note_rejects_empty_note():
    res = client.post("/analyze-note", json={"note": "", "framework": "pytorch"})
    assert res.status_code == 422


def test_analyze_file_rejects_unsupported_extension():
    res = client.post(
        "/analyze-file",
        files={"file": ("note.docx", b"hello", "application/octet-stream")},
    )
    assert res.status_code == 422
    assert "Unsupported file type" in res.json()["detail"]


def test_analyze_file_rejects_empty_file():
    res = client.post("/analyze-file", files={"file": ("note.pdf", b"", "application/pdf")})
    assert res.status_code == 422
    assert "empty" in res.json()["detail"]


def test_analyze_file_rejects_pdf_without_text_layer():
    # Valid-looking PDF header but unparseable/no text content
    res = client.post(
        "/analyze-file",
        files={"file": ("scan.pdf", b"%PDF-1.4 garbage", "application/pdf")},
    )
    assert res.status_code == 422
