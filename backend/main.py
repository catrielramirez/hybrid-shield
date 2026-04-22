import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import google.cloud.logging
import logging
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

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

if not PROJECT_ID:
    logger.warning("GOOGLE_CLOUD_PROJECT is not set.")

# GCS Storage Client
storage_client = storage.Client()

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



@app.get("/generate-upload-url")
async def generate_upload_url(
    filename: str = Query(...),
    content_type: str = Query("image/jpeg")
):
    """Generates a V4 signed URL for uploading an image to GCS."""
    try:
        thread_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        date_prefix = now.strftime("%Y/%m/%d")
        
        blob_name = f"imagenes_ingesta/{date_prefix}/{thread_id}_{filename}"
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(blob_name)

        # Generate V4 Signed URL for PUT
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
        )

        gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"

        # Initialize job in Firestore
        update_job_status(thread_id, "PENDING")
        
        return {
            "upload_url": url,
            "gcs_uri": gcs_uri,
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
