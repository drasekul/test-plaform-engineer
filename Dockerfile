# Dockerfile
# Imagen optimizada para el servicio Cloud Run (suscriptor de Pub/Sub).
# Se usa python:3.11-slim para minimizar el tamaño de la imagen (~150MB vs ~900MB de la full).

FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar solo requirements primero para aprovechar el cache de capas de Docker.
# Si el código cambia pero las dependencias no, Docker reutiliza esta capa.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente después de instalar dependencias
COPY src/ ./src/

# Puerto configurado via variable de entorno para compatibilidad con Cloud Run.
# Cloud Run inyecta PORT automáticamente; este valor es el fallback.
ENV PORT=8080

# Uvicorn como servidor ASGI para FastAPI.
# --host 0.0.0.0 es necesario para que Cloud Run pueda enrutar tráfico al contenedor.
# --workers 1 porque Cloud Run escala horizontalmente a nivel de instancias, no de workers.
CMD ["uvicorn", "src.infrastructure.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
