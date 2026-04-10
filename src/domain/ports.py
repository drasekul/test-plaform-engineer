# src/domain/ports.py
# Puertos (interfaces abstractas) del dominio. Definen los contratos que deben cumplir
# los adaptadores de infraestructura.
# El uso de ABCs garantiza que la capa de aplicación dependa de abstracciones,
# no de implementaciones concretas (principio D de SOLID).
from abc import ABC, abstractmethod

from src.domain.entities import Sale


class MessagePublisher(ABC):
    """
    Puerto de salida para publicación de mensajes.
    Implementado por PubSubPublisher en la capa de infraestructura.
    """

    @abstractmethod
    def publish(self, sale: Sale) -> str:
        """
        Publica una venta en el bus de mensajes.
        Retorna el message_id asignado por el broker para trazabilidad en logs.
        """
        ...


class DataRepository(ABC):
    """
    Puerto de salida para persistencia de datos.
    Implementado por BigQueryRepository en la capa de infraestructura.
    """

    @abstractmethod
    def save(self, sale: Sale) -> None:
        """Persiste una venta en el almacén de datos analíticos."""
        ...
