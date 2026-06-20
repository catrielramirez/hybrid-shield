import os
import sys
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv

# 1. AJUSTE DE ENTORNO: Carga dinámica del .env desde el backend
RUTA_DEPLOY = os.path.dirname(os.path.abspath(__file__)) # carpeta backend/deploy
BACKEND_DIR = os.path.abspath(os.path.join(RUTA_DEPLOY, "..")) # carpeta backend

ruta_env = os.path.join(BACKEND_DIR, ".env")
load_dotenv(dotenv_path=ruta_env)

# 2. CONFIGURACIÓN DE RUTAS Y ENTORNO DE EJECUCIÓN
# Cambiamos el directorio de trabajo a 'backend' para resolver todas las rutas como relativas
# y evitar el error de tar/zip con rutas absolutas de Windows en Vertex AI SDK.
os.chdir(BACKEND_DIR)
sys.path.append(".")

# Importación utilizando el espacio de nombres completo 'agents.moderator'
from agents.moderator.graph import HybridShieldAgent

# Definición de rutas relativas limpias para Vertex AI
PATH_REQUIREMENTS = "agents/moderator/requirements.txt"
PATH_EXTRA_PACKAGES = "./agents"

# 3. PARÁMETROS DEL PROYECTO
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecommerce-police-portfolio")
LOCATION = "us-central1"
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
# Extraemos las variables críticas del .env local
env_vars = {}
variables_criticas = ["DB_CONNECTION_NAME", "DB_NAME", "DB_USER", "DB_PASS", "GOOGLE_CLOUD_PROJECT", "DATA_STORE_ID", "ENGINE_ID"]

for key in variables_criticas:
    valor = os.getenv(key)
    if valor:
        env_vars[key] = valor

agente_instancia.env_vars = env_vars

print("Empaquetando y subiendo el agente a Vertex AI Agent Engine...")
print("Nota: Se aplicará el archivo .gcloudignore automáticamente.")

remote_agent = reasoning_engines.ReasoningEngine.create(
    reasoning_engine=agente_instancia,
    requirements=PATH_REQUIREMENTS,
    extra_packages=[PATH_EXTRA_PACKAGES],
    display_name="hybrid_shield_moderator_agent",
)

print("\n========================================================")
print("¡Despliegue Exitoso! El agente ya está operativo en GCP.")
print(f"Resource Name: {remote_agent.resource_name}")
print(f"Reasoning Engine ID: {remote_agent.name}")
print("========================================================")