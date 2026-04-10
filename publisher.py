#!/usr/bin/env python3
# publisher.py
# Simulador de la célula de BI: lee ventas.csv y publica cada fila como
# mensaje independiente al tópico de Pub/Sub.
#
# Uso:
#   export PUBSUB_TOPIC=projects/MY_PROJECT/topics/ventas-topic
#   export GOOGLE_APPLICATION_CREDENTIALS=path/to/sa-key.json
#   python publisher.py --file ventas.csv --batch-size 100
import argparse
import logging
import os

from src.application.use_cases import ProcessSaleUseCase, PublishSaleUseCase
from src.domain.entities import Sale
from src.domain.ports import DataRepository
from src.infrastructure.csv_reader import read_csv
from src.infrastructure.pubsub_adapter import PubSubPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


class _NullRepository(DataRepository):
    """
    Repositorio nulo para usar ProcessSaleUseCase en modo publisher.
    En este contexto solo necesitamos transformar los datos, no persistirlos;
    la persistencia ocurre en Cloud Run después de que Pub/Sub entrega el mensaje.
    """

    def save(self, sale: Sale) -> None:
        pass  # No-op intencional: el publisher no escribe directamente en BigQuery


def main(file_path: str, batch_size: int) -> None:
    # Leer el topic path desde variable de entorno para evitar hardcodear IDs
    # de proyecto
    topic_path = os.environ["PUBSUB_TOPIC"]

    publisher = PubSubPublisher(topic_path=topic_path)
    publish_use_case = PublishSaleUseCase(publisher=publisher)
    process_use_case = ProcessSaleUseCase(repository=_NullRepository())

    rows = read_csv(file_path)
    total = len(rows)
    logger.info(f"Iniciando publicación de {total} registros desde '{file_path}'")

    for i, row in enumerate(rows, start=1):
        # Mapear columnas del CSV a los campos esperados por el caso de uso
        raw_data = {
            "product": row["producto"],
            "region": row["region"],
            "month": row["mes"],
            "monthly_sales": row["ventas_mensuales"],
        }

        try:
            sale = process_use_case.execute(raw_data)
            message_id = publish_use_case.execute(sale)
            logger.info(
                f"[{i}/{total}] Publicado: sale_id={sale.sale_id} "
                f"product={sale.product} message_id={message_id}"
            )
        except ValueError as e:
            # Registrar el error y continuar con la siguiente fila
            logger.warning(
                f"[{i}/{total}] Fila inválida omitida: {e} — datos: {raw_data}"
            )

        # Log de progreso por lotes para monitoreo en datasets grandes
        if batch_size and i % batch_size == 0:
            logger.info(f"Progreso: {i}/{total} mensajes publicados ({i/total:.0%})")

    logger.info(f"Publicación completada: {total} registros procesados")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simulador de publicación de ventas a Google Cloud Pub/Sub"
    )
    parser.add_argument(
        "--file",
        default="ventas.csv",
        help="Ruta al archivo CSV de ventas (default: ventas.csv)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Intervalo de logging de progreso (default: 100 registros)",
    )
    args = parser.parse_args()
    main(args.file, args.batch_size)
