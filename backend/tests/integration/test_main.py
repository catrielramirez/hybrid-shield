import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Mockear inicializaciones a nivel de módulo en main.py que conectan con GCP
with patch("google.cloud.logging.Client"), \
     patch("google.auth.default", return_value=(MagicMock(), "test-project")), \
     patch("google.cloud.storage.Client"), \
     patch("vertexai.Client"):
    from backend.main import app

client = TestClient(app)

def test_health_check():
    """Prueba el endpoint de health check."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "timestamp" in data


@patch("backend.main.storage_client")
def test_get_upload_url(mock_storage_client):
    """Prueba la generación de URL firmada (signed URL) para la subida de imágenes."""
    # Configurar mocks de Cloud Storage
    mock_bucket = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/mock-signed-url"

    payload = {
        "filename": "producto.jpg",
        "content_type": "image/jpeg"
    }
    
    response = client.post("/get-upload-url", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["upload_url"] == "https://storage.googleapis.com/mock-signed-url"
    
    # Verificar que se llamó a GCS con el bucket correcto
    mock_storage_client.bucket.assert_called_once()
    mock_blob.generate_signed_url.assert_called_once()


@patch("backend.main.storage_client")
@patch("backend.main.update_job_status")
@patch("backend.main.agent")
def test_metadata_endpoint(mock_agent, mock_update_status, mock_storage_client):
    """
    Prueba el endpoint de recepción de metadata.
    Verifica que se persista en GCS y que se actualice Firestore e invoque al agente en background.
    """
    mock_bucket = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    payload = {
        "job_id": "test-job-id-12345",
        "filename": "producto.jpg",
        "content_type": "image/jpeg",
        "title": "Reloj de prueba",
        "description": "Un reloj muy bonito para testear.",
        "price": 120.5
    }
    
    response = client.post("/metadata", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["job_id"] == "test-job-id-12345"
    assert "metadata_path" in data
    
    # Verificar que se intentó subir la metadata a Cloud Storage
    mock_bucket.blob.assert_called()
    mock_blob.upload_from_string.assert_called_once()
    
    # Verificar que se intentó inicializar el trabajo en Firestore
    mock_update_status.assert_called_once_with("test-job-id-12345", "PENDING")


@patch("backend.main.get_job_status")
def test_get_job_status_found(mock_get_status):
    """Prueba la consulta de estado de un job cuando existe."""
    mock_get_status.return_value = {
        "status": "COMPLETED",
        "result": "approved",
        "reasons": []
    }
    
    response = client.get("/jobs/test-job-id-12345")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["result"] == "approved"
    mock_get_status.assert_called_once_with("test-job-id-12345")


@patch("backend.main.get_job_status")
def test_get_job_status_not_found(mock_get_status):
    """Prueba la consulta de estado de un job inexistente (404)."""
    mock_get_status.return_value = None
    
    response = client.get("/jobs/job-inexistente")
    
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    mock_get_status.assert_called_once_with("job-inexistente")
