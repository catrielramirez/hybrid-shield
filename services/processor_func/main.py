import os
import json
import functions_framework
from google.cloud import storage
from google.cloud import aiplatform

class TrustSafetyEventProcessor:
    def __init__(self):
        self._storage_client = None
        self._aiplatform_initialized = False

    @property
    def storage_client(self):
        if not self._storage_client:
            self._storage_client = storage.Client()
        return self._storage_client

    def _init_aiplatform(self):
        if not self._aiplatform_initialized:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
            if project_id:
                aiplatform.init(project=project_id, location=region)
                self._aiplatform_initialized = True

    def _parse_gcs_uri(self, gcs_uri: str) -> tuple[str, str]:
        uri_parts = gcs_uri.replace("gs://", "").split("/", 1)
        if len(uri_parts) != 2:
            raise ValueError(f"Formato de URI GCS inválido: {gcs_uri}")
        return uri_parts[0], uri_parts[1]

    def execute(self, bucket_name: str, file_name: str) -> None:
        print(f"Evaluando archivo entrante: {file_name} del bucket: {bucket_name}")

        if not file_name.endswith('.json'):
            print(f"Archivo omitido. No cumple con la extensión requerida (.json): {file_name}")
            return

        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        
        try:
            json_data = json.loads(blob.download_as_string())
        except Exception as e:
            print(f"Error crítico al leer o parsear el archivo JSON {file_name}: {e}")
            return

        gcs_image_uri = json_data.get("gcs_image_uri")
        
        path_parts = file_name.split('/')
        fallback_id = path_parts[-2] if len(path_parts) >= 2 else path_parts[-1].split('.')[0]
        job_id = json_data.get("job_id", fallback_id)
        
        if not gcs_image_uri:
            print(f"No se encontró gcs_image_uri dentro de {file_name}")
            return

        try:
            img_bucket_name, img_blob_name = self._parse_gcs_uri(gcs_image_uri)
            img_bucket = self.storage_client.bucket(img_bucket_name)
            img_blob = img_bucket.blob(img_blob_name)
            
            if not img_blob.exists():
                print(f"El objeto referenciado no existe: {gcs_image_uri}")
                return

            print("Optimizando imagen...")
            image_bytes = img_blob.download_as_bytes()

            # IMPORTACIÓN PEREZOSA DEL MÓDULO LOCAL
            try:
                from shared.image_utils import optimize_image
            except ImportError:
                import sys
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
                from backend.shared.image_utils import optimize_image

            optimized_bytes = optimize_image(image_bytes)

            base_dir = os.path.dirname(file_name)
            optimized_blob_name = f"{base_dir}/optimized_image.webp" if base_dir else f"items/{job_id}/optimized_image.webp"
            
            optimized_blob = bucket.blob(optimized_blob_name)
            optimized_gcs_uri = f"gs://{bucket_name}/{optimized_blob_name}"
            
            optimized_blob.upload_from_string(optimized_bytes, content_type="image/webp")

        except Exception as e:
            print(f"Falló pipeline de imagen: {e}")
            return

        reasoning_engine_id = os.getenv("REASONING_ENGINE_ID")
        if not reasoning_engine_id:
            print("REASONING_ENGINE_ID no configurado")
            return

        self._init_aiplatform()
        print(f"Invocando Reasoning Engine ID: {reasoning_engine_id}...")
        
        try:
            engine = aiplatform.ReasoningEngine(reasoning_engine_id)
            
            agent_input = {
                "input_data": {
                    "title": json_data.get("title", ""),
                    "description": json_data.get("description", ""),
                    "price": json_data.get("price", 0),
                    "gcs_image_uri": optimized_gcs_uri
                },
                "gcs_uri": optimized_gcs_uri,
                "thread_id": job_id
            }
            
            config = {"configurable": {"thread_id": job_id}}
            
            response = engine.query(input=agent_input, config=config)
            print(f"Respuesta exitosa: {response}")
        except Exception as e:
            print(f"Error Reasoning Engine: {e}")

processor_service = TrustSafetyEventProcessor()

@functions_framework.cloud_event
def process_image_event(cloud_event):
    data = cloud_event.data
    processor_service.execute(bucket_name=data["bucket"], file_name=data["name"])