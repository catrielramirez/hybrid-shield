import os
import uuid
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import google.cloud.logging
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage
from google.auth import default
from google.auth.transport import requests
import asyncio

# ================================================================
# Logging Configuration
# ================================================================
client = google.cloud.logging.Client()
client.setup_logging()
logger = logging.getLogger("moderation_pipeline")

from agents.moderator.services.firestore_service import update_job_status, get_job_status

# ================================================================
# Initialization
# ================================================================
project_root = Path(__file__).resolve().parent
# En lugar de solo load_dotenv(), usa esto:
dotenv_path = project_root / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    logger.warning(".env file not found, skipping (assuming environment variables are set in Cloud Run).")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ecommerce-police-media-uploads")
SERVICE_ACCOUNT_EMAIL = "679252770153-compute@developer.gserviceaccount.com"

if not PROJECT_ID:
    logger.warning("GOOGLE_CLOUD_PROJECT is not set.")

credentials, project_id = default()
auth_request = requests.Request()
credentials.refresh(auth_request)
storage_client = storage.Client(credentials=credentials)

# ================================================================
# Lifespan Management (Sustituye a @app.on_event)
# ================================================================
async def warmup_services():
    """Background task to initialize Firestore client."""
    try:
        logger.info("Warming up Firestore...")
        await get_job_status("dummy_warmup_id")
        logger.info("Services warmup successful.")
    except Exception as e:
        logger.warning(f"Services warmup failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lógica de startup
    asyncio.create_task(warmup_services())
    yield
    # Lógica de shutdown iría acá si fuera necesaria

# ================================================================
# FastAPI App
# ================================================================
app = FastAPI(title="Semantic Shield Moderation API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
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
# Request Models
# ================================================================
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

# ================================================================
# Step 1: Generate Upload URL
# ================================================================
@app.post("/get-upload-url")
async def get_upload_url(request: UploadUrlRequest):
    """
    Step 1: Genera un job_id único y una URL firmada v4 para la carga de la imagen original.
    Sigue la estructura: items/{job_id}/raw_image.ext
    """
    try:
        job_id = str(uuid.uuid4())
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        # Extraer la extensión original (.jpg, .png, etc.)
        file_extension = Path(request.filename).suffix or ".jpg"
        image_blob_name = f"items/{job_id}/raw_image{file_extension}"
        image_blob = bucket.blob(image_blob_name)

        upload_url = image_blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=request.content_type,
            service_account_email=SERVICE_ACCOUNT_EMAIL,
            access_token=credentials.token,
        )

        logger.info(f"Generated upload URL for job_id={job_id} at path {image_blob_name}")

        return {
            "job_id": job_id,
            "upload_url": upload_url
        }

    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")

# ================================================================
# Step 2: Persist Metadata
# ================================================================
@app.post("/metadata")
async def create_metadata(request: MetadataRequest):
    """
    Step 2: Recibe la metadata una vez que el frontend terminó de subir la imagen.
    Persiste el JSON en items/{job_id}/metadata.json, lo que dispara la Cloud Function.
    """
    try:
        job_id = request.job_id
        now = datetime.now(timezone.utc)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)

        # Reconstruir la ruta exacta de la imagen subida en el Step 1
        file_extension = Path(request.filename).suffix or ".jpg"
        image_blob_name = f"items/{job_id}/raw_image{file_extension}"
        
        # Nueva ruta de destino para el archivo de metadatos JSON
        metadata_blob_name = f"items/{job_id}/metadata.json"
        metadata_blob = bucket.blob(metadata_blob_name)

        metadata_content = request.model_dump()
        metadata_content["gcs_image_uri"] = f"gs://{GCS_BUCKET_NAME}/{image_blob_name}"
        metadata_content["created_at"] = now.isoformat()

        # Al subir este archivo, Eventarc gatilla automáticamente la Cloud Function
        metadata_blob.upload_from_string(
            data=json.dumps(metadata_content, indent=2),
            content_type="application/json",
        )

        logger.info(f"Metadata persisted to GCS: {metadata_blob_name} (Cloud Function triggered)")

        # Inicializar el estado en Firestore para que el frontend pueda hacer polling
        await update_job_status(job_id, "PENDING")

        return {
            "status": "success",
            "job_id": job_id,
            "metadata_path": metadata_blob_name
        }

    except Exception as e:
        logger.error(f"Metadata persistence failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process metadata request")

# ================================================================
# Job Status Tracking
# ================================================================
@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Endpoint para que el frontend consulte el estado del proceso en Firestore."""
    try:
        logger.info(f"Polling job status for job_id={job_id}")
        job_data = await get_job_status(job_id)
        
        if not job_data:
            logger.warning(f"Job not found in Firestore: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")
        
        status = job_data.get("status", "unknown")
        if status in ["ERROR", "FAILED"]:
            logger.error(f"Job {job_id} failed with data: {job_data}")
            raise HTTPException(
                status_code=500, 
                detail=f"Job processing failed: {job_data.get('metadata', {}).get('error', 'Unknown error')}"
            )

        logger.info(f"Job {job_id} status: {status}")
        return job_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)