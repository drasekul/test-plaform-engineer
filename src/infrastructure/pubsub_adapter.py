# src/infrastructure/pubsub_adapter.py
# Adaptador de Pub/Sub que implementa el puerto MessagePublisher.
# Este módulo es el único lugar que conoce el SDK de google-cloud-pubsub.
import json

from google.cloud import pubsub_v1

from src.domain.entities import Sale
from src.domain.ports import MessagePublisher


class PubSubPublisher(MessagePublisher):
    """
    Implementación del puerto MessagePublisher usando Google Cloud Pub/Sub.

    El topic_path debe tener el formato: projects/{project_id}/topics/{topic_name}
    Este valor se configura via variable de entorno PUBSUB_TOPIC en el publisher.py.
    """

    def __init__(self, topic_path: str) -> None:
        self._client = pubsub_v1.PublisherClient()
        self._topic_path = topic_path

    def publish(self, sale: Sale) -> str:
        """
        Serializa la entidad Sale a JSON y la publica en Pub/Sub.

        Se usa future.result() para bloquear hasta confirmar que Pub/Sub
        aceptó el mensaje, garantizando entrega al menos una vez (at-least-once).
        Retorna el message_id asignado por Pub/Sub para trazabilidad en logs.
        """
        payload = {
            "sale_id": sale.sale_id,
            "product": sale.product,
            "region": sale.region,
            "month": sale.month,
            "monthly_sales": sale.monthly_sales,
            "date": sale.date.isoformat(),
            "year": sale.year,
        }
        # Los mensajes Pub/Sub deben ser bytes
        data = json.dumps(payload).encode("utf-8")
        future = self._client.publish(self._topic_path, data=data)
        # Bloquea hasta confirmar la publicación; lanza excepción si falla
        return future.result()
