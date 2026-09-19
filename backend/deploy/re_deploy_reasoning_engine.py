import os
import sys
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv

# 1. AJUSTE DE ENTORNO: Carga dinámica del .env desde el backend
ruta_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
load_dotenv(dotenv_path=ruta_env)

# 2. CONFIGURACIÓN DE RUTAS: Aseguramos que Python encuentre el módulo interno de agentes
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importación de la clase Wrapper del agente
import config
from agents.moderator.graph import HybridShieldAgent

# 3. ID DEL AGENTE EXISTENTE (seteado en .env tras el primer deploy)
REASONING_ENGINE_ID = config.get_reasoning_engine_id()

# 4. PARÁMETROS DEL PROYECTO
PROJECT_ID = config.get_project_id()
LOCATION = config.get_reasoning_engine_location()
STAGING_BUCKET = f"gs://{PROJECT_ID}-vertex-staging"

print("Inicializando la SDK de Vertex AI...")
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET
)

print("Instanciando el agente...")
agente_instancia = HybridShieldAgent()

print("Preparando e inyectando variables de configuración en la instancia...")
env_vars = {}
variables_criticas = ["DB_CONNECTION_NAME", "DB_NAME", "DB_USER", "DB_PASS", "GOOGLE_CLOUD_PROJECT", "DATA_STORE_ID", "ENGINE_ID"]

for key in variables_criticas:
    valor = os.getenv(key)
    if valor:
        env_vars[key] = valor

agente_instancia.env_vars = env_vars

print(f"Actualizando el agente en Vertex AI (ID: {REASONING_ENGINE_ID})...")

# LLAMADA DE ACTUALIZACIÓN: Se apunta al recurso existente como argumento posicional
resource_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}"
remote_agent = reasoning_engines.ReasoningEngine(resource_path)

# Truco estratégico: Cambiamos el contexto de ejecución a la carpeta 'backend'
# para usar rutas relativas limpias y evitar problemas de empaquetado en Windows
base_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(base_backend_dir)

remote_agent.update(
    reasoning_engine=agente_instancia,
    requirements="agents/moderator/requirements.txt",
    extra_packages=["./agents", "config.py"],
)

print("\n========================================================")
print("¡Actualización Exitosa! El agente ya ha sido actualizado en GCP.")
print("========================================================")