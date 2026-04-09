# tests/unit/test_csv_reader.py
# Tests del lector de CSV. Usan archivos temporales para evitar dependencia
# del archivo ventas.csv real, haciendo los tests portables y deterministas.
import pytest

from src.infrastructure.csv_reader import read_csv


@pytest.mark.unit
class TestCsvReader:

    def test_reads_csv_and_returns_list_of_dicts(self, tmp_path):
        # El reader debe retornar una lista de dicts con las claves del header
        csv_content = (
            "producto,region,mes,ventas_mensuales\n"
            "Producto A,RegiÃ³n 1,Enero 2022,1200\n"
        )
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        result = read_csv(str(csv_file))

        assert len(result) == 1
        assert result[0]["producto"] == "Producto A"
        assert result[0]["mes"] == "Enero 2022"
        assert result[0]["ventas_mensuales"] == "1200"

    def test_returns_empty_list_for_header_only_csv(self, tmp_path):
        # Un CSV sin datos no debe causar error
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("producto,region,mes,ventas_mensuales\n", encoding="utf-8")

        result = read_csv(str(csv_file))

        assert result == []

    def test_preserves_encoding_artifact_for_use_case(self, tmp_path):
        # El reader NO corrige el encoding; lo pasa tal cual al caso de uso.
        # La corrección es responsabilidad de ProcessSaleUseCase
        # (separación de concerns).
        csv_content = (
            "producto,region,mes,ventas_mensuales\n"
            "Producto A,RegiÃ³n 1,Enero 2022,1200\n"
        )
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        result = read_csv(str(csv_file))

        # El artefacto 'RegiÃ³n' debe llegar intacto al caso de uso
        assert result[0]["region"] == "RegiÃ³n 1"

    def test_reads_multiple_rows(self, tmp_path):
        csv_content = (
            "producto,region,mes,ventas_mensuales\n"
            "Producto A,Región 1,Enero 2022,1200\n"
            "Producto B,Región 2,Febrero 2022,800\n"
        )
        csv_file = tmp_path / "multi.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        result = read_csv(str(csv_file))

        assert len(result) == 2
        assert result[1]["producto"] == "Producto B"
