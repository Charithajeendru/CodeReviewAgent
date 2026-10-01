import pytest
from pydantic import ValidationError

from backend.config import settings
from backend.models.project import ProjectReviewRequest


def test_project_model_accepts_one_and_multiple_files():
    one = ProjectReviewRequest(project_name="One", files=[{"path": "main.py", "content": "print(1)"}])
    many = ProjectReviewRequest(project_name="Many", files=[
        {"path": "src/main.py", "content": "print(1)"},
        {"path": "tests/test_main.py", "content": ""},
    ])

    assert one.files[0].filename == "main.py"
    assert one.files[0].content_size == len("print(1)".encode())
    assert len(many.files) == 2


@pytest.mark.parametrize("path", ["../outside.py", "/absolute.py", "C:/outside.py", "src\\outside.py", "src//main.py", "./main.py"])
def test_project_model_rejects_unsafe_paths(path):
    with pytest.raises(ValidationError):
        ProjectReviewRequest(project_name="Unsafe", files=[{"path": path, "content": "x"}])


def test_project_model_rejects_duplicate_paths_case_insensitively():
    with pytest.raises(ValidationError, match="duplicate file paths"):
        ProjectReviewRequest(project_name="Duplicate", files=[
            {"path": "src/Main.py", "content": "a"},
            {"path": "src/main.py", "content": "b"},
        ])


def test_project_model_enforces_project_limits(monkeypatch):
    monkeypatch.setattr(settings, "max_project_files", 1)
    with pytest.raises(ValidationError, match="more files"):
        ProjectReviewRequest(project_name="Too many", files=[
            {"path": "a.py", "content": "a"},
            {"path": "b.py", "content": "b"},
        ])

    monkeypatch.setattr(settings, "max_project_files", 10)
    monkeypatch.setattr(settings, "max_project_file_bytes", 2)
    with pytest.raises(ValidationError, match="per-file"):
        ProjectReviewRequest(project_name="Large file", files=[{"path": "a.py", "content": "abc"}])

    monkeypatch.setattr(settings, "max_project_file_bytes", 10)
    monkeypatch.setattr(settings, "max_project_total_bytes", 2)
    with pytest.raises(ValidationError, match="total size"):
        ProjectReviewRequest(project_name="Large project", files=[
            {"path": "a.py", "content": "ab"},
            {"path": "b.py", "content": "c"},
        ])


def test_project_model_rejects_size_mismatch_and_unknown_language():
    with pytest.raises(ValidationError, match="does not match"):
        ProjectReviewRequest(project_name="Mismatch", files=[{"path": "a.py", "content": "é", "size": 1}])
    with pytest.raises(ValidationError, match="not supported"):
        ProjectReviewRequest(project_name="Unknown language", language="Fortran", files=[{"path": "a.py", "content": "x"}])