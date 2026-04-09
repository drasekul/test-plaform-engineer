# src/infrastructure/main.py
# Punto de entrada del servicio Cloud Run.
# Expone un endpoint HTTP POST / que recibe mensajes push de Pub/Sub,
# los decodifica y delega el procesamiento a ProcessSaleUseCase.
import base64
import json
import logging
import os

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from src.application.use_cases import ProcessSaleUseCase
from src.domain.ports import DataRepository
from src.infrastructure.bigquery_adapter import BigQueryRepository

# Configurar logging estructurado para que Cloud Logging lo capture correctamente
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FIF Sales Pipeline Subscriber",
    description="Suscriptor de Pub/Sub que procesa ventas y las almacena en BigQuery",
    version="1.0.0",
)


class PubSubMessage(BaseModel):
    """Estructura del mensaje individual de Pub/Sub."""

    data: str  # Payload codificado en base64
    messageId: str
    publishTime: str


class PubSubPushRequest(BaseModel):
    """
    Wrapper del request que Pub/Sub envía al endpoint de push subscription.
    Pub/Sub siempre envía esta estructura exacta al hacer HTTP POST.
    """

    message: PubSubMessage
    subscription: str


def get_repository() -> DataRepository:
    """
    Factoría del repositorio de BigQuery.
    Se usa inyección de dependencias de FastAPI para poder sobreescribir
    esta función con un mock en los tests de aceptación sin modificar el código
    de producción. Las variables de entorno se leen aquí para detectar
    configuración faltante al arrancar.
    """
    return BigQueryRepository(
        project_id=os.environ["GCP_PROJECT_ID"],
        dataset_id=os.environ["BQ_DATASET"],
        table_id=os.environ["BQ_TABLE"],
    )


@app.get("/health")
async def health_check():
    """
    Health check para Cloud Run.
    Cloud Run verifica este endpoint periódicamente; si retorna != 200,
    reinicia el contenedor.
    """
    return {"status": "ok"}


@app.post("/", status_code=status.HTTP_200_OK)
async def receive_pubsub_message(
    body: PubSubPushRequest,
    repository: DataRepository = Depends(get_repository),
):
    """
    Endpoint principal del suscriptor de Pub/Sub (push subscription).

    Pub/Sub espera HTTP 200-299 como confirmación (ACK).
    - Si retorna 4xx: Pub/Sub NO reintenta (error del cliente/datos inválidos).
    - Si retorna 5xx o timeout: Pub/Sub reintenta automáticamente (error transitorio).
    Esta distinción es crítica para evitar loops infinitos con datos corruptos.
    """
    try:
        # Decodificar el payload base64 del mensaje Pub/Sub
        decoded_bytes = base64.b64decode(body.message.data)
        raw_data = json.loads(decoded_bytes.decode("utf-8"))

    except json.JSONDecodeError as e:
        # JSON malformado: datos irrecuperables, no reintentar
        logger.error(
            f"JSON inválido en mensaje Pub/Sub message_id={body.message.messageId}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload del mensaje Pub/Sub no es JSON válido",
        )

    try:
        use_case = ProcessSaleUseCase(repository=repository)
        sale = use_case.execute(raw_data)

        logger.info(
            f"Venta procesada exitosamente: sale_id={sale.sale_id} "
            f"product={sale.product}"
        )
        return {"status": "processed", "sale_id": sale.sale_id}

    except ValueError as e:
        # Datos semánticamente inválidos (ej. monthly_sales negativo): no reintentar
        logger.error(
            f"Datos inválidos en mensaje message_id={body.message.messageId}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        # Error inesperado: retornar 500 para que Pub/Sub reintente
        logger.error(
            f"Error inesperado procesando message_id={body.message.messageId}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )
