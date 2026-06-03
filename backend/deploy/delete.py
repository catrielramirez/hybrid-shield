import os
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv

# Cargar entorno
ruta_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
load_dotenv(dotenv_path=ruta_env)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecommerce-police-portfolio")
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

print("Buscando agentes desplegados en Vertex AI...")
# Listamos todos los reasoning engines activos
lista_agentes = reasoning_engines.ReasoningEngine.list()

if not lista_agentes:
    print("No se encontraron agentes para eliminar.")
    exit()

print(f"Se encontraron {len(lista_agentes)} agentes.")
print("--------------------------------------------------------")

# Opcional: Si querés salvar el ÚLTIMO que desplegaste, 
# el método .list() suele devolverlos ordenados por fecha (el más reciente primero).
# Si querés borrar ABSOLUTAMENTE TODO, eliminá las próximas dos líneas:
print(f"Conservando el agente más reciente: {lista_agentes[0].name}")
lista_agentes = lista_agentes[1:] 

for agente in lista_agentes:
    print(f"Eliminando agente viejo: {agente.name} ({agente.display_name})...")
    try:
        agente.delete()
        print(f"¡Agente {agente.name} eliminado con éxito!")
    except Exception as e:
        print(f"No se pudo eliminar {agente.name}: {e}")

print("--------------------------------------------------------")
print("Limpieza finalizada.")