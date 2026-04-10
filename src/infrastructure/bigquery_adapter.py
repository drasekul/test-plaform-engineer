# src/infrastructure/bigquery_adapter.py
# Adaptador de BigQuery que implementa el puerto DataRepository.
# Este módulo es el único lugar del proyecto que conoce los detalles de BigQuery.
# Cualquier cambio de destino de datos (ej. migrar a Spanner) solo requiere
# cambiar aquí.
from datetime import datetime, timezone

from google.cloud import bigquery

from src.domain.entities import Sale
from src.domain.ports import DataRepository


class BigQueryRepository(DataRepository):
    """
    Implementación del puerto DataRepository usando BigQuery.
    Se instancia una sola vez por proceso para reutilizar la conexión del cliente.
    """

    def __init__(self, project_id: str, dataset_id: str, table_id: str) -> None:
        # El cliente de BigQuery usa las credenciales de la SA del entorno
        # (GOOGLE_APPLICATION_CREDENTIALS o la SA asignada al Cloud Run,
        # que es la forma recomendada en GCP).
        self._client = bigquery.Client(project=project_id)
        # Referencia completa a la tabla en formato project.dataset.table
        self._table_ref = f"{project_id}.{dataset_id}.{table_id}"

    def save(self, sale: Sale) -> None:
        """
        Inserta una fila en la tabla de BigQuery usando streaming insert
        (insert_rows_json). Se agrega ingested_at para trazabilidad de
        cuándo llegó el dato al pipeline.

        Nota: streaming inserts en BigQuery tienen latencia ~1s antes de
        ser visibles en queries. Para reportería en Looker Studio esto es
        aceptable.
        """
        row = {
            "sale_id": sale.sale_id,
            "product": sale.product,
            "region": sale.region,
            "month": sale.month,
            "monthly_sales": sale.monthly_sales,
            # BigQuery acepta 'YYYY-MM-DD' para tipo DATE
            "date": sale.date.isoformat(),
            "year": sale.year,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        errors = self._client.insert_rows_json(self._table_ref, [row])
        if errors:
            # insert_rows_json retorna lista de errores vacía si todo OK
            raise RuntimeError(f"Error al insertar fila en BigQuery: {errors}")
