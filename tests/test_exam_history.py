from fastapi.testclient import TestClient

import config
from main import app


def test_delete_exam_removes_markdown_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EXAMS_DIR", tmp_path)
    exam_file = tmp_path / "paper.md"
    exam_file.write_text("# test", encoding="utf-8")

    client = TestClient(app)
    response = client.delete("/api/exam/paper.md")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert not exam_file.exists()


def test_delete_exam_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EXAMS_DIR", tmp_path)

    client = TestClient(app)
    response = client.delete("/api/exam/..%5Csecret.md")

    assert response.status_code == 400
