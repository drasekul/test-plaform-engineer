# tests/unit/test_entities.py
# Tests de la entidad central del dominio.
# Verifican que la dataclass se construye correctamente y mantiene sus invariantes.
import pytest
from datetime import date
from src.domain.entities import Sale


@pytest.mark.unit
class TestSale:

    def test_sale_can_be_created_with_all_fields(self):
        # Verificar que todos los campos se asignan correctamente
        sale = Sale(
            sale_id="123e4567-e89b-12d3-a456-426614174000",
            product="Producto A",
            region="Región 1",
            month="Enero 2022",
            monthly_sales=1200,
            date=date(2022, 1, 1),
            year=2022,
        )
        assert sale.sale_id == "123e4567-e89b-12d3-a456-426614174000"
        assert sale.product == "Producto A"
        assert sale.region == "Región 1"
        assert sale.month == "Enero 2022"
        assert sale.monthly_sales == 1200
        assert sale.date == date(2022, 1, 1)
        assert sale.year == 2022

    def test_sale_equality_based_on_fields(self):
        # Las dataclasses comparan por valor, no por referencia
        sale1 = Sale("id", "Prod A", "Reg 1", "Enero 2022", 100, date(2022, 1, 1), 2022)
        sale2 = Sale("id", "Prod A", "Reg 1", "Enero 2022", 100, date(2022, 1, 1), 2022)
        assert sale1 == sale2
