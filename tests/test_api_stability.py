import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.api import health as health_api
from backend.api import review as review_api
from backend.agents import project_orchestrator
from backend.agents import orchestrator
from backend.database.database import ReviewDatabase
from backend.main import app


@pytest.fixture

def api_client(tmp_path, monkeypatch):
    database = ReviewDatabase(str(tmp_path / "reviews.db"))
    monkeypatch.setattr(review_api, "db", database)
    monkeypatch.setattr(health_api, "db", database)
    monkeypatch.setattr(config.settings, "max_code_chars", 1000)
    monkeypatch.setattr(config.settings, "max_batch_files", 4)
    monkeypatch.setattr(config.settings, "max_batch_file_chars", 1000)
    monkeypatch.setattr(config.settings, "max_batch_total_chars", 3000)
    monkeypatch.setattr(config.settings, "max_project_files", 20)
    monkeypatch.setattr(config.settings, "max_project_file_bytes", 1000)
    monkeypatch.setattr(config.settings, "max_project_total_bytes", 5000)
    with TestClient(app) as client:
        yield client


def test_health_returns_standard_envelope_and_checks_database(api_client):
    response = api_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["error"] is None
    assert response.json()["data"]["status"] == "healthy"
    assert response.json()["data"]["service"] == "CodeReviewAgent"


def test_empty_code_returns_standard_validation_error(api_client):
    response = api_client.post("/api/review", json={"code": "  "})

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["data"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"code": "print('ok')", "language": "Brainfuck"},
        {"code": "print('ok')", "filename": "../secret.py"},
        {"code": "print('ok')", "filename": "folder\\secret.py"},
        {"code": "print('ok')", "unexpected": True},
    ],
)
def test_invalid_language_filename_or_fields_are_rejected(api_client, payload):
    response = api_client.post("/api/review", json=payload)

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_oversized_single_review_is_rejected(api_client, monkeypatch):
    monkeypatch.setattr(config.settings, "max_code_chars", 4)

    response = api_client.post("/api/review", json={"code": "print('too long')"})

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_all_single_source_endpoints_enforce_source_limit(api_client, monkeypatch):
    monkeypatch.setattr(config.settings, "max_code_chars", 4)
    payload = {"filename": "sample.py", "language": "Python", "code": "12345"}

    for endpoint in ("/api/review", "/api/detect-language", "/api/generate-tests", "/api/fix"):
        response = api_client.post(endpoint, json=payload)
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_existing_read_and_helper_endpoints_use_success_envelope(api_client):
    root = api_client.get("/")
    files = api_client.get("/api/files")
    detected = api_client.post("/api/detect-language", json={"filename": "sample.py", "code": "x = 1"})
    tests = api_client.post("/api/generate-tests", json={"filename": "sample.py", "code": "x = 1"})
    fix = api_client.post("/api/fix", json={"filename": "sample.py", "code": "x = 1"})
    languages = api_client.get("/api/languages")
    public_config = api_client.get("/api/config")

    for response in (root, files, detected, tests, fix, languages, public_config):
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["error"] is None
        assert "data" in response.json()
    assert len(languages.json()["data"]["languages"]) == 18
    assert public_config.json()["data"]["limits"]["max_project_files"] == 20
    assert public_config.json()["data"]["limits"]["max_project_related_file_chars"] == 12000


