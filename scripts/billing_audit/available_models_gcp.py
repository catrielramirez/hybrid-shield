import sys
from google import genai

PROJECT_ID = "ecommerce-police-portfolio"

try:
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="us-central1"
    )
    
    print("=" * 60)
    print("MODELOS DISPONIBLES")
    print("=" * 60)
    
    # Listar los modelos de forma segura inspeccionando sus atributos correctos
    models = client.models.list()
    for model in models:
        # Extraer el identificador limpio del modelo
        model_id = model.name.split("/")[-1]
        print(f" - ID de Modelo: {model_id} (Ruta: {model.name})")

except Exception as e:
    print(f"[ERROR INESPERADO] {e}", file=sys.stderr)