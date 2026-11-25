"""Tests for merge reversal (Phase D2)."""
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.config import settings
from app.models import (
    AdminAuditLog,
    Incident,
    MergeEvent,
    Report,
    StatusEnum,
)
from app.services.incident_merge import MergeReversalConflictError, reverse_merge
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


def _run_worker(session_factory, times=3):
    worker = MatchingWorker()
    with patch("app.services.matching_worker.SessionLocal", session_factory):
        for _ in range(times):
            worker._process_next_job()


def _login(client):
    resp = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert resp.status_code == 200
    csrf = client.cookies.get("streetproof_csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


def test_reverse_merge_restores_state(client, db_session, mock_embedding_service, session_factory):
    old = settings.auto_merge_enabled
    settings.auto_merge_enabled = True
    try:
        r1 = _submit(client, "Large pothole on main road", sha="1" * 64, phash="f" * 16)
        _run_worker(session_factory, times=1)
        r2 = _submit(client, "Large pothole on main road again", lat=27.7001, lng=85.3001, sha="1" * 64, phash="f" * 16)
        _run_worker(session_factory, times=4)

        merge_event = db_session.scalar(select(MergeEvent).where(MergeEvent.report_id == r2["id"], MergeEvent.action == "AUTOMATIC_INCIDENT_MERGE"))
        assert merge_event is not None

        reversal = reverse_merge(db_session, merge_event=merge_event, actor_username="admin")
        db_session.commit()

        report2 = db_session.get(Report, r2["id"])
        source_incident = db_session.get(Incident, r2["incident_id"])
        assert report2.incident_id == r2["incident_id"]
        assert source_incident.status == StatusEnum.OPEN
        assert source_incident.merged_into_incident_id is None
        assert reversal.action == "MERGE_REVERSAL"
        assert merge_event.reversed_at is not None
    finally:
        settings.auto_merge_enabled = old


def test_reverse_merge_refuses_if_target_changed(client, db_session, mock_embedding_service, session_factory):
    old = settings.auto_merge_enabled
    settings.auto_merge_enabled = True
    try:
        r1 = _submit(client, "Large pothole on main road", sha="1" * 64, phash="f" * 16)
        _run_worker(session_factory, times=1)
        r2 = _submit(client, "Large pothole on main road again", lat=27.7001, lng=85.3001, sha="1" * 64, phash="f" * 16)
        _run_worker(session_factory, times=4)

        merge_event = db_session.scalar(select(MergeEvent).where(MergeEvent.report_id == r2["id"], MergeEvent.action == "AUTOMATIC_INCIDENT_MERGE"))
        assert merge_event is not None

        # Add a new report to target incident after merge -> should block reversal
        extra = Report(
            description="Extra report added after merge to target incident",
            category=db_session.get(Report, r1["id"]).category,
            latitude=27.7002,
            longitude=85.3002,
            image_path="uploads/extra.jpg",
            phash="0" * 16,
            incident_id=r1["incident_id"],
        )
        db_session.add(extra)
        db_session.commit()

        with pytest.raises(MergeReversalConflictError):
            reverse_merge(db_session, merge_event=merge_event, actor_username="admin")
        db_session.rollback()
    finally:
        settings.auto_merge_enabled = old


def test_reverse_merge_api_returns_409_on_conflict(client, db_session, mock_embedding_service, session_factory):
    old = settings.auto_merge_enabled
    settings.auto_merge_enabled = True
    try:
        r1 = _submit(client, "Large pothole on main road", sha="1" * 64, phash="f" * 16)
        _run_worker(session_factory, times=1)
        r2 = _submit(client, "Large pothole on main road again", lat=27.7001, lng=85.3001, sha="1" * 64, phash="f" * 16)
        _run_worker(session_factory, times=4)

        merge_event = db_session.scalar(select(MergeEvent).where(MergeEvent.report_id == r2["id"], MergeEvent.action == "AUTOMATIC_INCIDENT_MERGE"))
        assert merge_event is not None

        # Make it unsafe
        extra = Report(
            description="Extra report added after merge to target incident",
            category=db_session.get(Report, r1["id"]).category,
            latitude=27.7002,
            longitude=85.3002,
            image_path="uploads/extra.jpg",
            phash="0" * 16,
            incident_id=r1["incident_id"],
        )
        db_session.add(extra)
        db_session.commit()

        headers = _login(client)
        res = client.post(f"/api/admin/merges/{merge_event.id}/reverse", headers=headers)
        assert res.status_code == 409
    finally:
        settings.auto_merge_enabled = old