def test_review_is_persisted_and_retrieved_with_consistent_payload(api_client):
    response = api_client.post(
        "/api/review",
        json={"filename": "sample.py", "language": "Python", "code": "def add(a, b):\n    return a + b"},
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["summary"]["files_reviewed"] == ["sample.py"]
    assert result["review_id"]
    assert result["created_at"]

    retrieved = api_client.get(f"/api/review/{result['review_id']}")

    assert retrieved.status_code == 200
    assert retrieved.json()["data"]["review_id"] == result["review_id"]
    assert retrieved.json()["data"]["summary"] == result["summary"]
    assert retrieved.json()["data"]["language"] == result["language"]
    assert retrieved.json()["data"]["created_at"] == result["created_at"]

    history = api_client.get("/api/reviews")
    assert history.status_code == 200
    listing = history.json()["data"]["reviews"]
    assert listing[0]["review_id"] == result["review_id"]
    assert listing[0]["project_name"] == "sample.py"
    assert "source_code" not in listing[0]


def test_review_list_supports_pagination_and_enforces_bounds(api_client):
    api_client.post("/api/review", json={"filename": "one.py", "code": "x = 1"})
    api_client.post("/api/review", json={"filename": "two.py", "code": "x = 2"})

    first_page = api_client.get("/api/reviews?limit=1&offset=0")
    second_page = api_client.get("/api/reviews?limit=1&offset=1")
    assert first_page.status_code == second_page.status_code == 200
    assert len(first_page.json()["data"]["reviews"]) == 1
    assert len(second_page.json()["data"]["reviews"]) == 1
    assert first_page.json()["data"]["reviews"][0]["review_id"] != second_page.json()["data"]["reviews"][0]["review_id"]
    assert api_client.get("/api/reviews?limit=0").status_code == 422


def test_review_list_counts_single_file_agent_findings(api_client):
    created = api_client.post("/api/review", json={
        "filename": "unsafe.py",
        "language": "Python",
        "code": "eval(user_input)",
    })
    review_id = created.json()["data"]["review_id"]

    response = api_client.get("/api/reviews")
    saved = next(item for item in response.json()["data"]["reviews"] if item["review_id"] == review_id)

    assert saved["finding_counts"]["security"] == 1
    assert saved["severity_counts"]["critical"] == 1


def test_saving_same_review_id_does_not_create_duplicate_rows(api_client):
    database = review_api.db
    payload = {"review_id": "stable-id", "summary": {"files_reviewed": ["sample.py"]}}

    database.save_review("stable-id", payload)
    database.save_review("stable-id", payload)

    with database._connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM reviews WHERE review_id = ?",
            ("stable-id",),
        ).fetchone()["count"]
    assert count == 1


def test_nonexistent_and_malformed_review_ids_return_safe_errors(api_client):
    missing = api_client.get(f"/api/review/{uuid.uuid4()}")
    malformed = api_client.get("/api/review/not-a-uuid")

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "VALIDATION_ERROR"


