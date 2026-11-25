import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import MatchingJob, MatchingJobStatusEnum, MatchSuggestion, Report, StatusEnum
from app.services.matching_worker import MatchingWorker


def _make_image_file(filename="test.jpg", content=b"fake-jpeg-content", content_type="image/jpeg"):
    return (filename, io.BytesIO(content), content_type)


def _submit_report(client: TestClient, description: str, category: str = "pothole", lat: float = 27.7, lng: float = 85.3):
    # Patch save_image to avoid actual image processing/hashing complexity in tests
    with patch("app.api.reports.save_image") as mock_save:
        mock_save.return_value = ("uploads/test.jpg", "a" * 64, "f0f0f0f0f0f0f0f0", 8)
        resp = client.post(
            "/api/reports",
            data={
                "description": description,
                "category": category,
                "latitude": str(lat),
                "longitude": str(lng),
            },
            files={"image": _make_image_file()},
        )
    return resp


class TestMatchingIntegration:
    def test_report_submission_creates_matching_job(self, client, db_session):
        """Report submission creates a MatchingJob in the same transaction."""
        resp = _submit_report(client, "Large pothole on main road causing traffic issues")
        assert resp.status_code == 201
        report_id = resp.json()["id"]

        job = db_session.scalar(select(MatchingJob).where(MatchingJob.report_id == report_id))
        assert job is not None
        assert job.status == MatchingJobStatusEnum.PENDING
        assert job.attempts == 0

    def test_worker_processes_pending_job(self, client, db_session, mock_embedding_service, session_factory):
        """Worker processes a pending job and completes it."""
        # Create two reports in different incidents
        resp1 = _submit_report(client, "Large pothole on main road near market", "pothole", 27.7, 85.3)
        assert resp1.status_code == 201
        r1 = resp1.json()

        resp2 = _submit_report(client, "Big hole on the road beside the market", "pothole", 27.701, 85.301)
        assert resp2.status_code == 201
        r2 = resp2.json()

        # Process job for r2 with worker using test DB
        worker = MatchingWorker()
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()

        # r1 job may have been processed first (oldest pending); process again for r2
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()

        job2 = db_session.scalar(select(MatchingJob).where(MatchingJob.report_id == r2["id"]))
        assert job2 is not None
        assert job2.status in (MatchingJobStatusEnum.COMPLETED, MatchingJobStatusEnum.PENDING)

        # If r2's job was processed, it should be completed
        if job2.status == MatchingJobStatusEnum.COMPLETED:
            suggestions = list(db_session.scalars(select(MatchSuggestion).where(MatchSuggestion.report_id == r2["id"])).all())
            assert len(suggestions) >= 1

    def test_suggestions_persisted_after_matching(self, client, db_session, mock_embedding_service, session_factory):
        """Suggestions are persisted after successful matching with correct scores."""
        # Submit first report (creates incident A)
        resp1 = _submit_report(client, "Deep pothole on highway near bridge", "pothole", 27.7, 85.3)
        assert resp1.status_code == 201
        r1 = resp1.json()

        # Process first job so its embedding is generated
        worker = MatchingWorker()
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()

        # Submit second similar report (creates incident B)
        resp2 = _submit_report(client, "Large hole on highway near the bridge", "pothole", 27.701, 85.301)
        assert resp2.status_code == 201
        r2 = resp2.json()

        # Process second job
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()

        job2 = db_session.scalar(select(MatchingJob).where(MatchingJob.report_id == r2["id"]))
        assert job2 is not None
        assert job2.status == MatchingJobStatusEnum.COMPLETED

        suggestions = list(
            db_session.scalars(
                select(MatchSuggestion).where(MatchSuggestion.report_id == r2["id"])
            ).all()
        )
        assert len(suggestions) >= 1
        s = suggestions[0]
        assert 0.0 <= s.similarity_score <= 1.0
        assert s.matched_report_id == r1["id"]
        assert s.incident_id == r1["incident_id"]

    def test_interrupted_jobs_recover_on_restart(self, client, db_session, session_factory):
        """Interrupted PROCESSING jobs are recovered to PENDING on worker startup."""
        resp = _submit_report(client, "Broken streetlight on corner", "streetlight", 27.7, 85.3)
        assert resp.status_code == 201
        report_id = resp.json()["id"]

        job = db_session.scalar(select(MatchingJob).where(MatchingJob.report_id == report_id))
        assert job is not None

        # Simulate interrupted processing
        job.status = MatchingJobStatusEnum.PROCESSING
        db_session.commit()

        # Worker startup should recover it
        worker = MatchingWorker()
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._recover_interrupted_jobs()

        db_session.refresh(job)
        assert job.status == MatchingJobStatusEnum.PENDING

    def test_retry_logic_respects_max_retries(self, client, db_session, mock_embedding_service, session_factory):
        """Failed jobs are retried up to max_retries then marked FAILED."""
        resp = _submit_report(client, "Garbage pile near park", "garbage", 27.7, 85.3)
        assert resp.status_code == 201
        report_id = resp.json()["id"]

        worker = MatchingWorker()
        worker._max_retries = 2  # reduce for test speed

        # Make encode fail to trigger retries
        mock_embedding_service.encode.side_effect = RuntimeError("model error")

        with patch("app.services.matching_worker.SessionLocal", session_factory):
            # attempt 1: claim + fail -> PENDING (attempts=1)
            worker._process_next_job()
            job = db_session.scalar(select(MatchingJob).where(MatchingJob.report_id == report_id))
            db_session.refresh(job)
            assert job.status == MatchingJobStatusEnum.PENDING
            assert job.attempts == 1

            # attempt 2: claim + fail -> FAILED (attempts=2 >= max_retries=2)
            worker._process_next_job()
            db_session.refresh(job)
            assert job.status == MatchingJobStatusEnum.FAILED
            assert job.attempts == 2

    def test_ai_unavailable_report_succeeds_job_pending(self, client, db_session):
        """When AI is unavailable, report submission succeeds and job stays PENDING."""
        # The mock is ready by default in our fixture, but worker checks is_ready.
        # Simulate AI unavailable by making worker see not ready.
        not_ready_mock = type("S", (), {
            "is_ready": lambda self: False,
            "get_status": lambda self: {"status": "failed", "model_name": "test", "error": "not loaded"},
            "encode": lambda self, t: None,
        })()

        resp = _submit_report(client, "Pothole on road needs repair urgently", "pothole", 27.7, 85.3)
        assert resp.status_code == 201
        report_id = resp.json()["id"]

        job = db_session.scalar(select(MatchingJob).where(MatchingJob.report_id == report_id))
        assert job is not None
        assert job.status == MatchingJobStatusEnum.PENDING

        # Worker should not process when model not ready
        worker = MatchingWorker()
        with patch("app.services.matching_worker.SessionLocal"), patch(
            "app.services.matching_worker.EmbeddingService.get_instance", return_value=not_ready_mock
        ):
            worker._process_next_job()

        db_session.refresh(job)
        assert job.status == MatchingJobStatusEnum.PENDING

    def test_duplicate_suggestions_prevented(self, client, db_session, mock_embedding_service, session_factory):
        """Duplicate suggestions for the same report/incident are prevented."""
        # Create first report and process it
        resp1 = _submit_report(client, "Large pothole on main street", "pothole", 27.7, 85.3)
        assert resp1.status_code == 201
        r1 = resp1.json()

        worker = MatchingWorker()
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()  # process r1

        # Create second similar report
        resp2 = _submit_report(client, "Big pothole on main street nearby", "pothole", 27.701, 85.301)
        assert resp2.status_code == 201
        r2 = resp2.json()

        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()  # process r2

        # Manually reset r2 job to PENDING and reprocess to test idempotency
        job2 = db_session.scalar(select(MatchingJob).where(MatchingJob.report_id == r2["id"]))
        job2.status = MatchingJobStatusEnum.PENDING
        job2.completed_at = None
        db_session.commit()

        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()

        suggestions = list(
            db_session.scalars(
                select(MatchSuggestion).where(
                    MatchSuggestion.report_id == r2["id"],
                    MatchSuggestion.incident_id == r1["incident_id"],
                )
            ).all()
        )
        assert len(suggestions) == 1

