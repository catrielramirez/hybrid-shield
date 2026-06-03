import os
import pytest
import pytest_asyncio
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Carga de variables de entorno (al inicio para asegurar que todos los módulos tengan acceso)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from datetime import datetime  
from google.cloud import firestore
from backend.agents.moderator.graph import HybridShieldAgent


@pytest_asyncio.fixture(scope="session")
async def app():
    """Inicializa el grafo del agente una vez para toda la sesión (más eficiente)."""
    return await HybridShieldAgent()._build_graph()

@pytest.fixture
def unique_id():
    """
    ID único universal para threads de LangGraph y Firestore.
    Reemplaza a thread_id y firestore_test_id para evitar redundancia.
    """
    return f"test-job-{uuid.uuid4().hex[:8]}"

@pytest.fixture(autouse=True)
def cleanup_firestore(unique_id):
    """Limpia el documento de prueba en Firestore después de cada test."""
    yield
    try:
        db = firestore.Client(database="firestore-hybrid-shield")
        db.collection("jobs").document(unique_id).delete()
    except Exception:
        pass # Evita que un error en limpieza rompa el resultado del test

# --- Fixtures de Datos de Prueba ---

@pytest.fixture
def product_sample():
    return {
        "title": "Reloj h32",
        "description": "varios colores",
        "price": 450.0
    }

@pytest.fixture
def real_gcs_uri():
    return "gs://ecommerce-police-portfolio-golden-dataset/balanced/passed/003.jpg"