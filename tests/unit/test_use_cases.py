# tests/unit/test_use_cases.py
# Tests de los casos de uso. Usan mocks para los puertos, garantizando que
# no hay dependencias de GCP. Cada test verifica una transformación específica.
import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.application.use_cases import ProcessSaleUseCase


@pytest.mark.unit
class TestProcessSaleUseCase:

    def setup_method(self):
        # Mock del repositorio: permite verificar llamadas sin conectar a BigQuery
        self.mock_repository = MagicMock()
        self.use_case = ProcessSaleUseCase(repository=self.mock_repository)

    def _raw(self, **overrides) -> dict:
        # Helper para construir raw_data válido con valores por defecto
        base = {
            "product": "Producto A",
            "region": "Región 1",
            "month": "Enero 2022",
            "monthly_sales": "1200",
        }
        base.update(overrides)
        return base

    def test_corrects_region_encoding(self):
        # RegiÃ³n es un artefacto de leer UTF-8 bytes como latin-1.
        # El caso de uso debe corregirlo antes de persistir.
        sale = self.use_case.execute(self._raw(region="RegiÃ³n 1"))
        assert sale.region == "Región 1"

    def test_parses_month_string_to_date(self):
        # BigQuery requiere tipo DATE para filtros temporales eficientes.
        # 'Enero 2022' se mapea al primer día del mes por convención.
        sale = self.use_case.execute(self._raw(month="Enero 2022"))
        assert sale.date == date(2022, 1, 1)
        assert sale.year == 2022

    def test_parses_december(self):
        # Verificar que el mapeo de meses funciona para todo el calendario
        sale = self.use_case.execute(self._raw(month="Diciembre 2023"))
        assert sale.date == date(2023, 12, 1)

    def test_strips_whitespace_from_strings(self):
        # Espacios invisibles pueden causar duplicados o fallos en queries BQ.
        # Se eliminan preventivamente en todos los campos string.
        sale = self.use_case.execute(
            self._raw(product="  Producto A  ", region="  Región 1  ")
        )
        assert sale.product == "Producto A"
        assert sale.region == "Región 1"

    def test_generates_valid_uuid_v4(self):
        # El sale_id debe ser un UUID v4 válido para garantizar unicidad global.
        sale = self.use_case.execute(self._raw())
        parsed = uuid.UUID(sale.sale_id, version=4)
        assert str(parsed) == sale.sale_id

    def test_raises_value_error_for_zero_sales(self):
        # Ventas en cero son datos inválidos; no deben llegar a BigQuery.
        # ValueError hace que FastAPI retorne 422, evitando reintentos de Pub/Sub.
        with pytest.raises(ValueError, match="monthly_sales"):
            self.use_case.execute(self._raw(monthly_sales="0"))

    def test_raises_value_error_for_negative_sales(self):
        # Ventas negativas son igualmente inválidas
        with pytest.raises(ValueError, match="monthly_sales"):
            self.use_case.execute(self._raw(monthly_sales="-500"))

    def test_calls_repository_save_with_valid_sale(self):
        # Verificar que la persistencia se delega al puerto con una entidad Sale válida
        from src.domain.entities import Sale
        self.use_case.execute(self._raw())
        self.mock_repository.save.assert_called_once()
        saved_sale = self.mock_repository.save.call_args[0][0]
        assert isinstance(saved_sale, Sale)
        assert saved_sale.monthly_sales == 1200
        assert saved_sale.product == "Producto A"

    def test_converts_string_monthly_sales_to_int(self):
        # Los valores del CSV llegan como strings; deben convertirse a int
        sale = self.use_case.execute(self._raw(monthly_sales="1200"))
        assert isinstance(sale.monthly_sales, int)
        assert sale.monthly_sales == 1200