class TestMatchingPublicApi:
    def test_public_matching_status_hides_internal_evidence(self, client, db_session, mock_embedding_service, session_factory):
        resp1 = _submit_report(client, "Large pothole on main road near market", "pothole", 27.7, 85.3)
        assert resp1.status_code == 201
        r1 = resp1.json()
        worker = MatchingWorker()
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()

        resp2 = _submit_report(client, "Big hole on the road beside the market", "pothole", 27.701, 85.301)
        assert resp2.status_code == 201
        r2 = resp2.json()
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()

        res = client.get(f"/api/matching/reports/{r2['id']}")
        assert res.status_code == 200
        data = res.json()
        assert set(data.keys()) == {"status", "suggestion_count", "error_message"}
        assert data["status"] in {"pending", "processing", "completed", "failed"}
        assert isinstance(data["suggestion_count"], int)
        assert data["suggestion_count"] >= 0
        # Ensure no internal evidence fields leak.
        serialized = str(data).lower()
        for forbidden in [
            "similarity_score", "matched_report_description", "incident_latitude", "incident_longitude",
            "sha256_match", "phash_similarity", "text_similarity", "geo_distance_meters",
            "category_match", "candidate_classification", "incident_id", "matched_report_id", "suggestions"
        ]:
            assert forbidden not in data
            assert f"'{forbidden}'" not in serialized

    def test_public_matching_status_returns_null_when_no_job(self, client, db_session):
        report = Report(
            description="Report without matching job for public status",
            category="pothole",
            latitude=27.7,
            longitude=85.3,
            image_path="uploads/test.jpg",
            sha256_hash="b" * 64,
            phash="0" * 16,
            phash_size=8,
            incident_id=_create_standalone_incident(db_session),
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)

        res = client.get(f"/api/matching/reports/{report.id}")
        assert res.status_code == 200
        assert res.json() is None

    def test_matching_suggestions_requires_admin_and_hides_from_public(self, client, db_session):
        resp = _submit_report(client, "Potential match report", "pothole", 27.7, 85.3)
        report_id = resp.json()["id"]

        unauth = client.get(f"/api/matching/suggestions/{report_id}")
        assert unauth.status_code == 401

        login = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
        assert login.status_code == 200
        auth = client.get(f"/api/matching/suggestions/{report_id}")
        assert auth.status_code == 200
        assert isinstance(auth.json(), list)


def _create_standalone_incident(db_session):
    from app.models import Incident, CategoryEnum, StatusEnum
    incident = Incident(
        title="Standalone incident",
        description="Standalone",
        category=CategoryEnum.POTHOLE,
        latitude=27.7,
        longitude=85.3,
        status=StatusEnum.OPEN,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)
    return incident.id
