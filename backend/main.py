import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import google.cloud.logging
import logging
import vertexai
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage

# ================================================================
# Logging & Tracing Configuration
# ================================================================
client = google.cloud.logging.Client()
client.setup_logging()
logger = logging.getLogger("moderation_pipeline")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

trace.set_tracer_provider(TracerProvider())
cloud_trace_exporter = CloudTraceSpanExporter()
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(cloud_trace_exporter)
)
tracer = trace.get_tracer("moderation_pipeline")


from vertexai.preview import reasoning_engines
from backend.agents.moderator.services.firestore_service import update_job_status

# ================================================================
# Initialization
# ================================================================
# Find project root (one level up from backend/)
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ecommerce-police-portfolio-buckets")
NEXTJS_PUBLIC_DIR = os.getenv('NEXTJS_PUBLIC_DIR', str(project_root / 'frontend' / 'public'))
REASONING_ENGINE_ID = os.getenv("REASONING_ENGINE_RESOURCE_ID")

if PROJECT_ID and LOCATION: 
    vertexai.init(project=PROJECT_ID, location=LOCATION)
else:
    logger.warning("GOOGLE_CLOUD_PROJECT or LOCATION is not set.")

# GCS Storage Client
storage_client = storage.Client()

if REASONING_ENGINE_ID:
    try:
        logger.info(f"Connecting to Reasoning Engine: {REASONING_ENGINE_ID}")
        active_graph = reasoning_engines.ReasoningEngine(REASONING_ENGINE_ID)
    except Exception as e:
        logger.error(f"Failed to connect to Reasoning Engine: {e}. Falling back to local graph.")
        from backend.agents.moderator.graph import create_moderator_graph
        active_graph = create_moderator_graph()
else:
    from backend.agents.moderator.graph import create_moderator_graph
    active_graph = create_moderator_graph()

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

class AnalyzeRequest(BaseModel):
    thread_id: str
    gcs_uri: str
    title: str
    description: str
    price: float


class ReviewRequest(BaseModel):
    thread_id: str
    decision: dict


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


@app.post("/analyze")
async def analyze_product(request: AnalyzeRequest):
    """
    Invokes the LangGraph pipeline with the provided product data and GCS URI.
    Handles autonomous results or flags for manual moderation.
    """
    try:
        thread_id = request.thread_id
        logger.info(f"Processing moderation request: {thread_id}", extra={"thread_id": thread_id})
        
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "input_data": {
                "title": request.title,
                "description": request.description,
                "price": request.price
            },
            "thread_id": thread_id,
            "gcs_uri": request.gcs_uri,
            "audit_log": [],
            "requires_human_intervention": False,
            "early_blocked": False
        }
        
        with tracer.start_as_current_span("moderation_analysis"):
            # Invoke the graph (Managed or Local)
            if REASONING_ENGINE_ID and hasattr(active_graph, "query"):
                # Remote Reasoning Engine call
                final_state = active_graph.query(input_data=initial_state, thread_id=thread_id)
            else:
                # Local LangGraph invocation
                final_state = active_graph.invoke(initial_state, config)
            
            # Check for human-in-the-loop interruption
            if final_state.get("requires_human_intervention"):
                return {
                    "status": "pending_human_review",
                    "thread_id": thread_id,
                    "risk_score": final_state.get("risk_score"),
                    "reasoning": final_state.get("reasoning")
                }
            
        return {
            "status": "completed",
            "thread_id": thread_id,
            "final_action": final_state.get("final_action"),
            "risk_score": final_state.get("risk_score"),
            "reasoning": final_state.get("reasoning"),
            "policy_citations": final_state.get("policy_citations", [])
        }
        
    except Exception as e:
        logger.error(f"Error during moderation analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/review")
async def review_product(request: ReviewRequest):
    """
    Submits a manual decision from a human moderator, resumes the moderation flow,
    and ensures the audit record is finalized with the human feedback.
    """
    try:
        config = {"configurable": {"thread_id": request.thread_id}}
        
        if REASONING_ENGINE_ID and hasattr(active_graph, "query"):
            # Managed resumption via Reasoning Engine
            final_state = active_graph.query(
                thread_id=request.thread_id, 
                human_feedback=request.decision
            )
        else:
            # Local LangGraph resumption
            active_graph.update_state(
                config, 
                {"human_feedback": request.decision, "requires_human_intervention": False}, 
                as_node="human_pause"
            )
            
            logger.info(f"Human review received for thread_id: {request.thread_id}. Resuming graph...")
            final_state = active_graph.invoke(None, config)
        
        return {
            "status": "success",
            "message": "Human review processed and audit record persisted.",
            "thread_id": request.thread_id,
            "final_action": final_state.get("final_action"),
            "risk_score": final_state.get("risk_score")
        }
        
    except Exception as e:
        logger.error(f"Error during human review submission: {e}")
        raise HTTPException(status_code=500, detail=f"Review processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
