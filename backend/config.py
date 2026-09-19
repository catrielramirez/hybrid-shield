"""
Centralized environment-variable access for the backend.

Deliberately built as plain functions, not an eagerly-evaluated class/
singleton: the Vertex AI Reasoning Engine deployment path
(HybridShieldAgent.set_up() in agents/moderator/graph.py) injects
credentials into an `env_vars` dict AFTER the module has already been
imported and unpickled at runtime. Reading env vars lazily, at call time,
is what makes that pattern work — a singleton built at import time would
capture stale or missing values.

Every default below mirrors a value that used to be hardcoded somewhere
in the codebase, so leaving a variable unset keeps existing behavior
unchanged.
"""
import os
from typing import Optional

_DEFAULT_PROJECT_ID = "ecommerce-police-portfolio"
_DEFAULT_LOCATION = "us-central1"
_DEFAULT_GCS_BUCKET = "ecommerce-police-media-uploads"
_DEFAULT_GOLDEN_DATASET_BUCKET = "ecommerce-police-portfolio-golden-dataset"
_DEFAULT_SERVICE_ACCOUNT_EMAIL = "679252770153-compute@developer.gserviceaccount.com"
_DEFAULT_FIRESTORE_DATABASE = "firestore-hybrid-shield"
_DEFAULT_DB_NAME = "agent_states"
_DEFAULT_CLOUD_SQL_REGION = "us-central1"
_DEFAULT_REASONING_ENGINE_LOCATION = "us-central1"


def _env(name: str, default: Optional[str] = None, overrides: Optional[dict] = None) -> Optional[str]:
    """Reads `name` from `overrides` first (Reasoning Engine env_vars), then os.environ."""
    if overrides:
        value = overrides.get(name)
        if value:
            return value
    return os.getenv(name, default)


def get_project_id(overrides: Optional[dict] = None) -> str:
    return _env("GOOGLE_CLOUD_PROJECT", _DEFAULT_PROJECT_ID, overrides)


def get_location(overrides: Optional[dict] = None) -> str:
    """Vertex AI (Gemini / Search) location. Intentionally separate from the
    Cloud SQL region below — GOOGLE_CLOUD_LOCATION may be set to "global"."""
    return _env("GOOGLE_CLOUD_LOCATION", _DEFAULT_LOCATION, overrides)


def get_gcs_bucket_name(overrides: Optional[dict] = None) -> str:
    """Bucket used by the upload/moderation API (main.py)."""
    return _env("GCS_BUCKET_NAME", _DEFAULT_GCS_BUCKET, overrides)


def get_golden_dataset_bucket(overrides: Optional[dict] = None) -> str:
    """Separate bucket used only by the offline eval script — not the uploads bucket above."""
    return _env("GOOGLE_CLOUD_BUCKET", _DEFAULT_GOLDEN_DATASET_BUCKET, overrides)


def get_service_account_email(overrides: Optional[dict] = None) -> str:
    return _env("SERVICE_ACCOUNT_EMAIL", _DEFAULT_SERVICE_ACCOUNT_EMAIL, overrides)


def get_data_store_id(overrides: Optional[dict] = None) -> Optional[str]:
    return _env("DATA_STORE_ID", None, overrides)


def get_engine_id(overrides: Optional[dict] = None) -> Optional[str]:
    return _env("ENGINE_ID", None, overrides) or get_data_store_id(overrides)


def get_firestore_project_id(overrides: Optional[dict] = None) -> str:
    return _env("FIRESTORE_PROJECT_ID", None, overrides) or get_project_id(overrides)


def get_firestore_database(overrides: Optional[dict] = None) -> str:
    return _env("FIRESTORE_DATABASE_ID", _DEFAULT_FIRESTORE_DATABASE, overrides)


def is_local_dev() -> bool:
    return os.getenv("GOOGLE_CLOUD_PROJECT") is None or os.getenv("LOCAL_DEV") == "true"


def get_allowed_origins(overrides: Optional[dict] = None) -> list[str]:
    raw = _env("ALLOWED_ORIGINS", "*", overrides) or "*"
    return [origin.strip() for origin in raw.split(",")]


def parse_cloud_sql_connection(overrides: Optional[dict] = None) -> dict:
    """
    Parses DB_CONNECTION_NAME ("project:region:instance") into its parts.
    Single source of truth for the Cloud SQL instance identity, used by both
    graph.py's checkpointer and audit_service.py's history reader so they
    always point at the same instance.
    """
    conn_name = _env("DB_CONNECTION_NAME", "", overrides) or ""
    parts = conn_name.split(":")
    project_id = parts[0] if len(parts) > 0 and parts[0] else get_project_id(overrides)
    region = parts[1] if len(parts) > 1 and parts[1] else _DEFAULT_CLOUD_SQL_REGION
    instance = parts[2] if len(parts) > 2 else ""
    return {
        "project_id": project_id,
        "region": region,
        "instance": instance,
        "connection_name": conn_name,
    }


def get_db_name(overrides: Optional[dict] = None) -> str:
    return _env("DB_NAME", _DEFAULT_DB_NAME, overrides)


def get_db_credentials(overrides: Optional[dict] = None) -> tuple[Optional[str], Optional[str]]:
    return _env("DB_USER", None, overrides), _env("DB_PASS", None, overrides)


def get_reasoning_engine_location() -> str:
    """Vertex AI Agent Engine deploy region (backend/deploy/*.py scripts only).
    Intentionally separate from GOOGLE_CLOUD_LOCATION, which may be "global"."""
    return os.getenv("REASONING_ENGINE_LOCATION", _DEFAULT_REASONING_ENGINE_LOCATION)


def get_reasoning_engine_id() -> str:
    """Deployed Reasoning Engine numeric ID, used by the re_deploy/delete/test
    scripts. Raises instead of silently defaulting: reusing a stale ID from a
    previous deployment would target the wrong (or a deleted) resource."""
    value = os.getenv("REASONING_ENGINE_ID")
    if not value:
        raise ValueError(
            "ERROR: REASONING_ENGINE_ID no configurado. "
            "Copiá el ID que imprime deploy_reasoning_engine.py a tu .env."
        )
    return value
