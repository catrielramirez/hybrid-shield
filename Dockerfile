FROM python:3.12-slim

WORKDIR /app

# Copiamos los requerimientos desde la raíz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos TODO el monorepo para mantener la estructura de carpetas
COPY . .

# Exponemos el puerto de Cloud Run
EXPOSE 8080

# El comando debe apuntar a la carpeta backend
# Usamos uvicorn backend.main:app porque Python verá el paquete 'backend'
ENV PYTHONPATH=/app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]