def test_batch_returns_valid_files_and_errors_for_invalid_files(api_client):
    response = api_client.post(
        "/api/review/batch",
        json={
            "files": [
                {"filename": "good.py", "language": "Python", "code": "def f():\n    return 1"},
                {"filename": "../bad.py", "language": "Python", "code": "def g():\n    return 2"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["partial"] is True
    assert data["summary"]["files_reviewed"] == ["good.py"]
    assert data["file_errors"][0]["index"] == 1
    assert data["reviews"][0]["summary"]["files_reviewed"] == ["good.py"]


def test_batch_rejects_excess_file_count_and_total_size(api_client, monkeypatch):
    files = [
        {"filename": f"{index}.py", "code": "x = 1"}
        for index in range(2)
    ]
    monkeypatch.setattr(config.settings, "max_batch_files", 1)

    too_many = api_client.post("/api/review/batch", json={"files": files})

    assert too_many.status_code == 413
    assert too_many.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

    monkeypatch.setattr(config.settings, "max_batch_files", 4)
    monkeypatch.setattr(config.settings, "max_batch_total_chars", 5)
    too_large = api_client.post("/api/review/batch", json={"files": files})

    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_batch_reports_per_file_size_error_without_blocking_valid_files(api_client, monkeypatch):
    monkeypatch.setattr(config.settings, "max_batch_file_chars", 4)
    response = api_client.post(
        "/api/review/batch",
        json={
            "files": [
                {"filename": "large.py", "code": "12345"},
                {"filename": "small.py", "code": "x=1"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["partial"] is True
    assert data["summary"]["files_reviewed"] == ["small.py"]
    assert data["file_errors"][0]["index"] == 0


def test_batch_keeps_successful_files_when_one_analysis_raises(api_client, monkeypatch):
    original_review = orchestrator.orchestrate_review

    async def fail_one_file(code, filename="", user_language=None):
        if filename == "bad.py":
            raise RuntimeError("internal details must not reach the caller")
        return await original_review(code, filename, user_language)

    monkeypatch.setattr(orchestrator, "orchestrate_review", fail_one_file)
    response = api_client.post(
        "/api/review/batch",
        json={
            "files": [
                {"filename": "good.py", "code": "x = 1"},
                {"filename": "bad.py", "code": "x = 2"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["files_reviewed"] == ["good.py"]
    assert data["file_errors"] == [{
        "index": 1,
        "filename": "bad.py",
        "message": "Analysis failed for this file.",
    }]
    assert "internal details" not in response.text


def test_batch_rejects_empty_and_all_invalid_files(api_client):
    empty = api_client.post("/api/review/batch", json={"files": []})
    invalid = api_client.post("/api/review/batch", json={"files": [{"code": "   "}]})

    assert empty.status_code == 400
    assert empty.json()["success"] is False
    assert invalid.status_code == 422
    assert invalid.json()["error"]["details"]["file_errors"]


def test_database_failure_returns_safe_api_error(api_client, monkeypatch):
    def fail_save(review_id, payload):
        raise sqlite3.OperationalError("sensitive database path")

    monkeypatch.setattr(review_api.db, "save_review", fail_save)
    response = api_client.post("/api/review", json={"code": "x = 1"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_ERROR"
    assert "sensitive database path" not in response.text


def test_malformed_json_returns_standard_error(api_client):
    response = api_client.post(
        "/api/review",
        content="{not valid json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_oversized_raw_request_body_is_rejected(api_client):
    from backend.config import settings

    raw_body = b" " * (settings.max_request_bytes + 1)
    response = api_client.post(
        "/api/review",
        content=raw_body,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_project_review_analyzes_files_and_persists_retrievable_result(api_client):
    response = api_client.post("/api/reviews/project", json={
        "project_name": "Phase C smoke",
        "files": [
            {"path": "src/main.py", "content": "from . import util\nvalue = 1"},
            {"path": "src/util.py", "content": "def load():\n    return 1"},
            {"path": "tests/test_main.py", "content": "def test_main():\n    assert True"},
            {"path": "requirements.txt", "content": "fastapi==0.115.0"},
            {"path": "README.md", "content": "Phase C project"},
        ],
        "entry_file": "src/main.py",
    })

    assert response.status_code == 200
    assert response.json()["success"] is True
    project = response.json()["data"]
    assert project["file_count"] == 5
    assert project["metadata"]["test_files"] == ["tests/test_main.py"]
    assert project["dependencies"][0]["name"] == "fastapi"
    assert project["languages"][0]["language"] == "Python"
    assert project["file_tree"]["type"] == "directory"
    assert project["analysis_capabilities"]["ai_analysis"] == "UNAVAILABLE"
    assert all(finding["file"] for finding in project["findings"])
    assert "content" not in str(project["files"])

    retrieved = api_client.get(f"/api/review/{project['review_id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["data"]["project"]["project_id"] == project["project"]["project_id"]
    assert retrieved.json()["data"]["file_count"] == 5
    assert "from . import util" not in retrieved.text


@pytest.mark.parametrize("path", ["../outside.py", "/absolute.py", "C:/outside.py"])
def test_project_api_rejects_invalid_paths(api_client, path):
    response = api_client.post("/api/reviews/project", json={
        "project_name": "Unsafe",
        "files": [{"path": path, "content": "print(1)"}],
    })

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_project_api_enforces_file_count_size_and_duplicate_path_limits(api_client, monkeypatch):
    base = {"project_name": "Limited", "files": [{"path": "a.py", "content": "x"}]}
    monkeypatch.setattr(config.settings, "max_project_files", 1)
    too_many = api_client.post("/api/reviews/project", json={
        **base,
        "files": base["files"] + [{"path": "b.py", "content": "y"}],
    })
    assert too_many.status_code == 422

    monkeypatch.setattr(config.settings, "max_project_files", 20)
    monkeypatch.setattr(config.settings, "max_project_file_bytes", 1)
    too_large = api_client.post("/api/reviews/project", json={
        "project_name": "Large file",
        "files": [{"path": "a.py", "content": "xx"}],
    })
    assert too_large.status_code == 422

    monkeypatch.setattr(config.settings, "max_project_file_bytes", 20)
    monkeypatch.setattr(config.settings, "max_project_total_bytes", 1)
    total = api_client.post("/api/reviews/project", json={
        "project_name": "Large project",
        "files": [{"path": "a.py", "content": "xx"}],
    })
    assert total.status_code == 422

    monkeypatch.setattr(config.settings, "max_project_total_bytes", 100)
    duplicate = api_client.post("/api/reviews/project", json={
        "project_name": "Duplicate",
        "files": [{"path": "a.py", "content": "x"}, {"path": "A.py", "content": "y"}],
    })
    assert duplicate.status_code == 422


def test_project_api_reports_multiple_languages_relationships_and_correct_finding_files(api_client):
    response = api_client.post("/api/reviews/project", json={
        "project_name": "Mixed project",
        "files": [
            {"path": "src/main.py", "content": "from . import db\nif value == None:\n    pass"},
            {"path": "src/db.py", "content": "def get():\n    return 1"},
            {"path": "web/main.ts", "content": "import { add } from './math';\nexport const value: number = add(1, 2);"},
            {"path": "web/math.ts", "content": "export function add(a: number, b: number) { return a + b; }"},
            {"path": "package.json", "content": '{"dependencies":{"react":"^18.0.0"}}'},
        ],
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert {item["language"] for item in data["languages"]} == {"Python", "TypeScript"}
    assert data["project"]["framework"] == "React"
    assert any(
        relation["source"] == "web/main.ts"
        and relation["target"] == "web/math.ts"
        and relation["resolution_status"] == "resolved_internal"
        for relation in data["relationships"]
    )
    assert any(finding["file"] == "src/main.py" and finding["agent"] == "Bug Agent" for finding in data["findings"])
    assert data["metadata"]["dependency_files"] == ["package.json"]


def test_project_api_returns_python_syntax_findings(api_client):
    response = api_client.post("/api/reviews/project", json={
        "project_name": "Syntax check",
        "files": [{"path": "broken.py", "content": "def broken(:\n    pass"}],
    })

    assert response.status_code == 200
    data = response.json()["data"]
    syntax = next(finding for finding in data["findings"] if finding["agent"] == "Syntax Analyzer")
    assert syntax["file"] == "broken.py"
    assert syntax["line_start"] == 1


def test_project_api_keeps_other_file_results_when_one_agent_fails(api_client, monkeypatch):
    original = project_orchestrator.analyze_bugs

    def fail_for_bad_file(code, filename="", language="generic", context=None):
        if filename == "bad.py":
            raise RuntimeError("private exception detail")
        return original(code, filename, language, context)

    monkeypatch.setattr(project_orchestrator, "analyze_bugs", fail_for_bad_file)
    response = api_client.post("/api/reviews/project", json={
        "project_name": "Partial analysis",
        "files": [
            {"path": "good.py", "content": "value = 1"},
            {"path": "bad.py", "content": "value = 2"},
        ],
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["partial"] is True
    assert {item["path"] for item in data["file_reviews"]} == {"good.py", "bad.py"}
    bad_status = next(item for item in data["file_reviews"] if item["path"] == "bad.py")["agent_statuses"]
    assert next(item for item in bad_status if item["agent"] == "Bug Agent")["status"] == "error"
    assert next(item for item in bad_status if item["agent"] == "Security Agent")["status"] == "ok"
    assert data["file_errors"] == [{"file": "bad.py", "agent": "Bug Agent", "message": "Agent analysis failed for this file."}]
    assert "private exception detail" not in response.text
