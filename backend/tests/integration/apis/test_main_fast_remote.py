"""
Smoke test remoto contra la FastAPI desplegada en Cloud Run.
Verifica que los endpoints críticos responden correctamente en producción.

NO requiere mocks — hace requests HTTP reales.
Requiere: google-auth, requests

Ejecutar con:
    python backend/tests/integration/test_main_remote.py

O con pytest (no requiere fixtures):
    pytest backend/tests/integration/test_main_remote.py -v -s
"""
import uuid
import json
import pytest
import requests
import google.auth
import google.auth.transport.requests

BASE_URL = "https://hybrid-shield-backend-679252770153.us-central1.run.app"

# ================================================================
# AUTH: Token de identidad para Cloud Run (IAM-protected)
# ================================================================

def _get_auth_headers() -> dict:
    """Obtiene un token de identidad para autenticarse contra Cloud Run."""
    try:
        credentials, _ = google.auth.default()
        auth_request = google.auth.transport.requests.Request()
        credentials.refresh(auth_request)
        token = credentials.token
        return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"[WARN] No se pudo obtener token de auth: {e}")
        print("[WARN] Intentando sin autenticación (solo funciona si el servicio es público).")
        return {}


HEADERS = _get_auth_headers()


# ================================================================
# HELPER
# ================================================================

def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


# ================================================================
# 1. HEALTH CHECK
# ================================================================

def test_remote_health_check():
    """El servicio debe estar online y responder 200."""
    response = requests.get(_url("/api/health"), headers=HEADERS, timeout=60)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "online"
    assert "timestamp" in data
    print(f"  ✓ Health check OK — timestamp: {data['timestamp']}")


# ================================================================
# 2. GET UPLOAD URL
# ================================================================

def test_remote_get_upload_url():
    """Debe generar un job_id y una URL firmada de GCS."""
    payload = {
        "filename": "smoke_test_image.jpg",
        "content_type": "image/jpeg"
    }
    response = requests.post(_url("/api/get-upload-url"), json=payload, headers=HEADERS, timeout=15)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "job_id" in data, "Response missing job_id"
    assert "upload_url" in data, "Response missing upload_url"
    assert data["upload_url"].startswith("https://"), "upload_url should be a valid HTTPS URL"
    print(f"  ✓ Upload URL generated — job_id: {data['job_id']}")
    return data["job_id"]


# ================================================================
# 3. JOB NOT FOUND
# ================================================================

def test_remote_job_not_found():
    """Un job_id inexistente debe devolver 404."""
    fake_id = f"nonexistent-{uuid.uuid4().hex[:8]}"
    response = requests.get(_url(f"/api/jobs/{fake_id}"), headers=HEADERS, timeout=10)

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    assert response.json()["detail"] == "Job not found"
    print(f"  ✓ 404 correctamente devuelto para job inexistente")


# ================================================================
# 4. AUDITOR DASHBOARD
# ================================================================

def test_remote_auditor_jobs():
    """El endpoint de auditor debe responder con una lista (puede estar vacía)."""
    response = requests.get(_url("/api/jobs/auditor"), headers=HEADERS, timeout=15)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Corrección aquí: validar que es un dict y comprobar sus claves internas
    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
    assert "historical" in data, "Missing 'historical' key in response"
    assert "pending" in data, "Missing 'pending' key in response"
    print(f"  ✓ Auditor jobs endpoint OK — {len(data['pending'])} pending, {len(data['historical'])} historical")

# ================================================================
# 5. AUDIT TRACE NOT FOUND
# ================================================================

def test_remote_audit_trace_not_found():
    """Un thread_id inexistente debe devolver 404."""
    fake_thread = f"fake-thread-{uuid.uuid4().hex[:8]}"
    response = requests.get(_url(f"/api/audit/trace/{fake_thread}"), headers=HEADERS, timeout=10)

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    print(f"  ✓ 404 correctamente devuelto para trace inexistente")


# ================================================================
# 6. RESUME JOB NOT FOUND
# ================================================================

def test_remote_resume_nonexistent_job():
    """
    Intentar resumir un job inexistente no debe crashear el servidor.
    Esperamos 500 (error interno al no encontrar el thread en el checkpointer)
    o 404 dependiendo de la implementación de resume_graph_execution.
    """
    fake_thread = f"fake-thread-{uuid.uuid4().hex[:8]}"
    response = requests.post(
        _url(f"/api/jobs/{fake_thread}/resume"),
        json={"action": "Approve", "justification": "Smoke test"},
        headers=HEADERS,
        timeout=15
    )

    # Aceptamos 500 o 404 — lo que NO aceptamos es un crash sin respuesta JSON
    assert response.status_code in (404, 500), (
        f"Expected 404 or 500, got {response.status_code}: {response.text}"
    )
    assert response.headers["content-type"].startswith("application/json"), (
        "Response must be JSON even on error"
    )
    print(f"  ✓ Resume con job inexistente devolvió {response.status_code} con JSON válido")


# ================================================================
# 7. FULL E2E FLOW: Upload URL → Metadata → Poll
# ================================================================

def test_remote_e2e_upload_and_metadata():
    """
    Flujo completo del lado del usuario:
    1. Solicitar upload URL → obtener job_id
    2. Enviar metadata → job creado como PENDING en Firestore
    3. Polling inmediato → job encontrado (PENDING o posterior)
    """
    # Step 1: get upload URL
    upload_response = requests.post(
        _url("/api/get-upload-url"),
        json={"filename": "e2e_test.jpg", "content_type": "image/jpeg"},
        headers=HEADERS,
        timeout=15
    )
    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]
    print(f"  ✓ Step 1 — job_id generado: {job_id}")

    # Step 2: send metadata (triggers pipeline via Eventarc — no esperamos resultado del agente)
    metadata_response = requests.post(
        _url("/api/metadata"),
        json={
            "job_id": job_id,
            "filename": "e2e_test.jpg",
            "content_type": "image/jpeg",
            "title": "Silla ergonómica smoke test",
            "description": "Test de integración remoto.",
            "price": 85.0
        },
        headers=HEADERS,
        timeout=15
    )
    assert metadata_response.status_code == 200
    meta_data = metadata_response.json()
    assert meta_data["status"] == "success"
    assert meta_data["job_id"] == job_id
    print(f"  ✓ Step 2 — metadata persistida: {meta_data['metadata_path']}")

    # Step 3: poll — el job debe existir en Firestore como PENDING
    poll_response = requests.get(_url(f"/api/jobs/{job_id}"), headers=HEADERS, timeout=10)
    assert poll_response.status_code == 200
    job_data = poll_response.json()
    assert job_data.get("status") is not None
    print(f"  ✓ Step 3 — job encontrado con status: {job_data['status']}")


# ================================================================
# RUNNER STANDALONE
# ================================================================

if __name__ == "__main__":
    tests = [
        test_remote_health_check,
        test_remote_get_upload_url,
        test_remote_job_not_found,
        test_remote_auditor_jobs,
        test_remote_audit_trace_not_found,
        test_remote_resume_nonexistent_job,
        test_remote_e2e_upload_and_metadata,
    ]

    passed = 0
    failed = 0

    print(f"\n{'='*60}")
    print(f"Smoke Test — {BASE_URL}")
    print(f"{'='*60}\n")

    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"[PASS] {name}\n")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}")
            print(f"       {e}\n")
            failed += 1

    print(f"{'='*60}")
    print(f"Resultado: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")