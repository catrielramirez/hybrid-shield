$PROJECT_ID = "ecommerce-police-portfolio"
$SERVICE_ACCOUNT = "679252770153-compute@developer.gserviceaccount.com"

Write-Host "Asignando permisos para el agente de moderación en el proyecto: $PROJECT_ID..."
Write-Host "Cuenta de Servicio: $SERVICE_ACCOUNT"
Write-Host "--------------------------------------------------------"

# 1. Permite invocar modelos de Gemini (google-genai)
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/aiplatform.user"

# 2. Permite leer imágenes desde los buckets (Feature Extractor)
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/storage.objectViewer"

# 3. Permite hacer RAG Vectorial (Vertex AI Search / Discovery Engine)
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/discoveryengine.viewer"

# 4. Permite usar Firestore / Datastore para el tracking del status
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/datastore.user"

Write-Host "--------------------------------------------------------"
Write-Host "¡Permisos asignados exitosamente a $SERVICE_ACCOUNT!"