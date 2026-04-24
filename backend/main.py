import os
import uuid
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import google.cloud.logging
import logging
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage
from google.auth import default
from google.auth.transport import requests

# ================================================================
# Logging Configuration
# ================================================================
client = google.cloud.logging.Client()
client.setup_logging()
logger = logging.getLogger("moderation_pipeline")

from backend.agents.moderator.services.firestore_service import update_job_status

# ================================================================
# Initialization
# ================================================================
# Find project root (one level up from backend/)
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ecommerce-police-portfolio-buckets")
SERVICE_ACCOUNT_EMAIL = "679252770153-compute@developer.gserviceaccount.com"

if not PROJECT_ID:
    logger.warning("GOOGLE_CLOUD_PROJECT is not set.")

# GCS Credentials & Storage Client
credentials, project_id = default()
auth_request = requests.Request()
credentials.refresh(auth_request)  # Obtain token needed for IAM signing
storage_client = storage.Client(credentials=credentials)

# ================================================================
# FastAPI App
# ================================================================
app = FastAPI(title="Semantic Shield Moderation API")

# Setup CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Diagnostic endpoint to verify API status."""
    return {
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ================================================================
# Request Model
# ================================================================
class MetadataRequest(BaseModel):
    filename: str
    content_type: str = "image/jpeg"
    title: str
    description: str
    price: float


# ================================================================
# Unified Ingestion Endpoint
# ================================================================
@app.post("/metadata")
async def create_metadata(request: MetadataRequest):
    """
    Single ingestion endpoint that consolidates the entire intake flow:
    1. Generates a unique job_id (UUID).
    2. Creates a V4 Signed URL for the client to perform a Direct Binary Upload.
    3. Persists the received metadata JSON to Cloud Storage.
    4. Initializes the job record in Firestore with PENDING status.

    Returns the upload_url and job_id so the frontend can proceed
    with the binary upload immediately.
    """
    try:
        # --- Step 1: Generate unique job_id ---
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        date_prefix = now.strftime("%Y/%m/%d")

        bucket = storage_client.bucket(GCS_BUCKET_NAME)

        # --- Step 2: Generate V4 Signed URL for image upload ---
        image_blob_name = f"imagenes_ingesta/{date_prefix}/{job_id}_{request.filename}"
        image_blob = bucket.blob(image_blob_name)

        upload_url = image_blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=request.content_type,
            service_account_email=SERVICE_ACCOUNT_EMAIL,
            access_token=credentials.token,
        )

        # --- Step 3: Persist metadata JSON to Cloud Storage ---
        metadata_blob_name = f"metadata_ingesta/{date_prefix}/{job_id}.json"
        metadata_blob = bucket.blob(metadata_blob_name)

        metadata_content = request.model_dump()
        metadata_content["job_id"] = job_id
        metadata_content["gcs_image_uri"] = f"gs://{GCS_BUCKET_NAME}/{image_blob_name}"
        metadata_content["created_at"] = now.isoformat()

        metadata_blob.upload_from_string(
            data=json.dumps(metadata_content, indent=2),
            content_type="application/json",
        )

        logger.info(f"Metadata persisted to GCS: {metadata_blob_name}")

        # --- Step 4: Initialize job in Firestore ---
        update_job_status(job_id, "PENDING")

        logger.info(f"Ingestion flow completed for job_id={job_id}")

        # --- Response to Frontend ---
        return {
            "upload_url": upload_url,
            "job_id": job_id,
        }

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process ingestion request")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
