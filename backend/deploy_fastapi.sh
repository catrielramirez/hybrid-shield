#!/bin/bash
set -e

# Asegurar que estamos en el directorio del backend
cd "$(dirname "$0")"

# Archivo de entorno esperado
ENV_FILE="./.env"

# 1. Cargar variables desde el archivo .env de forma segura
if [ -f "$ENV_FILE" ]; then
    echo "Cargando variables desde $ENV_FILE..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Error: No se encontró el archivo $ENV_FILE."
    exit 1
fi

# Variables necesarias
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"ecommerce-police-portfolio"}
SERVICE_NAME=${SERVICE_NAME:-"hybrid-shield-backend"}
REGION=${REGION:-"us-central1"}
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-"http://localhost:3000,http://127.0.0.1:3000"}

# Asegurar que estas variables tengan valor (puedes definirlas aquí o en tu .env)
# Reemplaza con tus valores reales:
SERVICE_ACCOUNT_EMAIL=${SERVICE_ACCOUNT_EMAIL:-"tu-email@tu-proyecto.iam.gserviceaccount.com"}
DB_INSTANCE_NAME=${DB_INSTANCE_NAME:-"tu-proyecto:us-central1:tu-instancia"}

echo "Desplegando FastAPI en Cloud Run (Servicio: $SERVICE_NAME)..."

# Desplegar desde el código fuente inyectando las variables de entorno
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --max-instances=3 \
    --min-instances=0 \
    --set-env-vars="ALLOWED_ORIGINS=$ALLOWED_ORIGINS,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,SERVICE_ACCOUNT_EMAIL=$SERVICE_ACCOUNT_EMAIL,DB_INSTANCE_NAME=$DB_INSTANCE_NAME"

echo "========================================================"
echo "Despliegue de FastAPI completado con éxito."
echo "========================================================"