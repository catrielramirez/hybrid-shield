# Configuración de Secret Manager para Cloud Run

Este documento explica cómo utilizar el script `setup_secrets.sh` para migrar la gestión de variables de entorno sensibles (como contraseñas y usuarios de bases de datos) desde texto plano en tu código o configuración de Cloud Run, hacia **Google Cloud Secret Manager**.

## 🛡️ ¿Qué hace el script?

El script `setup_secrets.sh` automatiza las mejores prácticas de DevOps para la gestión de secretos. Ejecuta de forma idempotente los siguientes pasos:

1. **Lectura Segura:** Lee las variables `DB_USER`, `DB_PASS`, `GOOGLE_CLOUD_PROJECT` y `SERVICE_NAME` desde tu archivo `.env` local.
2. **Creación en GCP:** Crea los contenedores lógicos de los secretos (`DB_USER` y `DB_PASS`) en Google Cloud Secret Manager si aún no existen.
3. **Versionado de Secretos:** Inyecta los valores leídos del `.env` como la última versión (`latest`) de dichos secretos.
4. **IAM Permisos:** Otorga el rol de acceso necesario (`roles/secretmanager.secretAccessor`) a la Service Account de Cloud Run (`[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`), garantizando el principio de mínimo privilegio.
5. **Configuración de Cloud Run:** Actualiza tu servicio en Cloud Run (`gcloud run services update`) pasándole la bandera `--set-secrets` para que inyecte los valores expuestos de Secret Manager como variables de entorno seguras en el contenedor.

## 📋 Requisitos Previos

1. Tener el **Google Cloud SDK** (`gcloud`) instalado y configurado en tu terminal.
2. Estar autenticado con una cuenta que tenga permisos de administrador en GCP (`roles/owner` o roles que permitan manejar secretos, IAM y Cloud Run).
   ```bash
   gcloud auth login
   ```
3. Tu archivo `.env` debe existir en la misma carpeta (`backend/`) y contener al menos:
   ```env
   GOOGLE_CLOUD_PROJECT=tu-id-del-proyecto
   SERVICE_NAME=hybrid-shield-backend
   REGION=us-central1
   DB_USER=postgres_user
   DB_PASS=tu_super_password
   ```

## 🚀 Ejecución por Primera Vez

Sigue estos pasos la primera vez que configures el entorno de producción:

1. Asigna permisos de ejecución al script:
   ```bash
   chmod +x setup_secrets.sh
   ```

2. Ejecuta el script:
   ```bash
   ./setup_secrets.sh
   ```

Observarás los logs indicando la creación, asignación de permisos y el despliegue final sobre tu servicio en Cloud Run. A partir de este momento, **las variables dejarán de estar en texto plano en la configuración de Cloud Run**.

## 🔄 Cómo Manejar Actualizaciones de Contraseñas (Rotación)

El script es completamente seguro de ejecutar múltiples veces gracias a su naturaleza **idempotente**.

Si necesitas cambiar la contraseña de tu base de datos (por ejemplo, por rotación de claves):

1. Cambia tu clave de la base de datos Postgres.
2. Actualiza tu archivo local `.env` poniendo la nueva contraseña en `DB_PASS`.
3. Vuelve a ejecutar `./setup_secrets.sh`.

El script detectará que el secreto ya existe, inyectará una **nueva versión**, y le indicará a Cloud Run que empiece a utilizar la nueva versión `latest` reiniciando tus contenedores de forma transparente.
