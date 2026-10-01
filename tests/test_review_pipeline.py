import asyncio
import sqlite3

from backend.agents.orchestrator import orchestrate_review, orchestrate_review_batch
from backend.database.database import ReviewDatabase


def test_orchestrate_review_includes_static_analysis_and_language() -> None:
    result = asyncio.run(
        orchestrate_review(
            "def add(a, b):\n    return a + b\n",
            "example.py",
            "Python",
        )
    )

    assert result.language is not None
    assert result.language.language == "Python"
    assert hasattr(result, "static_analysis")
    assert isinstance(result.static_analysis, dict)
    assert "status" in result.static_analysis
    assert hasattr(result, "code_quality")
    assert isinstance(result.code_quality, list)


def test_review_database_migrates_missing_code_quality_column(tmp_path) -> None:
    db_path = tmp_path / "legacy_reviews.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE reviews (
            review_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            language TEXT,
            files TEXT,
            findings TEXT,
            generated_tests TEXT,
            fixes TEXT,
            final_report TEXT,
            payload TEXT
        )
        """
    )
    connection.execute(
        "INSERT INTO reviews (review_id, created_at, language, files, findings, generated_tests, fixes, final_report, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "legacy-123",
            "2024-01-01",
            "Python",
            "[]",
            "[]",
            "[]",
            "[]",
            "{}",
            "{}",
        ),
    )
    connection.commit()
    connection.close()

    legacy_db = ReviewDatabase(str(db_path))
    legacy_db._init_db()

    with legacy_db._connect() as connection:
        columns = [row["name"] for row in connection.execute("PRAGMA table_info(reviews)").fetchall()]
        assert "code_quality" in columns


def test_orchestrate_review_batch_aggregates_multiple_files() -> None:
    result = asyncio.run(
        orchestrate_review_batch([
            {"filename": "a.py", "code": "def add(a, b):\n    return a + b\n", "language": "Python"},
            {"filename": "b.py", "code": "def greet(name):\n    return 'hi'\n", "language": "Python"},
        ])
    )

    assert result["summary"]["files_reviewed"] == ["a.py", "b.py"]
    assert result["summary"]["overall_risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert len(result["reviews"]) == 2
