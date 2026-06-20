import os
import sys
from google import genai
from google.genai.errors import APIError
from loadenv import loadenv


loadenv()

# CONFIGURACIÓN: Reemplaza con tus datos reales de GCP
PROJECT_ID = os.getenv("PROJECT_ID")
# El nuevo SDK unificado permite interrogar el endpoint 'global' o regiones específicas
REGIONS = ["us-central1", "global"]

def limpiar_caches_unificadas():
    print("=" * 60)
    print("INICIANDO LIMPIEZA CON SDK UNIFICADO: google-genai")
    print("=" * 60)
    
    caches_eliminadas = 0
    
    for region in REGIONS:
        print(f"\n[Región: {region}] Inicializando cliente GenAI...")
        try:
            # Inicialización del cliente oficial moderno con bandera Vertex activa
            client = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=region
            )
            
            # Listar las cachés utilizando el namespace simplificado 'caches'
            caches_activas = list(client.caches.list())
            
            if not caches_activas:
                print(f"[Región: {region}] No se encontraron instancias de Context Cache activas.")
                continue
                
            print(f"[Región: {region}] Se encontraron {len(caches_activas)} cachés persistentes:")
            
            for cache in caches_activas:
                print(f"  -> Solicitando eliminación de: {cache.name}")
                
                # Ejecución del borrado directo usando el método unificado
                client.caches.delete(name=cache.name)
                
                print(f"  [OK] CONFIRMADO: Removido con éxito.")
                caches_eliminadas += 1
                
        except APIError as e:
            print(f"  [ERROR DE API] Error en la región {region}: {e.message}", file=sys.stderr)
        except Exception as e:
            print(f"  [ERROR INESPERADO] {e}", file=sys.stderr)

    print("\n" + "=" * 60)
    print(f"PROCESO FINALIZADO. Total de cachés removidas desde genai: {caches_eliminadas}")
    print("=" * 60)

if __name__ == "__main__":
    # Se eliminó la validación estricta que bloqueaba la ejecución
    limpiar_caches_unificadas()