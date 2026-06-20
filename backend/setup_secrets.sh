#!/bin/bash
set -x

# Salir inmediatamente si ocurre un error
set -e

# Asegurar que estamos en el directorio del script
cd "$(dirname "$0")"

# Archivo de entorno esperado (apuntando a la raiz)
ENV_FILE="../.env"

# 1. Cargar variables desde el archivo .env de forma segura
if [ -f "$ENV_FILE" ]; then
    echo "Cargando variables desde $ENV_FILE..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Error: No se encontró el archivo $ENV_FILE. Por favor, asegúrate de que el archivo .env existe en la carpeta raíz."
    exit 1
fi

# Variables necesarias
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-""}
SERVICE_NAME=${SERVICE_NAME:-"hybrid-shield-backend"}
REGION=${REGION:-"us-central1"}

# Validaciones de variables obligatorias
if [ -z "$PROJECT_ID" ]; then
    echo "Error: GOOGLE_CLOUD_PROJECT no está definido en el archivo .env."
    exit 1
fi

if [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
    echo "Error: DB_USER o DB_PASS no están definidos en el archivo .env."
    exit 1
fi

echo "Iniciando configuración de seguridad para el proyecto: $PROJECT_ID"

# Obtener el Project Number
echo "Obteniendo Project Number..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "La Service Account de Cloud Run es: $SERVICE_ACCOUNT"

# 2 & 3. Función para crear el secreto, añadir versión y otorgar permisos
setup_secret() {
    local secret_name=$1
    local secret_value=$2

    # Verificar si el secreto ya existe
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "[OK] El secreto $secret_name ya existe."
    else
        echo "[INFO] Creando el secreto $secret_name..."
        gcloud secrets create "$secret_name" \
            --replication-policy="automatic" \
            --project="$PROJECT_ID"
    fi

    # Añadir nueva versión del secreto con el valor del .env
    echo "[INFO] Añadiendo valor actual al secreto $secret_name..."
    echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
        --data-file=- \
        --project="$PROJECT_ID"

    # 4. Otorgar permisos a la Service Account
    echo "[INFO] Otorgando permisos de acceso a la Service Account para $secret_name..."
    gcloud secrets add-iam-policy-binding "$secret_name" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project="$PROJECT_ID" >/dev/null 2>&1
}

# Ejecutar la función para DB_USER y DB_PASS
setup_secret "DB_USER" "$DB_USER"
setup_secret "DB_PASS" "$DB_PASS"

# 5. Desplegar / Actualizar Cloud Run
echo "Actualizando el servicio Cloud Run '$SERVICE_NAME' para montar los secretos..."
gcloud run services update "$SERVICE_NAME" \
    --set-secrets="DB_PASS=DB_PASS:latest,DB_USER=DB_USER:latest" \
    --region="$REGION" \
    --project="$PROJECT_ID"

echo "========================================================"
echo "Configuración de seguridad completada con éxito."
echo "Cloud Run ahora lee DB_USER y DB_PASS desde Secret Manager."
echo "========================================================"