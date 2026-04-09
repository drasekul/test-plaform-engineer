# src/domain/entities.py
# Entidad central del dominio. Representa una venta mensual por producto y región.
# Se usa dataclass con frozen=True para garantizar inmutabilidad real y comparación por valor.
# IMPORTANTE: este módulo NO tiene imports de GCP ni de ningún SDK externo.
# La independencia de dependencias externas es lo que hace testeable al dominio.
from dataclasses import dataclass
from datetime import date as DateType


@dataclass(frozen=True)
class Sale:
    """
    Representa una venta mensual de un producto en una región.
    Todos los campos son el resultado de transformar y limpiar los datos del CSV original.
    frozen=True garantiza inmutabilidad real: ninguna capa puede modificar la entidad
    después de su creación, previniendo corrupción de datos silenciosa.
    """
    sale_id: str        # Identificador único UUID v4 generado en ProcessSaleUseCase
    product: str        # Nombre del producto normalizado (sin espacios extra)
    region: str         # Región con encoding corregido (ej. 'Región 1' en lugar de 'RegiÃ³n 1')
    month: str          # Período original en texto ('Enero 2022')
    monthly_sales: int  # Ventas del mes, validadas como entero positivo
    date: DateType      # Primer día del mes para uso como DATE en BigQuery
    year: int           # Año extraído de date para facilitar queries y particionado en BQ
