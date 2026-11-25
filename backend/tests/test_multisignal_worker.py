from unittest.mock import patch

from sqlalchemy import select

from app.models import MatchingJob, MatchingJobStatusEnum, MatchSuggestion, Report
from app.services.matching_worker import MatchingWorker


def _submit(client, description, category="pothole", lat=27.7, lng=85.3, sha="a" * 64, phash="f" * 16):
    with patch("app.api.reports.save_image") as mock_save:
        mock_save.return_value = ("uploads/test.jpg", sha, phash, 8)
        resp = client.post(
            "/api/reports",
            data={"description": description, "category": category, "latitude": str(lat), "longitude": str(lng)},
            files={"image": ("test.jpg", b"fake", "image/jpeg")},
        )
    assert resp.status_code == 201
    return resp.json()


def test_worker_persists_multisignal_fields(client, db_session, mock_embedding_service, session_factory):
    r1 = _submit(client, "Large pothole on main road", sha="1" * 64, phash="f" * 16)
    worker = MatchingWorker()
    with patch("app.services.matching_worker.SessionLocal", session_factory):
        worker._process_next_job()  # process r1

    r2 = _submit(client, "Big pothole on main road nearby", lat=27.7001, lng=85.3001, sha="2" * 64, phash="f" * 16)
    with patch("app.services.matching_worker.SessionLocal", session_factory):
        worker._process_next_job()  # process r2

    job = db_session.scalar(select(MatchingJob).where(MatchingJob.report_id == r2["id"]))
    assert job.status == MatchingJobStatusEnum.COMPLETED
    suggestions = list(db_session.scalars(select(MatchSuggestion).where(MatchSuggestion.report_id == r2["id"])).all())
    assert len(suggestions) >= 1
    s = suggestions[0]
    assert s.candidate_classification in ("AUTO_MERGE_CANDIDATE", "REVIEW_CANDIDATE")
    assert s.category_match is True
    assert s.geo_distance_meters is not None
    assert s.geo_distance_meters < 500
    assert s.text_similarity is not None
    assert s.phash_similarity is not None


def test_worker_missing_candidate_embedding_still_uses_other_signals(client, db_session, mock_embedding_service, session_factory):
    # r1: no embedding, but same sha256 and close
    r1 = _submit(client, "Streetlight broken on corner", category="streetlight", sha="a" * 64, phash="1" * 16)
    # Remove embedding if any
    rep1 = db_session.get(Report, r1["id"])
    rep1.embedding = None
    db_session.commit()

    r2 = _submit(client, "Streetlight broken on corner again", category="streetlight", lat=27.70005, lng=85.30005, sha="a" * 64, phash="1" * 16)
    worker = MatchingWorker()
    # Process r2 (and r1 may be pending before it; process enough times)
    with patch("app.services.matching_worker.SessionLocal", session_factory):
        for _ in range(3):
            worker._process_next_job()

    suggestions = list(db_session.scalars(select(MatchSuggestion).where(MatchSuggestion.report_id == r2["id"])).all())
    assert len(suggestions) >= 1
    assert suggestions[0].sha256_match is True


def test_worker_category_disagreement_prevents_auto_merge(client, db_session, mock_embedding_service, session_factory):
    r1 = _submit(client, "Large pothole on main road", category="pothole", sha="1" * 64, phash="f" * 16)
    worker = MatchingWorker()
    with patch("app.services.matching_worker.SessionLocal", session_factory):
        worker._process_next_job()

    r2 = _submit(client, "Garbage pile on main road", category="garbage", lat=27.7001, lng=85.3001, sha="1" * 64, phash="f" * 16)
    with patch("app.services.matching_worker.SessionLocal", session_factory):
        worker._process_next_job()

    suggestions = list(db_session.scalars(select(MatchSuggestion).where(MatchSuggestion.report_id == r2["id"])).all())
    # Category disagreement prevents auto-merge; may be review or no match depending on evidence.
    for s in suggestions:
        assert s.candidate_classification != "AUTO_MERGE_CANDIDATE"


def test_worker_exact_sha256_far_location_different_category_creates_review_suggestion(client, db_session, mock_embedding_service, session_factory):
    r1 = _submit(client, "Large pothole on main road", category="pothole", lat=27.7, lng=85.3, sha="same" * 16, phash="f" * 16)
    worker = MatchingWorker()
    with patch("app.services.matching_worker.SessionLocal", session_factory):
        worker._process_next_job()

    r2 = _submit(client, "Graffiti on wall downtown", category="graffiti", lat=28.7, lng=86.3, sha="same" * 16, phash="f" * 16)
    with patch("app.services.matching_worker.SessionLocal", session_factory):
        worker._process_next_job()

    suggestions = list(db_session.scalars(select(MatchSuggestion).where(MatchSuggestion.report_id == r2["id"])).all())
    assert len(suggestions) >= 1
    s = suggestions[0]
    assert s.sha256_match is True
    assert s.category_match is False
    assert s.candidate_classification == "REVIEW_CANDIDATE"
    assert s.status.value == "pending"
    assert s.geo_distance_meters is not None and s.geo_distance_meters > 500


def test_worker_exact_sha256_does_not_auto_merge_when_enabled_if_far_apart(client, db_session, mock_embedding_service, session_factory):
    from app.config import settings
    old = settings.auto_merge_enabled
    settings.auto_merge_enabled = True
    try:
        r1 = _submit(client, "Large pothole on main road", category="pothole", lat=27.7, lng=85.3, sha="far1" * 16, phash="f" * 16)
        worker = MatchingWorker()
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            worker._process_next_job()

        r2 = _submit(client, "Pothole reported elsewhere", category="pothole", lat=28.7, lng=86.3, sha="far1" * 16, phash="f" * 16)
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            for _ in range(3):
                worker._process_next_job()

        report2 = db_session.get(Report, r2["id"])
        assert report2.incident_id == r2["incident_id"]
        suggestions = list(db_session.scalars(select(MatchSuggestion).where(MatchSuggestion.report_id == r2["id"])).all())
        assert any(s.sha256_match is True and s.status.value == "pending" for s in suggestions)
        from app.models import MergeEvent
        assert db_session.scalar(select(MergeEvent).where(MergeEvent.report_id == r2["id"])) is None
    finally:
        settings.auto_merge_enabled = old
