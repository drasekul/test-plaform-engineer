# src/application/use_cases.py
# Casos de uso: orquestan el flujo de la aplicación usando solo los puertos del dominio.
# Esta capa NO conoce si el destino es BigQuery, una base SQL, o un archivo.
# NO importa nada de google.cloud.* — eso es responsabilidad de la infraestructura.
import uuid
from datetime import date as DateType

from src.domain.entities import Sale
from src.domain.ports import DataRepository, MessagePublisher

# Mapeo de meses en español a su número.
# Se define aquí (no via locale) para evitar dependencia del sistema operativo del contenedor.
_MONTH_MAP: dict[str, int] = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}


def _fix_encoding(text: str) -> str:
    """
    Corrige el artefacto de encoding del archivo ventas.csv.
    El CSV contiene caracteres como 'RegiÃ³n' porque bytes UTF-8 de 'Región'
    fueron interpretados como latin-1. Este proceso invierte esa conversión:
    re-codifica en latin-1 y decodifica como UTF-8 para obtener el texto original.
    """
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Si el texto ya está correctamente codificado, se retorna sin cambios
        return text


def _parse_month_to_date(month_str: str) -> DateType:
    """
    Convierte 'Enero 2022' a date(2022, 1, 1).
    Se usa el primer día del mes como convención para representar el período mensual.
    Esto permite usar el campo como DATE en BigQuery para filtros y particionado eficientes.
    """
    parts = month_str.strip().split()
    month_name, year = parts[0], int(parts[1])
    month_num = _MONTH_MAP[month_name]
    return DateType(year, month_num, 1)


class ProcessSaleUseCase:
    """
    Caso de uso principal: recibe datos crudos desde Pub/Sub, los limpia,
    valida y transforma en una entidad Sale, luego la persiste via DataRepository.

    Transformaciones aplicadas:
    1. Fix encoding: 'RegiÃ³n' → 'Región'
    2. Strip: elimina espacios invisibles de todos los strings
    3. Parse fecha: 'Enero 2022' → date(2022, 1, 1)
    4. UUID: genera sale_id único por registro
    5. Validación: rechaza monthly_sales <= 0 con ValueError
    """

    def __init__(self, repository: DataRepository) -> None:
        # Inyección de dependencia del repositorio: permite testear con mocks
        self._repository = repository

    def execute(self, raw_data: dict) -> Sale:
        # 1. Corregir encoding de región (artefacto del CSV original)
        region = _fix_encoding(raw_data["region"].strip())

        # 2. Normalizar strings: eliminar espacios invisibles
        product = raw_data["product"].strip()
        month = raw_data["month"].strip()

        # 3. Validar que monthly_sales sea un entero positivo
        monthly_sales = int(raw_data["monthly_sales"])
        if monthly_sales <= 0:
            raise ValueError(
                f"monthly_sales debe ser un entero positivo, se recibió: {monthly_sales}"
            )

        # 4. Parsear el mes a un objeto date para tipado correcto en BigQuery
        sale_date = _parse_month_to_date(month)

        # 5. Generar identificador único por registro usando UUID v4
        sale_id = str(uuid.uuid4())

        sale = Sale(
            sale_id=sale_id,
            product=product,
            region=region,
            month=month,
            monthly_sales=monthly_sales,
            date=sale_date,
            year=sale_date.year,
        )

        # Persistir via el puerto — no se asume qué sistema de almacenamiento hay detrás
        self._repository.save(sale)
        return sale
