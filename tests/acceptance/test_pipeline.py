# tests/acceptance/test_pipeline.py
# Tests de aceptación del flujo completo: simulan un mensaje push de Pub/Sub
# al endpoint de Cloud Run y verifican que el registro llega correctamente a BigQuery.
# Se usan mocks para BigQueryRepository, por lo que no se requieren credenciales GCP.
import base64
import json
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.domain.entities import Sale
from src.infrastructure.main import app, get_repository


def _make_pubsub_payload(data: dict) -> dict:
    """
    Genera un payload con el formato exacto que usa Pub/Sub para push subscriptions.
    El campo 'data' contiene el JSON codificado en base64.
    """
    encoded = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
    return {
        "message": {
            "data": encoded,
            "messageId": "test-message-123",
            "publishTime": "2022-01-01T00:00:00Z",
        },
        "subscription": "projects/test-project/subscriptions/test-sub",
    }


@pytest.fixture
def mock_repository():
    return MagicMock()


@pytest.fixture
def client(mock_repository):
    # Se sobreescribe la dependencia get_repository para inyectar el mock.
    # FastAPI dependency_overrides permite esto sin modificar el código de producción.
    app.dependency_overrides[get_repository] = lambda: mock_repository
    with TestClient(app) as c:
        yield c
    # Limpiar los overrides para no afectar otros tests
    app.dependency_overrides.clear()


@pytest.mark.acceptance
class TestPipeline:

    def test_valid_payload_returns_200_and_sale_id(self, client, mock_repository):
        # Un mensaje Pub/Sub válido debe procesarse exitosamente y retornar el sale_id
        payload = _make_pubsub_payload({
            "product": "Producto A",
            "region": "Región 1",
            "month": "Enero 2022",
            "monthly_sales": 1200,
        })

        response = client.post("/", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert "sale_id" in body
        assert body["status"] == "processed"

    def test_valid_payload_saves_correct_schema_to_repository(self, client, mock_repository):  # noqa: E501
        # Verificar que el registro guardado en BQ tiene todos los campos correctos
        payload = _make_pubsub_payload({
            "product": "Producto A",
            "region": "RegiÃ³n 1",   # Encoding artefacto — debe corregirse
            "month": "Enero 2022",
            "monthly_sales": 1200,
        })

        response = client.post("/", json=payload)

        assert response.status_code == 200
        mock_repository.save.assert_called_once()
        saved_sale: Sale = mock_repository.save.call_args[0][0]
        assert saved_sale.product == "Producto A"
        assert saved_sale.region == "Región 1"        # Encoding corregido
        assert saved_sale.date == date(2022, 1, 1)    # Fecha parseada correctamente
        assert saved_sale.year == 2022
        assert saved_sale.monthly_sales == 1200
        assert len(saved_sale.sale_id) == 36          # UUID v4: 8-4-4-4-12 = 36 chars

    def test_negative_sales_returns_422_and_does_not_save(self, client, mock_repository):  # noqa: E501
        # 422 indica datos inválidos; Pub/Sub NO reintenta mensajes con respuestas 4xx
        payload = _make_pubsub_payload({
            "product": "Producto A",
            "region": "Región 1",
            "month": "Enero 2022",
            "monthly_sales": -1,
        })

        response = client.post("/", json=payload)

        assert response.status_code == 422
        mock_repository.save.assert_not_called()

    def test_malformed_json_in_base64_returns_400(self, client, mock_repository):
        # JSON inválido retorna 400; Pub/Sub tampoco reintenta mensajes 4xx
        payload = {
            "message": {
                "data": base64.b64encode(b"not-valid-json").decode(),
                "messageId": "test-456",
                "publishTime": "2022-01-01T00:00:00Z",
            },
            "subscription": "projects/test/subscriptions/test-sub",
        }

        response = client.post("/", json=payload)

        assert response.status_code == 400
        mock_repository.save.assert_not_called()

    def test_health_check_returns_200(self, client):
        # El health check permite a Cloud Run verificar que el servicio está activo
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
