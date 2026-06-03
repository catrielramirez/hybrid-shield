import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vertexai.preview import reasoning_engines
import vertexai

# Configura tu proyecto y ubicación si es necesario
PROJECT_ID = "ecommerce-police-portfolio" 
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION)

# ID del motor de razonamiento (Reasoning Engine) que acabamos de desplegar
REASONING_ENGINE_ID = "4106362019173629952"

print(f"Cargando Reasoning Engine: {REASONING_ENGINE_ID}")
remote_agent = reasoning_engines.ReasoningEngine(f"projects/679252770153/locations/us-central1/reasoningEngines/{REASONING_ENGINE_ID}")

print("Ejecutando agente remoto...")
response = remote_agent.query(
    input_data={
        "messages": [("user", "El usuario intentó publicar un producto que parece ser falsificado de la marca Nike.")],
    }
)

print("\n--- Respuesta del Agente ---")
print(response)
