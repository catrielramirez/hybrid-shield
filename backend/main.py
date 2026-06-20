import os
import uuid
import json
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import google.cloud.logging
from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage

# ================================================================
# 1. INITIALIZATION & ENV VARS
# ================================================================
project_root = Path(__file__).resolve().parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=dotenv_path)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ecommerce-police-media-uploads")
SERVICE_ACCOUNT_EMAIL = "679252770153-compute@developer.gserviceaccount.com"
IS_LOCAL = PROJECT_ID is None or os.getenv("LOCAL_DEV") == "true"

# ================================================================
# 2. LOGGING CONFIGURATION
# ================================================================
try:
    if not IS_LOCAL:
        client = google.cloud.logging.Client()
        client.setup_logging()
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("moderation_pipeline")
except Exception as e:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("moderation_pipeline")
    logger.info(f"Cloud logging setup failed, using local logging. Reason: {e}")

# ================================================================
# 3. SERVICES IMPORTS (Debe ir después de configurar el logger)
# ================================================================
from agents.moderator.services.firestore_service import update_job_status, get_job_status, get_auditor_jobs
from agents.moderator.services.audit_service import get_full_audit_trace, resume_graph_execution

# ================================================================
# 4. GOOGLE CLOUD STORAGE CREDENTIALS CONTROL
# ================================================================
if IS_LOCAL:
    logger.info("Local environment detected: configuring impersonated credentials.")
    from google.auth import default
    from google.auth.impersonated_credentials import impersonated_credentials
    
    base_credentials, _ = default()
    credentials = impersonated_credentials.Credentials(
        source_credentials=base_credentials,
        target_principal=SERVICE_ACCOUNT_EMAIL,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        lifetime=3600
    )
    storage_client = storage.Client(credentials=credentials)
else:
    logger.info("Production environment detected: using native Cloud Run service account.")
    storage_client = storage.Client()

# ================================================================
# 5. FASTAPI LIFESPAN & APP
# ================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lógica de startup (puedes agregar validaciones de conexión aquí si es necesario)
    yield
    # Lógica de shutdown

app = FastAPI(title="Semantic Shield Moderation API", lifespan=lifespan)

# ================================================================
# 6. CORS CONFIGURATION
# ================================================================
# Default to "*" so that if the .env file is ignored/missing in Cloud Run, CORS won't block requests
raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [origin.strip() for origin in raw_origins.split(",")]

# FastAPI does not allow allow_origins=["*"] when allow_credentials=True.
# Since we don't use sessions/cookies, we can safely disable credentials if "*" is present.
allow_all = "*" in origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=False if allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# 7. PYDANTIC MODELS & EXCEPTION HANDLERS
# ================================================================
class ResumeRequest(BaseModel):
    action: str
    justification: Optional[str] = None

class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str = "image/jpeg"

class MetadataRequest(BaseModel):
    job_id: str
    filename: str
    content_type: str = "image/jpeg"
    title: str
    description: str
    price: float

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url}\nError: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please check logs for details."}
    )

# ================================================================
# 8. ENDPOINTS: STEP 1 (UPLOAD DE IMÁGENES)
# ================================================================
@app.post("/api/get-upload-url")
async def get_upload_url(request: UploadUrlRequest):
    """Genera un job_id único y una URL firmada v4 para la carga de la imagen original."""
    try:
        job_id = str(uuid.uuid4())
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        file_extension = Path(request.filename).suffix or ".jpg"
        image_blob_name = f"items/{job_id}/raw_image{file_extension}"
        image_blob = bucket.blob(image_blob_name)

        import google.auth

        # Obtención explícita
        service_account_email = os.getenv("SERVICE_ACCOUNT_EMAIL")

        if not service_account_email:
            credentials, _ = google.auth.default()
            service_account_email = getattr(credentials, "service_account_email", None)

        if not service_account_email:
            raise ValueError("ERROR: SERVICE_ACCOUNT_EMAIL no configurado.")

        upload_url = image_blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=request.content_type,
            service_account_email=service_account_email
        )

        logger.info(f"Generated upload URL for job_id={job_id} at path {image_blob_name}")
        return {
            "job_id": job_id,
            "upload_url": upload_url
        }
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")

@app.post("/api/upload-direct")
async def upload_direct(file: UploadFile = File(...)):
    """Recibe la imagen y la sube directo al bucket, evitando proxies locales."""
    try:
        job_id = str(uuid.uuid4())
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        file_extension = Path(file.filename).suffix or ".jpg"
        image_blob_name = f"items/{job_id}/raw_image{file_extension}"
        image_blob = bucket.blob(image_blob_name)

        contents = await file.read()
        image_blob.upload_from_string(contents, content_type=file.content_type)
        
        logger.info(f"Directly uploaded file for job_id={job_id} at path {image_blob_name}")
        return {"job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to upload directly: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ================================================================
# 9. ENDPOINTS: STEP 2 (METADATA & DISPARO PIPELINE)
# ================================================================
@app.post("/api/metadata")
async def create_metadata(request: MetadataRequest):
    """Persiste el JSON en triggers/{job_id}/metadata.json, disparando Eventarc."""
    try:
        job_id = request.job_id
        now = datetime.now(timezone.utc)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)

        file_extension = Path(request.filename).suffix or ".jpg"
        image_blob_name = f"items/{job_id}/raw_image{file_extension}"
        
        metadata_blob_name = f"triggers/{job_id}/metadata.json"
        metadata_blob = bucket.blob(metadata_blob_name)

        metadata_content = request.model_dump()
        metadata_content["gcs_image_uri"] = f"gs://{GCS_BUCKET_NAME}/{image_blob_name}"
        metadata_content["created_at"] = now.isoformat()

        metadata_blob.upload_from_string(
            data=json.dumps(metadata_content, indent=2),
            content_type="application/json",
        )

        logger.info(f"Metadata persisted to GCS: {metadata_blob_name} (Cloud Function triggered)")
        await update_job_status(job_id, "PENDING")

        return {
            "status": "success",
            "job_id": job_id,
            "metadata_path": metadata_blob_name
        }
    except Exception as e:
        logger.error(f"Metadata persistence failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process metadata request")

