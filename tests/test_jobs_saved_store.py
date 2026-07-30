import sqlite3

from sqlalchemy import create_engine

from backend.modules.jobs import routes as jobs_routes


def test_sqlite_saved_job_round_trip_for_local_development(tmp_path, monkeypatch):
    db_path = tmp_path / "saved_jobs.db"
    monkeypatch.setattr(jobs_routes, "SAVED_JOBS_DB_PATH", str(db_path))
    monkeypatch.setattr(jobs_routes, "is_postgres_configured", lambda: False)
    request = jobs_routes.SaveJobRequest(
        job_id="job-local",
        client_id="client-a",
        title="Local Warehouse Associate",
        company="Example Logistics",
    )

    jobs_routes._save_job_to_sqlite(request, "2026-07-29T08:00:00")

    assert jobs_routes.list_saved_jobs_for_client("client-a") == [{
        "job_id": "job-local",
        "client_id": "client-a",
        "title": "Local Warehouse Associate",
        "company": "Example Logistics",
        "location": "",
        "salary": "",
        "url": "",
        "notes": "",
        "saved_date": "2026-07-29T08:00:00",
    }]


def test_list_saved_jobs_for_client_filters_exact_client(tmp_path, monkeypatch):
    db_path = tmp_path / "saved_jobs.db"
    monkeypatch.setattr(jobs_routes, "is_postgres_configured", lambda: False)
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
    monkeypatch.setattr(jobs_routes, "is_postgres_configured", lambda: False)
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


def test_postgres_saved_jobs_persist_and_filter_by_client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'postgres-simulation.db'}", future=True)
    monkeypatch.setattr(jobs_routes, "is_postgres_configured", lambda: True)
    monkeypatch.setattr(jobs_routes, "_postgres_engine", lambda: engine)

    first = jobs_routes.SaveJobRequest(
        job_id="job-a",
        client_id="client-a",
        title="Warehouse Associate",
        company="Example Logistics",
        notes="Initial note",
    )
    other_client = jobs_routes.SaveJobRequest(
        job_id="job-b",
        client_id="client-b",
        title="Office Assistant",
    )
    jobs_routes._save_job_to_postgres(first, "2026-07-29T09:00:00")
    jobs_routes._save_job_to_postgres(other_client, "2026-07-29T10:00:00")

    saved_jobs = jobs_routes.list_saved_jobs_for_client("client-a")

    assert [job["job_id"] for job in saved_jobs] == ["job-a"]
    assert saved_jobs[0]["client_id"] == "client-a"
    assert saved_jobs[0]["title"] == "Warehouse Associate"


def test_postgres_saved_job_upsert_updates_existing_record(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'postgres-upsert.db'}", future=True)
    monkeypatch.setattr(jobs_routes, "is_postgres_configured", lambda: True)
    monkeypatch.setattr(jobs_routes, "_postgres_engine", lambda: engine)
    original = jobs_routes.SaveJobRequest(
        job_id="job-a",
        client_id="client-a",
        title="Warehouse Associate",
        notes="Initial note",
    )
    updated = jobs_routes.SaveJobRequest(
        job_id="job-a",
        client_id="client-a",
        title="Senior Warehouse Associate",
        notes="Updated note",
    )

    jobs_routes._save_job_to_postgres(original, "2026-07-29T09:00:00")
    jobs_routes._save_job_to_postgres(updated, "2026-07-29T11:00:00")

    saved_jobs = jobs_routes.list_saved_jobs_for_client("client-a")

    assert len(saved_jobs) == 1
    assert saved_jobs[0]["title"] == "Senior Warehouse Associate"
    assert saved_jobs[0]["notes"] == "Updated note"
    assert saved_jobs[0]["saved_date"] == "2026-07-29T11:00:00"
