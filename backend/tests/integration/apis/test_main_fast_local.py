"""
Tests unitarios locales para la FastAPI de Hybrid Shield.
Usan TestClient con mocks — no requieren conexión a GCP.

Colocar en: backend/tests/unit/test_main_local.py
Ejecutar con: pytest backend/tests/unit/test_main_local.py -v
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


# ================================================================
# SETUP: Parchear todas las dependencias GCP antes de importar main
# ================================================================
with patch("google.cloud.logging.Client"), \
     patch("google.auth.default", return_value=(MagicMock(), "test-project")), \
     patch("google.cloud.storage.Client"), \
     patch("google.auth.impersonated_credentials.Credentials", MagicMock()):
    from backend.main import app

client = TestClient(app)


# ================================================================
# 1. HEALTH CHECK
# ================================================================

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "timestamp" in data


# ================================================================
# 2. GET UPLOAD URL
# ================================================================

@patch("backend.main.storage_client")
def test_get_upload_url_success(mock_storage_client):
    mock_bucket = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/mock-signed-url"

    response = client.post("/api/get-upload-url", json={
        "filename": "producto.jpg",
        "content_type": "image/jpeg"
    })

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["upload_url"] == "https://storage.googleapis.com/mock-signed-url"
    mock_storage_client.bucket.assert_called_once()
    mock_blob.generate_signed_url.assert_called_once()


@patch("backend.main.storage_client")
def test_get_upload_url_gcs_failure(mock_storage_client):
    mock_storage_client.bucket.side_effect = Exception("GCS connection failed")

    response = client.post("/api/get-upload-url", json={
        "filename": "producto.jpg",
        "content_type": "image/jpeg"
    })

    assert response.status_code == 500
    assert "upload URL" in response.json()["detail"]


# ================================================================
# 3. UPLOAD DIRECT
# ================================================================

@patch("backend.main.storage_client")
def test_upload_direct_success(mock_storage_client):
    mock_bucket = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    import io
    file_content = b"fake image content"
    response = client.post(
        "/api/upload-direct",
        files={"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}
    )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    mock_blob.upload_from_string.assert_called_once()


# ================================================================
# 4. METADATA ENDPOINT
# ================================================================

@patch("backend.main.storage_client")
@patch("backend.main.update_job_status", new_callable=AsyncMock)
def test_metadata_endpoint_success(mock_update_status, mock_storage_client):
    mock_bucket = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    response = client.post("/api/metadata", json={
        "job_id": "test-job-id-12345",
        "filename": "producto.jpg",
        "content_type": "image/jpeg",
        "title": "Reloj de prueba",
        "description": "Un reloj muy bonito para testear.",
        "price": 120.5
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["job_id"] == "test-job-id-12345"
    assert "metadata_path" in data
    mock_blob.upload_from_string.assert_called_once()
    mock_update_status.assert_called_once_with("test-job-id-12345", "PENDING")


@patch("backend.main.storage_client")
@patch("backend.main.update_job_status", new_callable=AsyncMock)
def test_metadata_endpoint_gcs_failure(mock_update_status, mock_storage_client):
    mock_storage_client.bucket.side_effect = Exception("GCS unavailable")

    response = client.post("/api/metadata", json={
        "job_id": "test-job-id-error",
        "filename": "producto.jpg",
        "content_type": "image/jpeg",
        "title": "Reloj",
        "description": "Descripción",
        "price": 100.0
    })

    assert response.status_code == 500


# ================================================================
# 5. JOB STATUS POLLING
# ================================================================

@patch("backend.main.get_job_status", new_callable=AsyncMock)
def test_get_job_found(mock_get_status):
    mock_get_status.return_value = {
        "status": "COMPLETED",
        "final_action": "Approve",
        "risk_score": 0.15
    }

    response = client.get("/api/jobs/test-job-id-12345")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["final_action"] == "Approve"
    mock_get_status.assert_called_once_with("test-job-id-12345")


@patch("backend.main.get_job_status", new_callable=AsyncMock)
def test_get_job_not_found(mock_get_status):
    mock_get_status.return_value = None

    response = client.get("/api/jobs/job-inexistente")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


@patch("backend.main.get_job_status", new_callable=AsyncMock)
def test_get_job_failed_status(mock_get_status):
    mock_get_status.return_value = {
        "status": "FAILED",
        "metadata": {"error": "LLM timeout"}
    }

    response = client.get("/api/jobs/failed-job-id")

    assert response.status_code == 500
    assert "LLM timeout" in response.json()["detail"]


# ================================================================
# 6. AUDITOR DASHBOARD
# ================================================================

@patch("backend.main.get_auditor_jobs", new_callable=AsyncMock)
def test_get_auditor_jobs_success(mock_get_jobs):
    mock_get_jobs.return_value = [
        {"job_id": "job-1", "status": "PENDING_HUMAN_REVIEW", "final_action": "Human Review"},
        {"job_id": "job-2", "status": "COMPLETED", "final_action": "Block"},
    ]

    response = client.get("/api/jobs/auditor")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["job_id"] == "job-1"


@patch("backend.main.get_auditor_jobs", new_callable=AsyncMock)
def test_get_auditor_jobs_empty(mock_get_jobs):
    mock_get_jobs.return_value = []

    response = client.get("/api/jobs/auditor")

    assert response.status_code == 200
    assert response.json() == []


@patch("backend.main.get_auditor_jobs", new_callable=AsyncMock)
def test_get_auditor_jobs_error(mock_get_jobs):
    mock_get_jobs.side_effect = Exception("Firestore unavailable")

    response = client.get("/api/jobs/auditor")

    assert response.status_code == 500


# ================================================================
# 7. AUDIT TRACE
# ================================================================

@patch("backend.main.get_full_audit_trace", new_callable=AsyncMock)
def test_get_audit_trace_success(mock_get_trace):
    mock_get_trace.return_value = {
        "thread_id": "test-thread-123",
        "status": "success",
        "audit_log": [{"node": "pre_filter", "status": "completed"}],
        "final_action": "Human Review",
        "risk_score": 0.6,
    }

    response = client.get("/api/audit/trace/test-thread-123")

    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "test-thread-123"
    assert len(data["audit_log"]) == 1
    mock_get_trace.assert_called_once_with("test-thread-123")


@patch("backend.main.get_full_audit_trace", new_callable=AsyncMock)
def test_get_audit_trace_not_found(mock_get_trace):
    mock_get_trace.return_value = None

    response = client.get("/api/audit/trace/nonexistent-thread")

    assert response.status_code == 404
    assert response.json() == {"detail": "Trace not found"}


@patch("backend.main.get_full_audit_trace", new_callable=AsyncMock)
def test_get_audit_trace_db_error(mock_get_trace):
    mock_get_trace.side_effect = Exception("Database connection failed")

    response = client.get("/api/audit/trace/test-thread-123")

    assert response.status_code == 500
    assert "audit trace" in response.json()["detail"]


# ================================================================
# 8. HITL RESUME
# ================================================================

@patch("backend.main.resume_graph_execution", new_callable=AsyncMock)
def test_resume_job_approve(mock_resume):
    mock_resume.return_value = {
        "thread_id": "test-thread-123",
        "status": "resumed",
        "final_action": "Approve"
    }

    response = client.post("/api/jobs/test-thread-123/resume", json={
        "action": "Approve",
        "justification": "Producto verificado manualmente."
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resumed"
    assert data["final_action"] == "Approve"
    mock_resume.assert_called_once_with(
        "test-thread-123", "Approve", "Producto verificado manualmente."
    )


@patch("backend.main.resume_graph_execution", new_callable=AsyncMock)
def test_resume_job_block(mock_resume):
    mock_resume.return_value = {
        "thread_id": "test-thread-123",
        "status": "resumed",
        "final_action": "Block"
    }

    response = client.post("/api/jobs/test-thread-123/resume", json={
        "action": "Block"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["final_action"] == "Block"
    # justification es None cuando no se envía
    mock_resume.assert_called_once_with("test-thread-123", "Block", None)


@patch("backend.main.resume_graph_execution", new_callable=AsyncMock)
def test_resume_job_error(mock_resume):
    mock_resume.side_effect = Exception("Graph compilation failed")

    response = client.post("/api/jobs/test-thread-123/resume", json={"action": "Block"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error resuming job"}