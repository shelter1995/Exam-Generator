import pytest

from security import (
    MAX_FILENAME_LENGTH,
    ensure_safe_child_path,
    sanitize_upload_filename,
    validate_db_id,
)


def test_validate_db_id_accepts_simple_identifiers():
    assert validate_db_id("default") == "default"
    assert validate_db_id("training_2026-05") == "training_2026-05"


@pytest.mark.parametrize("db_id", ["", "../evil", "a/b", "a\\b", ".hidden", "x" * 65])
def test_validate_db_id_rejects_unsafe_identifiers(db_id):
    with pytest.raises(ValueError):
        validate_db_id(db_id)


def test_sanitize_upload_filename_removes_path_parts_and_unsafe_chars():
    filename = sanitize_upload_filename(r"..\课程<script>.pdf", {".pdf"})

    assert filename.endswith(".pdf")
    assert "/" not in filename
    assert "\\" not in filename
    assert ".." not in filename
    assert "<" not in filename
    assert len(filename) <= MAX_FILENAME_LENGTH


def test_sanitize_upload_filename_rejects_unsupported_extensions():
    with pytest.raises(ValueError):
        sanitize_upload_filename("payload.exe", {".pdf"})


def test_ensure_safe_child_path_rejects_path_traversal(tmp_path):
    base = tmp_path / "exams"
    base.mkdir()

    with pytest.raises(ValueError):
        ensure_safe_child_path(base, "../secret.md")

    safe = ensure_safe_child_path(base, "paper.md")
    assert safe == base / "paper.md"
