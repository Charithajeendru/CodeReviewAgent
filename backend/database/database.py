import json
import sqlite3
from pathlib import Path

from backend.config import settings


class ReviewDatabase:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = Path(db_path or settings.sqlite_database_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    language TEXT,
                    files TEXT,
                    findings TEXT,
                    code_quality TEXT,
                    generated_tests TEXT,
                    fixes TEXT,
                    final_report TEXT,
                    payload TEXT
                )
                """
            )

            columns = [row["name"] for row in connection.execute("PRAGMA table_info(reviews)").fetchall()]
            if "code_quality" not in columns:
                connection.execute("ALTER TABLE reviews ADD COLUMN code_quality TEXT")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS fixes (
                    fix_id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_tests (
                    test_id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL,
                    fix_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    execution_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS verification_results (
                    verification_id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL,
                    fix_id TEXT NOT NULL,
                    test_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def save_review(self, review_id: str, payload: dict) -> None:
        language_payload = payload.get("language")
        final_report_payload = payload.get("summary") or payload.get("final_report") or {}
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        files_payload = payload.get("files")
        if not isinstance(files_payload, list):
            files_payload = summary.get("files_reviewed", [])

        def as_list(key: str) -> list:
            value = payload.get(key, [])
            return value if isinstance(value, list) else []

        findings = (
            as_list("bugs")
            + as_list("security")
            + as_list("performance")
            + as_list("code_quality")
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reviews (
                    review_id, created_at, language, files, findings,
                    code_quality, generated_tests, fixes, final_report, payload
                ) VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET
                    created_at = excluded.created_at,
                    language = excluded.language,
                    files = excluded.files,
                    findings = excluded.findings,
                    code_quality = excluded.code_quality,
                    generated_tests = excluded.generated_tests,
                    fixes = excluded.fixes,
                    final_report = excluded.final_report,
                    payload = excluded.payload
                """,
                (
                    review_id,
                    json.dumps(language_payload) if isinstance(language_payload, (dict, list)) else str(language_payload),
                    json.dumps(files_payload),
                    json.dumps(findings),
                    json.dumps(as_list("code_quality")),
                    json.dumps(as_list("tests")),
                    json.dumps(as_list("fixes")),
                    json.dumps(final_report_payload),
                    json.dumps(payload),
                ),
            )

    def get_review(self, review_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reviews WHERE review_id = ?",
                (review_id,),
            ).fetchone()
            if row is None:
                return None

            def decode(value: str | None, default):
                try:
                    return json.loads(value) if value else default
                except (TypeError, json.JSONDecodeError):
                    return default

            payload = decode(row["payload"], {})
            if not isinstance(payload, dict):
                payload = {}
            files = decode(row["files"], [])
            if not isinstance(files, list):
                files = []
            payload.setdefault("language", decode(row["language"], None))
            payload.setdefault("files", files)
            payload.setdefault("bugs", [])
            payload.setdefault("security", [])
            payload.setdefault("performance", [])
            payload.setdefault("code_quality", decode(row["code_quality"], []))
            payload.setdefault("tests", decode(row["generated_tests"], []))
            payload.setdefault("fixes", decode(row["fixes"], []))
            payload.setdefault("static_analysis", {})
            summary = payload.setdefault("summary", decode(row["final_report"], {}))
            if isinstance(summary, dict):
                summary.setdefault("files_reviewed", files)
                summary.setdefault("overall_risk_level", "LOW")
                summary.setdefault("lines_reviewed", 0)
            payload["review_id"] = row["review_id"]
            payload["created_at"] = row["created_at"]
            return payload

    def list_reviews(self, limit: int = 50, offset: int = 0) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT review_id, created_at, language, files, findings, final_report, payload "
                "FROM reviews ORDER BY created_at DESC, review_id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()

        results = []
        for row in rows:
            try:
                payload = json.loads(row["payload"] or "{}")
            except (TypeError, json.JSONDecodeError):
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
            language = payload.get("language")
            if isinstance(language, dict):
                language = language.get("language")
            if not language:
                language = payload.get("language") or summary.get("language") or "Unknown"
            project_findings = payload.get("findings")
            if isinstance(project_findings, list):
                findings = [item for item in project_findings if isinstance(item, dict)]
            else:
                findings = [
                    item
                    for key in ("bugs", "security", "performance", "code_quality")
                    for item in (payload.get(key) if isinstance(payload.get(key), list) else [])
                    if isinstance(item, dict)
                ]
            agent_by_category = {
                "bugs": "Bug Agent",
                "security": "Security Agent",
                "performance": "Performance Agent",
                "code_quality": "Code Quality Agent",
            }
            category_counts = {
                category: sum(item.get("agent") == agent for item in findings)
                for category, agent in agent_by_category.items()
            }
            finding_count = len(findings)
            severity_counts = {
                severity: sum(
                    isinstance(item, dict) and str(item.get("severity", "")).casefold() == severity
                    for item in findings
                )
                for severity in ("critical", "high", "medium", "low", "info")
            }
            file_names = summary.get("files_reviewed", [])
            if not isinstance(file_names, list):
                file_names = []
            results.append({
                "review_id": row["review_id"],
                "created_at": row["created_at"],
                "project_name": project.get("project_name") or (file_names[0] if file_names else "Code Review"),
                "language": language,
                "risk_level": summary.get("overall_risk_level", "LOW"),
                "file_count": (
                    payload.get("file_count")
                    or len(file_names)
                    or (len(payload.get("files", [])) if isinstance(payload.get("files", []), list) else 0)
                ),
                "finding_count": finding_count,
                "finding_counts": category_counts,
                "severity_counts": severity_counts,
                "tests_count": len(payload.get("tests", [])) if isinstance(payload.get("tests"), list) else 0,
                "status": "Completed",
            })
        return results

    def check_health(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def save_fix(self, payload: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO fixes (fix_id, finding_id, status, created_at, payload)
                VALUES (?, ?, ?, datetime('now'), ?)
                ON CONFLICT(fix_id) DO UPDATE SET
                    finding_id = excluded.finding_id,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    payload = excluded.payload
                """,
                (payload["fix_id"], payload["finding_id"], payload["status"], json.dumps(payload)),
            )

    def get_fix(self, fix_id: str) -> dict | None:
        return self._get_workflow_record("fixes", "fix_id", fix_id)

    def save_generated_test(self, payload: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO generated_tests (test_id, finding_id, fix_id, status, execution_status, created_at, payload)
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
                ON CONFLICT(test_id) DO UPDATE SET
                    finding_id = excluded.finding_id,
                    fix_id = excluded.fix_id,
                    status = excluded.status,
                    execution_status = excluded.execution_status,
                    created_at = excluded.created_at,
                    payload = excluded.payload
                """,
                (
                    payload["test_id"], payload["finding_id"], payload["fix_id"], payload["status"],
                    payload["execution_status"], json.dumps(payload),
                ),
            )

    def get_generated_test(self, test_id: str) -> dict | None:
        return self._get_workflow_record("generated_tests", "test_id", test_id)

    def save_verification(self, payload: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO verification_results (verification_id, finding_id, fix_id, test_id, status, created_at, payload)
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
                ON CONFLICT(verification_id) DO UPDATE SET
                    finding_id = excluded.finding_id,
                    fix_id = excluded.fix_id,
                    test_id = excluded.test_id,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    payload = excluded.payload
                """,
                (
                    payload["verification_id"], payload["finding_id"], payload["fix_id"], payload.get("test_id"),
                    payload["status"], json.dumps(payload),
                ),
            )

    def get_verification(self, verification_id: str) -> dict | None:
        return self._get_workflow_record("verification_results", "verification_id", verification_id)

    def _get_workflow_record(self, table: str, id_column: str, identifier: str) -> dict | None:
        allowed = {
            ("fixes", "fix_id"),
            ("generated_tests", "test_id"),
            ("verification_results", "verification_id"),
        }
        if (table, id_column) not in allowed:
            raise ValueError("Unsupported workflow record type.")
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT created_at, payload FROM {table} WHERE {id_column} = ?",
                (identifier,),
            ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(row["payload"])
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        payload["created_at"] = row["created_at"]
        return payload


db = ReviewDatabase()
