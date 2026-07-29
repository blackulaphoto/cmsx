import sqlite3

from backend.modules.jobs import routes as jobs_routes


def test_list_saved_jobs_for_client_filters_exact_client(tmp_path, monkeypatch):
    db_path = tmp_path / "saved_jobs.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                title TEXT,
                company TEXT,
                location TEXT,
                salary TEXT,
                url TEXT,
                notes TEXT,
                saved_date TEXT NOT NULL,
                UNIQUE(job_id, client_id)
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO saved_jobs
                (job_id, client_id, title, company, location, salary, url, notes, saved_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("job-a", "client-a", "Warehouse Associate", "Example Logistics", "Los Angeles", "", "", "", "2026-07-28"),
                ("job-b", "client-b", "Office Assistant", "Example Office", "Burbank", "", "", "", "2026-07-29"),
            ],
        )
    monkeypatch.setattr(jobs_routes, "SAVED_JOBS_DB_PATH", str(db_path))

    saved_jobs = jobs_routes.list_saved_jobs_for_client("client-a")

    assert [job["job_id"] for job in saved_jobs] == ["job-a"]
    assert saved_jobs[0]["client_id"] == "client-a"


def test_list_saved_jobs_for_client_supports_legacy_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_saved_jobs.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                notes TEXT,
                saved_date TEXT NOT NULL,
                UNIQUE(job_id, client_id)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO saved_jobs (job_id, client_id, notes, saved_date)
            VALUES (?, ?, ?, ?)
            """,
            ("legacy-job", "client-a", "Legacy record", "2026-07-28"),
        )
    monkeypatch.setattr(jobs_routes, "SAVED_JOBS_DB_PATH", str(db_path))

    saved_jobs = jobs_routes.list_saved_jobs_for_client("client-a")

    assert saved_jobs == [{
        "job_id": "legacy-job",
        "client_id": "client-a",
        "title": None,
        "company": None,
        "location": None,
        "salary": None,
        "url": None,
        "notes": "Legacy record",
        "saved_date": "2026-07-28",
    }]
