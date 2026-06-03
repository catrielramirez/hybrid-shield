FROM python:3.12-slim

# Instalamos uv para mantener la velocidad
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv

WORKDIR /app

# Copiamos solo el requirements generado
COPY requirements.txt .

# Instalamos las dependencias
RUN /uv pip install --system --no-cache -r requirements.txt

# Copiamos el resto del código
COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]