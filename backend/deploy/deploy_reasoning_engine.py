import os
import sys
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv

# 1. AJUSTE DE ENTORNO: Carga dinámica del .env desde la raíz del monorepo
ruta_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(dotenv_path=ruta_env)

# 2. CONFIGURACIÓN DE RUTAS: Aseguramos que Python encuentre el módulo interno de agentes
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

# Importación de la clase Wrapper del agente
from agents.moderator.graph import HybridShieldAgent

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
variables_criticas = ["DB_CONNECTION_NAME", "DB_NAME", "DB_USER", "DB_PASS", "GOOGLE_CLOUD_PROJECT"]

for key in variables_criticas:
    valor = os.getenv(key)
    if valor:
        env_vars[key] = valor

# PASO CLAVE: Guardamos el diccionario dentro de la instancia para que cloudpickle
# lo serialice y lo transporte automáticamente hacia el contenedor de GCP.
agente_instancia.env_vars = env_vars

print("Empaquetando y subiendo el agente a Vertex AI Agent Engine...")
print("Nota: Se aplicará el archivo .gcloudignore automáticamente.")

# LLAMADA OFICIAL: Se remueve 'env_vars' para cumplir estrictamente con la firma del método
remote_agent = reasoning_engines.ReasoningEngine.create(
    reasoning_engine=agente_instancia,
    requirements="agents/moderator/requirements.txt",
    extra_packages=["./agents"],
    display_name="hybrid_shield_moderator_agent",
)

print("\n========================================================")
print("¡Despliegue Exitoso! El agente ya está operativo en GCP.")
print(f"Resource Name: {remote_agent.resource_name}")
print(f"Reasoning Engine ID: {remote_agent.name}")
print("========================================================")