# ================================================================
# 10. JOB STATUS & POLLING TRACKING
# ================================================================
@app.get("/api/jobs/auditor")
async def api_get_auditor_jobs():
    """Consulta casos pendientes e históricos para el Auditor Dashboard."""
    try:
        logger.info("Fetching auditor jobs (pending and historical)")
        jobs = await get_auditor_jobs()
        return jobs
    except Exception as e:
        logger.error(f"Error fetching auditor jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Polling de estado del proceso en Firestore."""
    try:
        logger.info(f"Polling job status for job_id={job_id}")
        job_data = await get_job_status(job_id)
        
        if not job_data:
            logger.warning(f"Job not found in Firestore: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")
        
        status = job_data.get("status", "unknown")
        if status in ["ERROR", "FAILED"]:
            logger.error(f"Job {job_id} failed with data: {job_data}")
            err_detail = job_data.get('metadata', {}).get('error', 'Unknown error')
            raise HTTPException(status_code=500, detail=f"Job processing failed: {err_detail}")

        return job_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/jobs/{job_id}/image")
async def get_job_image(job_id: str):
    """Retorna la imagen del job descargándola de GCS o redirigiendo a una URL firmada."""
    from fastapi.responses import StreamingResponse, RedirectResponse
    try:
        logger.info(f"Fetching image proxy for job_id={job_id}")
        job_data = await get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        gcs_uri = job_data.get("gcs_image_uri") or job_data.get("gcs_uri") or job_data.get("image_url")
        if not gcs_uri:
            # Fallback a ver si está en input_data o metadata
            input_data = job_data.get("input_data") or {}
            metadata = job_data.get("metadata") or {}
            gcs_uri = input_data.get("gcs_image_uri") or input_data.get("gcs_uri") or input_data.get("image_url") or metadata.get("gcs_image_uri") or metadata.get("gcs_uri") or metadata.get("image_url")

        if not gcs_uri:
            raise HTTPException(status_code=404, detail="No image URI found for this job")
            
        if not gcs_uri.startswith("gs://"):
            if gcs_uri.startswith("http"):
                return RedirectResponse(url=gcs_uri)
            raise HTTPException(status_code=404, detail="Invalid image URI format")
            
        parts = gcs_uri[5:].split("/", 1)
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid GCS URI")
            
        bucket_name, blob_name = parts[0], parts[1]
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Image blob not found in storage")
            
        def iterfile():
            yield blob.download_as_bytes()
            
        content_type = blob.content_type or "image/jpeg"
        return StreamingResponse(iterfile(), media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image proxy for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving image")

# ================================================================
# 11. AUDIT & HITL RESUMPTION ENDPOINTS
# ================================================================
@app.get("/api/audit/trace/{thread_id}")
async def api_get_full_audit_trace(thread_id: str):
    """Devuelve la traza forense completa desde PostgresSaver."""
    try:
        logger.info(f"Fetching deep trace for thread_id={thread_id}")
        trace = await get_full_audit_trace(thread_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Audit trace not found")
        return trace
    except HTTPException:
        raise
    except Exception as e:
        # Si la función interna falla porque el thread no existe, interceptamos el mensaje
        err_msg = str(e).lower()
        if any(keyword in err_msg for keyword in ["not found", "does not exist", "keyerror", "empty", "none"]):
            logger.warning(f"Trace not found for thread_id={thread_id}. Reason: {e}")
            raise HTTPException(status_code=404, detail="Audit trace not found")
            
        logger.error(f"Database read failed for deep trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error reading audit trace")

@app.post("/api/jobs/{thread_id}/resume")
async def api_resume_job(thread_id: str, request: ResumeRequest):
    """Retoma la ejecución del grafo inyectando la decisión humana."""
    try:
        logger.info(f"Resuming job {thread_id} with action {request.action}")
        
        # Verify if thread_id/job exists
        job_data = await get_job_status(thread_id)
        if not job_data:
            logger.warning(f"Resume requested for nonexistent thread_id={thread_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
            
        result = await resume_graph_execution(thread_id, request.action, request.justification)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume job {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error resuming job")
        
# ================================================================
# 12. WEB SERVER RUNNER
# ================================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0" if not IS_LOCAL else "127.0.0.1"
    
    logger.info(f"Starting Uvicorn server on {host}:{port}")
    uvicorn.run(
        "main:app", 
        host=host, 
        port=port, 
        reload=True if IS_LOCAL else False
    )