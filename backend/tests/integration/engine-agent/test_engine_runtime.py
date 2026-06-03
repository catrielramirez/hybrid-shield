import os
import json
import google.auth
from google.auth.transport.requests import Request
import vertexai

PROJECT_ID = "ecommerce-police-portfolio"
LOCATION = "us-central1"
BUCKET = "ecommerce-police-portfolio-buckets"
AGENT_NAME = "SemanticShield_LangGraph_AgentRuntime_2026"

def main():
    print("Iniciando validación del agente en Vertex AI Reasoning Engine...")
    print(f"Proyecto: {PROJECT_ID} | Ubicación: {LOCATION}")

    # 1. Autenticación usando application-default login
    try:
        credentials, project = google.auth.default()
        if not credentials.valid:
            credentials.refresh(Request())
        print("Credenciales de Google Cloud cargadas exitosamente.")
    except Exception as e:
        print(f"Error al cargar credenciales: {e}")
        return

    # 2. Inicializar Cliente de Vertex AI
    # pyrefly: ignore [not-callable]
    v_client = vertexai.Client(
        project=PROJECT_ID,
        location=LOCATION,
        credentials=credentials
    )

    # 3. Buscar el Agent Engine por display_name
    print(f"\nBuscando agente con nombre: {AGENT_NAME}...")
    try:
        engines = v_client.agent_engines.list()
        target_engine_name = None
        for engine in engines:
            # Note: the list returns objects that might need to be checked for display_name
            # In some SDK versions, we might need to get the full resource first.
            if engine.display_name == AGENT_NAME:
                target_engine_name = engine.resource_name
                break
                
        if not target_engine_name:
            print(f"Error: No se encontró el agente '{AGENT_NAME}'.")
            print("Agentes disponibles:")
            for engine in engines:
                print(f" - {engine.display_name} ({engine.resource_name})")
            return

        print(f" Agente encontrado: {target_engine_name}")
        
        # Instanciar explícitamente
        engine = v_client.agent_engines.get(target_engine_name)
        print(" Motor de razonamiento instanciado correctamente.")
    except Exception as e:
        print(f"Error al buscar agentes: {e}")
        return

    # 4. Preparar el input para el agente LangGraph
    job_id = "a7f38d94-a73a-4e6f-b582-74d277fe3f7c"
    gcs_image_uri = "gs://ecommerce-police-portfolio-buckets/imagenes_ingesta/2026/04/27/a7f38d94-a73a-4e6f-b582-74d277fe3f7c_20250527_1347_Fashionable Dog in Raincoat_remix_01jw9a6pj0f3wtjq9egxypdqw8.png"
    
    # Adaptamos el JSON de entrada para incluir los campos solicitados y
    # respetar el schema de AgentState (input_data, gcs_uri, thread_id)
    input_state = {
        "input_data": {
            "title": "Fashionable Dog in Raincoat",
            "description": "Un perro elegante con piloto para la lluvia, estilo remix.",
            "price": 25.0,
            "gcs_image_uri": gcs_image_uri
        },
        "gcs_uri": gcs_image_uri,
        "thread_id": job_id,
        "title": "Fashionable Dog in Raincoat",
        "description": "Un perro elegante con piloto para la lluvia, estilo remix.",
        "price": 25.0,
        "gcs_image_uri": gcs_image_uri
    }
    
    print("\nEnviando consulta al agente LangGraph...")
    print(f"Job ID: {job_id}")
    print(f"Imagen: {gcs_image_uri}")
    print(f"Input Data: {json.dumps(input_state['input_data'], indent=2)}")
    
    # 5. Consultar al Agent Engine
    try:
        # Es CRITICO pasar el thread_id en el config para que el checkpointer de LangGraph funcione
        config = {"configurable": {"thread_id": job_id}}
        response = engine.query(input=input_state, config=config)
        
        print("\n" + "="*50)
        print("=== RESPUESTA COMPLETA DEL AGENTE ===")
        print("="*50)
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        # Extraer decision (final_action/decision) y reasoning para mostrarlos destacadamente
        if isinstance(response, dict):
            decision = response.get("final_action", response.get("decision", "No especificada"))
            reasoning = response.get("reasoning", "No especificado")
            
            print("\n" + "="*50)
            print("=== ANÁLISIS DE MODERACIÓN ===")
            print("="*50)
            print(f"DECISIÓN: {decision}")
            print(f"\nRAZONAMIENTO:\n{reasoning}")
            print("="*50)
        else:
            print("\nLa respuesta retornada no tiene el formato esperado (diccionario).")
            
    except Exception as e:
        error_msg = str(e).lower()
        if "permission" in error_msg or "403" in error_msg or "iam" in error_msg:
            print(f"\n[ERROR IAM] Problema de permisos de IAM detectado:")
            print(f"Asegúrate de que tu cuenta tenga los roles necesarios (ej. Vertex AI User, Storage Object Viewer).")
            print(f"Detalle del error: {e}")
        else:
            print(f"\nError al ejecutar la consulta contra el agente: {e}")

if __name__ == "__main__":
    main()
