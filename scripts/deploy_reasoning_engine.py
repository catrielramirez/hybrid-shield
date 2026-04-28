import os
import sys
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv

# 1. Cargar configuración del entorno
load_dotenv()

PROJECT_ID = "ecommerce-police-portfolio"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://ecommerce-police-portfolio-buckets"


REPO_URL = "https://github.com/catrielramirez/hybrid-shield.git"

# 3. Inicializar Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

if __name__ == "__main__":
    print(f"Iniciando despliegue remoto desde GitHub...")
    print(f"Repositorio: {REPO_URL}")
    print(f"Ubicación: {LOCATION}")
    print("-" * 50)

    try:
        # 4. Creación del Reasoning Engine usando la fuente de GitHub
        # El primer argumento es el PATH del builder dentro del repo (formato string)
        remote_engine = reasoning_engines.ReasoningEngine.create(
            "backend.agents.moderator.builder.moderator_runnable_builder",
            display_name="SemanticShield_GitHub_Final",
            requirements="scripts/requirements_reasoning_engine.txt",
            extra_packages=["backend"],
            gcs_source_path=REPO_URL,
        )

        print("\n" + "="*50)
        print("¡DESPLIEGUE EXITOSO DESDE GITHUB!")
        print(f"Resource ID: {remote_engine.resource_name}")
        print("="*50)
        print("\nCopia el Resource ID arriba y actualiza tu archivo .env")

    except Exception as e:
        print(f"\nERROR DURANTE EL DESPLIEGUE:")
        print(str(e))
        sys.exit(1)