#!/bin/bash

# Detener el script si ocurre un error
set -e

# Asegurar que el script opere desde su propio directorio
cd "$(dirname "$0")"

# Configuration
PROJECT_ID="ecommerce-police-portfolio"
REGION="us-central1"
BUCKET_NAME="ecommerce-police-media-uploads" 
REASONING_ENGINE_ID="5340066842096435200"
FUNCTION_NAME="processor-func"

echo "Deploying $FUNCTION_NAME..."

# Paso 1: Preparación y copia del código compartido
echo "Limpiando copias previas de shared..."
rm -rf shared

echo "Copying backend/shared directory locally for deployment..."
cp -r ../../backend/shared ./shared

# Paso 2: Despliegue de la Cloud Function
echo "Deploying Cloud Function to GCP..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=process_image_event \
    --memory=1024Mi \
    --cpu=1 \
    --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
    --trigger-event-filters="bucket=$BUCKET_NAME" \
    --max-instances=5 \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_REGION=$REGION,REASONING_ENGINE_ID=$REASONING_ENGINE_ID \
    --project=$PROJECT_ID

# Paso 3: Limpieza local
echo "Cleaning up deployment context..."
rm -rf shared

echo "Deployment complete!"