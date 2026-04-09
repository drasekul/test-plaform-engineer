# Platform Engineer Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un pipeline serverless en GCP (Cloud Run + Pub/Sub + BigQuery) con arquitectura hexagonal en Python, tests, Terraform y GitHub Actions siguiendo GitFlow.

**Architecture:** Hexagonal estricto con tres capas: `domain` (entidades + puertos ABC sin dependencias externas), `application` (casos de uso que orquestan el flujo), e `infrastructure` (adaptadores GCP + FastAPI). Los tests usan mocks puros — sin credenciales GCP reales.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, google-cloud-pubsub, google-cloud-bigquery, pytest, ruff, Terraform, GitHub Actions.

---

## Mapa de Archivos

| Archivo | Responsabilidad |
|---|---|
| `src/domain/entities.py` | Dataclass `Sale` — entidad central del dominio |
| `src/domain/ports.py` | ABCs `MessagePublisher` y `DataRepository` |
| `src/application/use_cases.py` | `ProcessSaleUseCase`, `PublishSaleUseCase` |
| `src/infrastructure/csv_reader.py` | Lectura del CSV de ventas |
| `src/infrastructure/bigquery_adapter.py` | Adaptador BigQuery (implementa `DataRepository`) |
| `src/infrastructure/pubsub_adapter.py` | Adaptador Pub/Sub (implementa `MessagePublisher`) |
| `src/infrastructure/main.py` | FastAPI app — endpoint POST / para recibir mensajes Pub/Sub |
| `publisher.py` | Script CLI: lee CSV y publica cada fila a Pub/Sub |
| `schema.json` | Schema JSON propuesto para mensajes Pub/Sub |
| `Dockerfile` | Imagen optimizada para Cloud Run |
| `requirements.txt` | Dependencias de producción |
| `requirements-dev.txt` | Dependencias de desarrollo/test |
| `pyproject.toml` | Config de pytest y ruff |
| `terraform/modules/platform/main.tf` | Recursos GCP: Cloud Run, Pub/Sub, BigQuery, SA |
| `terraform/modules/platform/variables.tf` | Variables del módulo Terraform |
| `terraform/modules/platform/outputs.tf` | Outputs del módulo Terraform |
| `terraform/environments/dev/main.tf` | Invoca módulo con vars del entorno dev |
| `terraform/environments/dev/backend.tf` | Backend remoto GCS para tfstate |
| `.github/workflows/pr-validation.yml` | CI en PRs: lint + tests (bloquea merge si falla) |
| `.github/workflows/develop-ci.yml` | CI en push a develop: tests + build Docker sin push |
| `.github/workflows/app-pipeline.yml` | CD en push a main: test + build + push + deploy |
| `.github/workflows/infra-pipeline.yml` | Infra: terraform plan + apply con aprobación manual |
| `tests/unit/test_entities.py` | Tests unitarios de la entidad Sale |
| `tests/unit/test_use_cases.py` | Tests unitarios de los casos de uso |
| `tests/unit/test_csv_reader.py` | Tests unitarios del lector de CSV |
| `tests/acceptance/test_pipeline.py` | Tests de aceptación del flujo completo |

---

## Task 1: Project Setup — Estructura y dependencias

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/domain/__init__.py`
- Create: `src/application/__init__.py`
- Create: `src/infrastructure/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/acceptance/__init__.py`

- [ ] **Step 1: Crear requirements.txt**

```
# Dependencias de producción del servicio Cloud Run.
# Versiones fijadas para garantizar reproducibilidad en el build de Docker.
fastapi==0.115.5
uvicorn[standard]==0.32.1
google-cloud-pubsub==2.27.0
google-cloud-bigquery==3.27.0
```

Guardar en: `requirements.txt`

- [ ] **Step 2: Crear requirements-dev.txt**

```
# Dependencias exclusivas de desarrollo y testing.
# Se separan de requirements.txt para no incluirlas en la imagen Docker de producción.
pytest==8.3.4
pytest-mock==3.14.0
pytest-cov==6.0.0
httpx==0.28.1
ruff==0.8.0
```

Guardar en: `requirements-dev.txt`

- [ ] **Step 3: Crear pyproject.toml**

```toml
# pyproject.toml centraliza la configuración de herramientas del proyecto.
# Se usa en lugar de múltiples archivos de config (setup.cfg, .flake8, etc.)

[tool.pytest.ini_options]
# testpaths limita pytest a la carpeta tests para evitar descubrir archivos no deseados
testpaths = ["tests"]
markers = [
    # Separar unit de acceptance permite ejecutar solo un subset en CI según el contexto
    "unit: tests unitarios sin dependencias externas (rápidos, sin GCP)",
    "acceptance: tests de aceptación del flujo completo (con mocks de integración)",
]
# --cov genera reporte de cobertura automáticamente en cada ejecución
addopts = "--cov=src --cov-report=term-missing"

[tool.ruff]
# Ruff reemplaza flake8 + isort con mejor rendimiento
line-length = 88
select = ["E", "F", "W", "I"]
```

- [ ] **Step 4: Crear archivos __init__.py vacíos**

```bash
mkdir -p src/domain src/application src/infrastructure
mkdir -p tests/unit tests/acceptance
touch src/__init__.py src/domain/__init__.py src/application/__init__.py src/infrastructure/__init__.py
touch tests/__init__.py tests/unit/__init__.py tests/acceptance/__init__.py
```

- [ ] **Step 5: Instalar dependencias localmente**

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Resultado esperado: instalación exitosa sin errores de conflicto.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-dev.txt pyproject.toml src/ tests/
git commit -m "chore: configurar estructura del proyecto y dependencias"
```

---

## Task 2: Domain Layer — Entidades y puertos (TDD)

**Files:**
- Create: `tests/unit/test_entities.py`
- Create: `src/domain/entities.py`
- Create: `src/domain/ports.py`

- [ ] **Step 1: Escribir el test de la entidad Sale**

```python
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
```

- [ ] **Step 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/test_entities.py -v
```

Resultado esperado: `FAILED` — `ModuleNotFoundError: No module named 'src.domain.entities'`

- [ ] **Step 3: Implementar entities.py**

```python
# src/domain/entities.py
# Entidad central del dominio. Representa una venta mensual por producto y región.
# Se usa dataclass para inmutabilidad implícita y comparación por valor.
# IMPORTANTE: este módulo NO tiene imports de GCP ni de ningún SDK externo.
# La independencia de dependencias externas es lo que hace testeable al dominio.
from dataclasses import dataclass
from datetime import date


@dataclass
class Sale:
    """
    Representa una venta mensual de un producto en una región.
    Todos los campos son el resultado de transformar y limpiar los datos del CSV original.
    """
    sale_id: str        # Identificador único UUID v4 generado en ProcessSaleUseCase
    product: str        # Nombre del producto normalizado (sin espacios extra)
    region: str         # Región con encoding corregido (ej. 'Región 1' en lugar de 'RegiÃ³n 1')
    month: str          # Período original en texto ('Enero 2022')
    monthly_sales: int  # Ventas del mes, validadas como entero positivo
    date: date          # Primer día del mes para uso como DATE en BigQuery
    year: int           # Año extraído de date para facilitar queries y particionado en BQ
```

- [ ] **Step 4: Implementar ports.py**

```python
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
```

- [ ] **Step 5: Ejecutar tests para verificar que pasan**

```bash
pytest tests/unit/test_entities.py -v
```

Resultado esperado:
```
tests/unit/test_entities.py::TestSale::test_sale_can_be_created_with_all_fields PASSED
tests/unit/test_entities.py::TestSale::test_sale_equality_based_on_fields PASSED
2 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/domain/ tests/unit/test_entities.py
git commit -m "feat: agregar entidad Sale y puertos del dominio"
```

---

## Task 3: Application Layer — ProcessSaleUseCase (TDD)

**Files:**
- Create: `tests/unit/test_use_cases.py` (clase TestProcessSaleUseCase)
- Create: `src/application/use_cases.py` (clase ProcessSaleUseCase)

- [ ] **Step 1: Escribir tests de ProcessSaleUseCase**

```python
# tests/unit/test_use_cases.py
# Tests de los casos de uso. Usan mocks para los puertos, garantizando que
# no hay dependencias de GCP. Cada test verifica una transformación específica.
import uuid
import pytest
from datetime import date
from unittest.mock import MagicMock
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
        sale = self.use_case.execute(self._raw(product="  Producto A  ", region="  Región 1  "))
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

    def test_calls_repository_save_exactly_once(self):
        # Verificar que la persistencia se delega correctamente al puerto
        self.use_case.execute(self._raw())
        self.mock_repository.save.assert_called_once()

    def test_converts_string_monthly_sales_to_int(self):
        # Los valores del CSV llegan como strings; deben convertirse a int
        sale = self.use_case.execute(self._raw(monthly_sales="1200"))
        assert isinstance(sale.monthly_sales, int)
        assert sale.monthly_sales == 1200
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/test_use_cases.py -v
```

Resultado esperado: `FAILED` — `ModuleNotFoundError: No module named 'src.application.use_cases'`

- [ ] **Step 3: Implementar ProcessSaleUseCase en use_cases.py**

```python
# src/application/use_cases.py
# Casos de uso: orquestan el flujo de la aplicación usando solo los puertos del dominio.
# Esta capa NO conoce si el destino es BigQuery, una base SQL, o un archivo.
# NO importa nada de google.cloud.* — eso es responsabilidad de la infraestructura.
import uuid
from datetime import date

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


def _parse_month_to_date(month_str: str) -> date:
    """
    Convierte 'Enero 2022' a date(2022, 1, 1).
    Se usa el primer día del mes como convención para representar el período mensual.
    Esto permite usar el campo como DATE en BigQuery para filtros y particionado eficientes.
    """
    parts = month_str.strip().split()
    month_name, year = parts[0], int(parts[1])
    month_num = _MONTH_MAP[month_name]
    return date(year, month_num, 1)


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
```

- [ ] **Step 4: Ejecutar tests para verificar que pasan**

```bash
pytest tests/unit/test_use_cases.py::TestProcessSaleUseCase -v
```

Resultado esperado:
```
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_corrects_region_encoding PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_parses_month_string_to_date PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_parses_december PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_strips_whitespace_from_strings PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_generates_valid_uuid_v4 PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_raises_value_error_for_zero_sales PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_raises_value_error_for_negative_sales PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_calls_repository_save_exactly_once PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_converts_string_monthly_sales_to_int PASSED
9 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/application/use_cases.py tests/unit/test_use_cases.py
git commit -m "feat: implementar ProcessSaleUseCase con transformaciones de datos"
```

---

## Task 4: Application Layer — PublishSaleUseCase (TDD)

**Files:**
- Modify: `tests/unit/test_use_cases.py` (agregar clase TestPublishSaleUseCase)
- Modify: `src/application/use_cases.py` (agregar clase PublishSaleUseCase)

- [ ] **Step 1: Agregar tests de PublishSaleUseCase en test_use_cases.py**

Agregar al final de `tests/unit/test_use_cases.py`:

```python
from datetime import date
from src.application.use_cases import PublishSaleUseCase
from src.domain.entities import Sale


@pytest.mark.unit
class TestPublishSaleUseCase:

    def setup_method(self):
        self.mock_publisher = MagicMock()
        # El publisher retorna un message_id (string) al publicar
        self.mock_publisher.publish.return_value = "msg-id-123"
        self.use_case = PublishSaleUseCase(publisher=self.mock_publisher)

    def _make_sale(self) -> Sale:
        return Sale(
            sale_id="test-uuid",
            product="Producto A",
            region="Región 1",
            month="Enero 2022",
            monthly_sales=1200,
            date=date(2022, 1, 1),
            year=2022,
        )

    def test_returns_message_id_from_publisher(self):
        # El message_id permite al caller loguear trazabilidad del mensaje publicado
        result = self.use_case.execute(self._make_sale())
        assert result == "msg-id-123"

    def test_calls_publisher_with_sale_entity(self):
        # El caso de uso delega la publicación al puerto sin conocer la implementación
        sale = self._make_sale()
        self.use_case.execute(sale)
        self.mock_publisher.publish.assert_called_once_with(sale)
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/test_use_cases.py::TestPublishSaleUseCase -v
```

Resultado esperado: `FAILED` — `ImportError: cannot import name 'PublishSaleUseCase'`

- [ ] **Step 3: Agregar PublishSaleUseCase al final de use_cases.py**

Agregar al final de `src/application/use_cases.py`:

```python
class PublishSaleUseCase:
    """
    Caso de uso de publicación: serializa una entidad Sale y la publica
    al bus de mensajes via el puerto MessagePublisher.
    Retorna el message_id para que el caller (publisher.py) pueda loguearlo.
    """

    def __init__(self, publisher: MessagePublisher) -> None:
        self._publisher = publisher

    def execute(self, sale: Sale) -> str:
        # Delega la publicación al puerto; no conoce si es Pub/Sub, SQS u otro broker
        message_id = self._publisher.publish(sale)
        return message_id
```

- [ ] **Step 4: Ejecutar todos los tests de use_cases para verificar que pasan**

```bash
pytest tests/unit/test_use_cases.py -v
```

Resultado esperado: todos los tests `PASSED` (9 + 2 = 11 en total).

- [ ] **Step 5: Commit**

```bash
git add src/application/use_cases.py tests/unit/test_use_cases.py
git commit -m "feat: agregar PublishSaleUseCase"
```

---

## Task 5: Infrastructure — CSV Reader (TDD)

**Files:**
- Create: `tests/unit/test_csv_reader.py`
- Create: `src/infrastructure/csv_reader.py`

- [ ] **Step 1: Escribir tests del CSV reader**

```python
# tests/unit/test_csv_reader.py
# Tests del lector de CSV. Usan archivos temporales para evitar dependencia
# del archivo ventas.csv real, haciendo los tests portables y deterministas.
import pytest
from src.infrastructure.csv_reader import read_csv


@pytest.mark.unit
class TestCsvReader:

    def test_reads_csv_and_returns_list_of_dicts(self, tmp_path):
        # El reader debe retornar una lista de dicts con las claves del header
        csv_content = "producto,region,mes,ventas_mensuales\nProducto A,RegiÃ³n 1,Enero 2022,1200\n"
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
        # La corrección es responsabilidad de ProcessSaleUseCase (separación de concerns).
        csv_content = "producto,region,mes,ventas_mensuales\nProducto A,RegiÃ³n 1,Enero 2022,1200\n"
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
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/test_csv_reader.py -v
```

Resultado esperado: `FAILED` — `ModuleNotFoundError: No module named 'src.infrastructure.csv_reader'`

- [ ] **Step 3: Implementar csv_reader.py**

```python
# src/infrastructure/csv_reader.py
# Adaptador de lectura del CSV de ventas.
# Responsabilidad única: leer el archivo y retornar los datos crudos como lista de dicts.
# La limpieza y transformación de datos es responsabilidad de ProcessSaleUseCase.
import csv


def read_csv(file_path: str) -> list[dict]:
    """
    Lee el archivo CSV de ventas y retorna una lista de diccionarios.

    Se usa encoding='utf-8' ya que ventas.csv está en UTF-8.
    Los artefactos de encoding como 'RegiÃ³n' son caracteres UTF-8 válidos
    que representan la corrupción del texto original; se corrigen en la capa de aplicación.
    
    Retorna los valores como strings (tal como los entrega csv.DictReader),
    sin conversión de tipos — eso también es responsabilidad del caso de uso.
    """
    rows = []
    with open(file_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows
```

- [ ] **Step 4: Ejecutar tests para verificar que pasan**

```bash
pytest tests/unit/test_csv_reader.py -v
```

Resultado esperado: 4 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/csv_reader.py tests/unit/test_csv_reader.py
git commit -m "feat: implementar lector de CSV"
```

---

## Task 6: Infrastructure — BigQuery Adapter (TDD con mocks)

**Files:**
- Create: `src/infrastructure/bigquery_adapter.py`

*Nota: no se crea test unitario para el adaptador de BQ porque requiere el SDK de GCP.
El comportamiento se cubre en los tests de aceptación via mock del repositorio completo.*

- [ ] **Step 1: Implementar bigquery_adapter.py**

```python
# src/infrastructure/bigquery_adapter.py
# Adaptador de BigQuery que implementa el puerto DataRepository.
# Este módulo es el único lugar del proyecto que conoce los detalles de BigQuery.
# Cualquier cambio de destino de datos (ej. migrar a Spanner) solo requiere cambiar aquí.
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
        # El cliente de BigQuery usa las credenciales de la SA del entorno (GOOGLE_APPLICATION_CREDENTIALS
        # o la SA asignada al Cloud Run, que es la forma recomendada en GCP).
        self._client = bigquery.Client(project=project_id)
        # Referencia completa a la tabla en formato project.dataset.table
        self._table_ref = f"{project_id}.{dataset_id}.{table_id}"

    def save(self, sale: Sale) -> None:
        """
        Inserta una fila en la tabla de BigQuery usando streaming insert (insert_rows_json).
        Se agrega ingested_at para trazabilidad de cuándo llegó el dato al pipeline.
        
        Nota: streaming inserts en BigQuery tienen latencia ~1s antes de ser visibles en queries.
        Para reportería en Looker Studio esto es aceptable.
        """
        row = {
            "sale_id": sale.sale_id,
            "product": sale.product,
            "region": sale.region,
            "month": sale.month,
            "monthly_sales": sale.monthly_sales,
            "date": sale.date.isoformat(),   # BigQuery acepta 'YYYY-MM-DD' para tipo DATE
            "year": sale.year,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        errors = self._client.insert_rows_json(self._table_ref, [row])
        if errors:
            # insert_rows_json retorna lista de errores vacía si todo OK
            raise RuntimeError(f"Error al insertar fila en BigQuery: {errors}")
```

- [ ] **Step 2: Commit**

```bash
git add src/infrastructure/bigquery_adapter.py
git commit -m "feat: implementar adaptador de BigQuery"
```

---

## Task 7: Infrastructure — PubSub Adapter (TDD con mocks)

**Files:**
- Create: `src/infrastructure/pubsub_adapter.py`

- [ ] **Step 1: Implementar pubsub_adapter.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add src/infrastructure/pubsub_adapter.py
git commit -m "feat: implementar adaptador de Pub/Sub"
```

---

## Task 8: Infrastructure — FastAPI Endpoint + Acceptance Tests (TDD)

**Files:**
- Create: `tests/acceptance/test_pipeline.py`
- Create: `src/infrastructure/main.py`

- [ ] **Step 1: Escribir tests de aceptación**

```python
# tests/acceptance/test_pipeline.py
# Tests de aceptación del flujo completo: simulan un mensaje push de Pub/Sub
# al endpoint de Cloud Run y verifican que el registro llega correctamente a BigQuery.
# Se usan mocks para BigQueryRepository, por lo que no se requieren credenciales GCP.
import base64
import json
import pytest
from datetime import date
from unittest.mock import MagicMock
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

    def test_valid_payload_saves_correct_schema_to_repository(self, client, mock_repository):
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

    def test_negative_sales_returns_422_and_does_not_save(self, client, mock_repository):
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
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/acceptance/test_pipeline.py -v
```

Resultado esperado: `FAILED` — `ModuleNotFoundError: No module named 'src.infrastructure.main'`

- [ ] **Step 3: Implementar main.py**

```python
# src/infrastructure/main.py
# Punto de entrada del servicio Cloud Run.
# Expone un endpoint HTTP POST / que recibe mensajes push de Pub/Sub,
# los decodifica y delega el procesamiento a ProcessSaleUseCase.
import base64
import json
import logging
import os

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from src.application.use_cases import ProcessSaleUseCase
from src.domain.ports import DataRepository
from src.infrastructure.bigquery_adapter import BigQueryRepository

# Configurar logging estructurado para que Cloud Logging lo capture correctamente
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FIF Sales Pipeline Subscriber",
    description="Suscriptor de Pub/Sub que procesa ventas y las almacena en BigQuery",
    version="1.0.0",
)


class PubSubMessage(BaseModel):
    """Estructura del mensaje individual de Pub/Sub."""
    data: str        # Payload codificado en base64
    messageId: str
    publishTime: str


class PubSubPushRequest(BaseModel):
    """
    Wrapper del request que Pub/Sub envía al endpoint de push subscription.
    Pub/Sub siempre envía esta estructura exacta al hacer HTTP POST.
    """
    message: PubSubMessage
    subscription: str


def get_repository() -> DataRepository:
    """
    Factoría del repositorio de BigQuery.
    Se usa inyección de dependencias de FastAPI para poder sobreescribir
    esta función con un mock en los tests de aceptación sin modificar el código de producción.
    Las variables de entorno se leen aquí para detectar configuración faltante al arrancar.
    """
    return BigQueryRepository(
        project_id=os.environ["GCP_PROJECT_ID"],
        dataset_id=os.environ["BQ_DATASET"],
        table_id=os.environ["BQ_TABLE"],
    )


@app.get("/health")
async def health_check():
    """
    Health check para Cloud Run.
    Cloud Run verifica este endpoint periódicamente; si retorna != 200, reinicia el contenedor.
    """
    return {"status": "ok"}


@app.post("/", status_code=status.HTTP_200_OK)
async def receive_pubsub_message(
    body: PubSubPushRequest,
    repository: DataRepository = Depends(get_repository),
):
    """
    Endpoint principal del suscriptor de Pub/Sub (push subscription).
    
    Pub/Sub espera HTTP 200-299 como confirmación (ACK).
    - Si retorna 4xx: Pub/Sub NO reintenta (error del cliente/datos inválidos).
    - Si retorna 5xx o timeout: Pub/Sub reintenta automáticamente (error transitorio).
    Esta distinción es crítica para evitar loops infinitos con datos corruptos.
    """
    try:
        # Decodificar el payload base64 del mensaje Pub/Sub
        decoded_bytes = base64.b64decode(body.message.data)
        raw_data = json.loads(decoded_bytes.decode("utf-8"))

    except json.JSONDecodeError as e:
        # JSON malformado: datos irrecuperables, no reintentar
        logger.error(f"JSON inválido en mensaje Pub/Sub message_id={body.message.messageId}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload del mensaje Pub/Sub no es JSON válido",
        )

    try:
        use_case = ProcessSaleUseCase(repository=repository)
        sale = use_case.execute(raw_data)

        logger.info(f"Venta procesada exitosamente: sale_id={sale.sale_id} product={sale.product}")
        return {"status": "processed", "sale_id": sale.sale_id}

    except ValueError as e:
        # Datos semánticamente inválidos (ej. monthly_sales negativo): no reintentar
        logger.error(f"Datos inválidos en mensaje message_id={body.message.messageId}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        # Error inesperado: retornar 500 para que Pub/Sub reintente
        logger.error(f"Error inesperado procesando message_id={body.message.messageId}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )
```

- [ ] **Step 4: Ejecutar tests de aceptación para verificar que pasan**

```bash
pytest tests/acceptance/test_pipeline.py -v
```

Resultado esperado:
```
tests/acceptance/test_pipeline.py::TestPipeline::test_valid_payload_returns_200_and_sale_id PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_valid_payload_saves_correct_schema_to_repository PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_negative_sales_returns_422_and_does_not_save PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_malformed_json_in_base64_returns_400 PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_health_check_returns_200 PASSED
5 passed
```

- [ ] **Step 5: Ejecutar suite completa de tests**

```bash
pytest -v
```

Resultado esperado: todos los tests de unit y acceptance pasan. Verificar cobertura ≥ 80% en `src/domain` y `src/application`.

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/main.py tests/acceptance/test_pipeline.py
git commit -m "feat: implementar endpoint FastAPI para suscripción push de Pub/Sub"
```

---

## Task 9: Publisher Script

**Files:**
- Create: `publisher.py`

- [ ] **Step 1: Implementar publisher.py**

```python
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
from src.domain.ports import DataRepository
from src.domain.entities import Sale
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
    # Leer el topic path desde variable de entorno para evitar hardcodear IDs de proyecto
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
            logger.warning(f"[{i}/{total}] Fila inválida omitida: {e} — datos: {raw_data}")

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
```

- [ ] **Step 2: Commit**

```bash
git add publisher.py
git commit -m "feat: agregar script publisher simulador de la célula de BI"
```

---

## Task 10: Schema JSON + Dockerfile

**Files:**
- Create: `schema.json`
- Create: `Dockerfile`

- [ ] **Step 1: Crear schema.json**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SaleRecord",
  "description": "Schema propuesto para mensajes publicados en el tópico de Pub/Sub. Define la estructura y tipos de los datos de ventas procesados por el pipeline.",
  "type": "object",
  "required": ["sale_id", "product", "region", "month", "monthly_sales", "date", "year"],
  "properties": {
    "sale_id": {
      "type": "string",
      "format": "uuid",
      "description": "Identificador único del registro, generado como UUID v4 en ProcessSaleUseCase"
    },
    "product": {
      "type": "string",
      "minLength": 1,
      "description": "Nombre del producto normalizado (sin espacios extra)"
    },
    "region": {
      "type": "string",
      "minLength": 1,
      "description": "Región de la venta con encoding corregido (UTF-8)"
    },
    "month": {
      "type": "string",
      "pattern": "^[A-Za-záéíóúÁÉÍÓÚ]+ \\d{4}$",
      "description": "Período mensual en texto, ej: 'Enero 2022'"
    },
    "monthly_sales": {
      "type": "integer",
      "minimum": 1,
      "description": "Total de ventas del mes, validado como entero positivo"
    },
    "date": {
      "type": "string",
      "format": "date",
      "description": "Primer día del mes en formato YYYY-MM-DD, para uso como DATE en BigQuery"
    },
    "year": {
      "type": "integer",
      "minimum": 2000,
      "description": "Año extraído de date para facilitar queries y particionado en BigQuery"
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 2: Crear Dockerfile**

```dockerfile
# Dockerfile
# Imagen optimizada para el servicio Cloud Run (suscriptor de Pub/Sub).
# Se usa python:3.11-slim para minimizar el tamaño de la imagen (~150MB vs ~900MB de la full).

FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar solo requirements primero para aprovechar el cache de capas de Docker.
# Si el código cambia pero las dependencias no, Docker reutiliza esta capa.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente después de instalar dependencias
COPY src/ ./src/

# Puerto configurado via variable de entorno para compatibilidad con Cloud Run.
# Cloud Run inyecta PORT automáticamente; este valor es el fallback.
ENV PORT=8080

# Uvicorn como servidor ASGI para FastAPI.
# --host 0.0.0.0 es necesario para que Cloud Run pueda enrutar tráfico al contenedor.
# --workers 1 porque Cloud Run escala horizontalmente a nivel de instancias, no de workers.
CMD ["uvicorn", "src.infrastructure.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
```

- [ ] **Step 3: Commit**

```bash
git add schema.json Dockerfile
git commit -m "feat: agregar schema JSON de Pub/Sub y Dockerfile optimizado para Cloud Run"
```

---

## Task 11: Terraform — Módulo platform

**Files:**
- Create: `terraform/modules/platform/variables.tf`
- Create: `terraform/modules/platform/main.tf`
- Create: `terraform/modules/platform/outputs.tf`

- [ ] **Step 1: Crear variables.tf**

```hcl
# terraform/modules/platform/variables.tf
# Variables de entrada del módulo platform.
# Al parametrizar todos los valores, el módulo puede reutilizarse en múltiples entornos
# (dev, staging, prod) simplemente pasando distintos valores.

variable "project_id" {
  description = "ID del proyecto GCP donde se despliegan los recursos"
  type        = string
}

variable "region" {
  description = "Región GCP para los recursos (ej. us-central1, southamerica-east1)"
  type        = string
}

variable "service_name" {
  description = "Nombre del servicio Cloud Run y prefijo para recursos relacionados"
  type        = string
  default     = "fif-sales-subscriber"
}

variable "image_url" {
  description = "URL completa de la imagen Docker en Artifact Registry (incluye tag del commit)"
  type        = string
}

variable "bq_dataset" {
  description = "ID del dataset de BigQuery donde se almacenan las ventas"
  type        = string
  default     = "fif_sales"
}

variable "bq_table" {
  description = "ID de la tabla de BigQuery de ventas"
  type        = string
  default     = "sales_records"
}

variable "pubsub_topic_name" {
  description = "Nombre del tópico de Pub/Sub para mensajes de ventas"
  type        = string
  default     = "ventas-topic"
}
```

- [ ] **Step 2: Crear main.tf**

```hcl
# terraform/modules/platform/main.tf
# Define todos los recursos GCP del pipeline de ventas.
# La separación en módulo permite reutilizarlo en múltiples entornos y facilita el testing.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# ─── Service Account de Ejecución (Cloud Run Runtime) ───────────────────────
# SA separada de la SA maestra (Terraform) para aplicar el principio de mínimo privilegio.
# Solo tiene los permisos estrictamente necesarios para operar en runtime.
resource "google_service_account" "cloudrun_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Cloud Run Runtime SA — ${var.service_name}"
  project      = var.project_id
  description  = "SA de ejecución para el suscriptor de Pub/Sub. Solo pubsub.subscriber y bigquery.dataEditor."
}

# Permiso para leer mensajes de Pub/Sub (consumir la suscripción)
resource "google_project_iam_member" "cloudrun_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

# Permiso para insertar filas en BigQuery (streaming insert)
resource "google_project_iam_member" "cloudrun_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

# ─── Pub/Sub ─────────────────────────────────────────────────────────────────
resource "google_pubsub_topic" "sales_topic" {
  name    = var.pubsub_topic_name
  project = var.project_id
}

# Suscripción push: Pub/Sub invoca el endpoint de Cloud Run con HTTP POST
# cuando llega un mensaje al tópico.
resource "google_pubsub_subscription" "sales_subscription" {
  name    = "${var.pubsub_topic_name}-subscription"
  topic   = google_pubsub_topic.sales_topic.name
  project = var.project_id

  push_config {
    # Cloud Run URL se conoce tras el primer deploy; Terraform lo gestiona via dependencia
    push_endpoint = "${google_cloud_run_v2_service.subscriber.uri}/"

    oidc_token {
      # Usar la SA de ejecución como token de autenticación garantiza que solo
      # Pub/Sub (con esta SA) puede invocar el endpoint de Cloud Run
      service_account_email = google_service_account.cloudrun_sa.email
    }
  }

  # 20 segundos para procesar el mensaje antes de que Pub/Sub lo reintente
  ack_deadline_seconds = 20

  # Si el mensaje falla repetidamente, evitar que bloquee el pipeline indefinidamente
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# ─── Cloud Run ───────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "subscriber" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  # Solo Pub/Sub y el load balancer pueden invocar el servicio.
  # Se evita exposición pública directa del endpoint para reducir la superficie de ataque.
  ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.cloudrun_sa.email

    scaling {
      # min_instances=0 permite cold start pero reduce costos en inactividad.
      # Para este caso de uso (ingesta batch) el cold start es aceptable.
      min_instance_count = 0
      # max_instances=5 permite escalar ante picos sin costos descontrolados.
      # Ajustar según volumen esperado de mensajes concurrentes.
      max_instance_count = 5
    }

    containers {
      image = var.image_url

      resources {
        limits = {
          # 1 CPU y 256Mi son suficientes para procesar mensajes individuales de Pub/Sub.
          # FastAPI + GCP SDKs requieren ~100Mi en estado estable.
          cpu    = "1"
          memory = "256Mi"
        }
      }

      # Variables de entorno para la configuración del servicio.
      # No se pasan credenciales: Cloud Run usa la SA asignada automáticamente.
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "BQ_DATASET"
        value = var.bq_dataset
      }
      env {
        name  = "BQ_TABLE"
        value = var.bq_table
      }
    }
  }
}

# ─── BigQuery ─────────────────────────────────────────────────────────────────
resource "google_bigquery_dataset" "sales_dataset" {
  dataset_id  = var.bq_dataset
  project     = var.project_id
  location    = var.region
  description = "Dataset de ventas mensuales procesadas por el pipeline de Pub/Sub"
}

resource "google_bigquery_table" "sales_table" {
  dataset_id          = google_bigquery_dataset.sales_dataset.dataset_id
  table_id            = var.bq_table
  project             = var.project_id
  deletion_protection = false # Permitir borrado via Terraform en entornos no-productivos

  # Schema alineado con la entidad Sale y el schema.json propuesto
  schema = jsonencode([
    { name = "sale_id",       type = "STRING",    mode = "REQUIRED", description = "UUID v4 único por registro" },
    { name = "product",       type = "STRING",    mode = "REQUIRED", description = "Nombre del producto normalizado" },
    { name = "region",        type = "STRING",    mode = "REQUIRED", description = "Región con encoding UTF-8 correcto" },
    { name = "month",         type = "STRING",    mode = "REQUIRED", description = "Período mensual en texto (ej. Enero 2022)" },
    { name = "monthly_sales", type = "INTEGER",   mode = "REQUIRED", description = "Total de ventas del mes" },
    { name = "date",          type = "DATE",      mode = "REQUIRED", description = "Primer día del mes para queries temporales" },
    { name = "year",          type = "INTEGER",   mode = "REQUIRED", description = "Año para facilitar particionado y queries" },
    { name = "ingested_at",   type = "TIMESTAMP", mode = "REQUIRED", description = "Timestamp de ingesta en el pipeline" },
  ])

  depends_on = [google_bigquery_dataset.sales_dataset]
}
```

- [ ] **Step 3: Crear outputs.tf**

```hcl
# terraform/modules/platform/outputs.tf
# Outputs del módulo: exponen valores que otros módulos o el entorno pueden consumir.
# El cloud_run_url es especialmente importante para configurar el push endpoint de Pub/Sub.

output "cloud_run_url" {
  description = "URL del servicio Cloud Run (usada como push endpoint de la suscripción Pub/Sub)"
  value       = google_cloud_run_v2_service.subscriber.uri
}

output "pubsub_topic_name" {
  description = "Nombre del tópico Pub/Sub para usar en el script publisher.py"
  value       = google_pubsub_topic.sales_topic.name
}

output "pubsub_topic_id" {
  description = "ID completo del tópico (projects/{project}/topics/{name}) para PUBSUB_TOPIC env var"
  value       = google_pubsub_topic.sales_topic.id
}

output "bq_table_id" {
  description = "ID completo de la tabla BigQuery (project.dataset.table) para queries en Looker Studio"
  value       = "${var.project_id}.${var.bq_dataset}.${var.bq_table}"
}

output "cloudrun_sa_email" {
  description = "Email de la SA de ejecución de Cloud Run"
  value       = google_service_account.cloudrun_sa.email
}
```

- [ ] **Step 4: Commit**

```bash
git add terraform/modules/
git commit -m "feat: agregar módulo Terraform platform (Cloud Run + Pub/Sub + BigQuery + SA)"
```

---

## Task 12: Terraform — Entorno dev

**Files:**
- Create: `terraform/environments/dev/backend.tf`
- Create: `terraform/environments/dev/main.tf`

- [ ] **Step 1: Crear backend.tf**

```hcl
# terraform/environments/dev/backend.tf
# Backend remoto en GCS para almacenar el tfstate.
# El estado remoto permite trabajo colaborativo y evita conflictos de estado local.
# El bucket debe crearse manualmente ANTES del primer terraform init
# (no puede ser gestionado por Terraform porque se necesita para Terraform).
terraform {
  backend "gcs" {
    bucket = "tf-state-fif-prueba"  # Reemplazar por el nombre real del bucket GCS
    prefix = "terraform/state/dev"
  }
}
```

- [ ] **Step 2: Crear main.tf del entorno dev**

```hcl
# terraform/environments/dev/main.tf
# Invoca el módulo platform con los valores específicos del entorno dev.
# La SA maestra (tf-deployer) ejecuta terraform apply con sus credenciales;
# la SA de ejecución (cloudrun-sa) se crea dentro del módulo y se asigna al Cloud Run.

terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "ID del proyecto GCP"
  type        = string
  default     = "test-fif-platform-engineer"
}

variable "region" {
  description = "Región GCP"
  type        = string
  default     = "REGION_PLACEHOLDER"  # Reemplazar con la región real (ej. us-central1)
}

variable "image_url" {
  description = "URL de la imagen Docker en Artifact Registry con tag del commit"
  type        = string
  default     = "REGION_PLACEHOLDER-docker.pkg.dev/test-fif-platform-engineer/AR_REPO_PLACEHOLDER/app:latest"
}

module "platform" {
  source = "../../modules/platform"

  project_id        = var.project_id
  region            = var.region
  image_url         = var.image_url
  service_name      = "fif-sales-subscriber"
  bq_dataset        = "fif_sales"
  bq_table          = "sales_records"
  pubsub_topic_name = "ventas-topic"
}

# Outputs del entorno para referencia en CI/CD y documentación
output "cloud_run_url"      { value = module.platform.cloud_run_url }
output "pubsub_topic_id"    { value = module.platform.pubsub_topic_id }
output "bq_table_id"        { value = module.platform.bq_table_id }
output "cloudrun_sa_email"  { value = module.platform.cloudrun_sa_email }
```

- [ ] **Step 3: Commit**

```bash
git add terraform/environments/
git commit -m "feat: agregar configuración de entorno dev con backend GCS remoto"
```

---

## Task 13: GitHub Actions — Workflows

**Files:**
- Create: `.github/workflows/pr-validation.yml`
- Create: `.github/workflows/develop-ci.yml`
- Create: `.github/workflows/app-pipeline.yml`
- Create: `.github/workflows/infra-pipeline.yml`

- [ ] **Step 1: Crear pr-validation.yml**

```yaml
# .github/workflows/pr-validation.yml
# Workflow de validación de Pull Requests hacia develop y main.
# Propósito: garantizar que ninguna nueva feature o fix rompa el código existente.
# Este workflow BLOQUEA el merge si algún step falla (branch protection rules en GitHub).
# Sigue la estrategia GitFlow: feature/* → develop → main.
name: PR Validation

on:
  pull_request:
    branches:
      - develop  # PRs de feature/* hacia develop
      - main     # PRs de develop o hotfix/* hacia main

jobs:
  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Instalar ruff
        run: pip install ruff==0.8.0

      # Ruff verifica estilo y errores comunes; falla el job si encuentra problemas
      - name: Ejecutar linter
        run: ruff check src/ tests/ publisher.py

  test:
    name: Tests (unit + acceptance)
    runs-on: ubuntu-latest
    needs: lint  # Los tests solo corren si el lint pasa

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Instalar dependencias
        run: pip install -r requirements.txt -r requirements-dev.txt

      # Se ejecutan tanto unit como acceptance; ambos deben pasar para aprobar el PR
      - name: Ejecutar tests con cobertura
        run: pytest -m "unit or acceptance" --cov=src --cov-report=term-missing -v
        env:
          # Variables mock para los tests de aceptación (no se usan credenciales reales)
          GCP_PROJECT_ID: "test-project"
          BQ_DATASET: "test-dataset"
          BQ_TABLE: "test-table"
```

- [ ] **Step 2: Crear develop-ci.yml**

```yaml
# .github/workflows/develop-ci.yml
# CI en la rama develop (post-merge).
# Propósito: validar el estado de la rama de integración después de cada merge.
# No hace deploy: develop es la rama de integración, no de producción.
# El build Docker sin push verifica que la imagen construye correctamente.
name: Develop CI

on:
  push:
    branches:
      - develop

jobs:
  test:
    name: Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Instalar dependencias
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Ejecutar suite completa de tests
        run: pytest -m "unit or acceptance" -v
        env:
          GCP_PROJECT_ID: "test-project"
          BQ_DATASET: "test-dataset"
          BQ_TABLE: "test-table"

  build:
    name: Build Docker (sin push)
    runs-on: ubuntu-latest
    needs: test  # Solo construir si los tests pasan

    steps:
      - uses: actions/checkout@v4

      # Construir la imagen Docker para verificar que el Dockerfile es válido.
      # No se hace push: develop no despliega a producción.
      - name: Build Docker image
        run: docker build -t fif-pipeline:${{ github.sha }} .
```

- [ ] **Step 3: Crear app-pipeline.yml**

```yaml
# .github/workflows/app-pipeline.yml
# Pipeline de despliegue a producción.
# Se dispara en push a main (merge desde develop o hotfix).
# Flujo: test → build + push a Artifact Registry → deploy a Cloud Run.
name: App Pipeline

on:
  push:
    branches:
      - main

jobs:
  test:
    name: Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Instalar dependencias
        run: pip install -r requirements.txt -r requirements-dev.txt

      # Re-ejecutar tests antes de cualquier build/deploy para garantizar
      # que el código que llega a main está validado
      - name: Ejecutar tests
        run: pytest -m "unit or acceptance" -v
        env:
          GCP_PROJECT_ID: "test-project"
          BQ_DATASET: "test-dataset"
          BQ_TABLE: "test-table"

  build-and-push:
    name: Build y Push a Artifact Registry
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      # Autenticación con GCP usando la SA key almacenada en GitHub Secrets
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - uses: google-github-actions/setup-gcloud@v2

      # Configurar Docker para usar Artifact Registry como registry
      - name: Configurar Docker para Artifact Registry
        run: gcloud auth configure-docker ${{ secrets.GCP_REGION }}-docker.pkg.dev

      # Tag con el SHA del commit para trazabilidad: saber exactamente qué commit está en producción
      - name: Build y Push imagen Docker
        run: |
          IMAGE="${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/${{ secrets.AR_REPO }}/app:${{ github.sha }}"
          docker build -t $IMAGE .
          docker push $IMAGE

  deploy:
    name: Deploy a Cloud Run
    runs-on: ubuntu-latest
    needs: build-and-push

    steps:
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - uses: google-github-actions/setup-gcloud@v2

      # Desplegar la nueva imagen al servicio Cloud Run existente.
      # gcloud run deploy actualiza el servicio sin downtime (rolling update).
      - name: Deploy a Cloud Run
        run: |
          IMAGE="${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/${{ secrets.AR_REPO }}/app:${{ github.sha }}"
          gcloud run deploy ${{ secrets.CLOUDRUN_SERVICE_NAME }} \
            --image $IMAGE \
            --region ${{ secrets.GCP_REGION }} \
            --project ${{ secrets.GCP_PROJECT_ID }}
```

- [ ] **Step 4: Crear infra-pipeline.yml**

```yaml
# .github/workflows/infra-pipeline.yml
# Pipeline de infraestructura como código con Terraform.
# Se dispara manualmente (workflow_dispatch) o automáticamente cuando cambia terraform/.
# El apply requiere aprobación manual en GitHub Environments para evitar cambios accidentales.
name: Infrastructure Pipeline

on:
  workflow_dispatch:  # Permite ejecución manual desde la UI de GitHub Actions
  push:
    branches:
      - main
    paths:
      - "terraform/**"  # Solo se dispara si hay cambios en Terraform

jobs:
  terraform-plan:
    name: Terraform Plan
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.0"

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          # La SA maestra (tf-deployer) tiene permisos para crear/modificar recursos GCP
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Terraform Init
        # Init descarga providers y configura el backend GCS remoto para el tfstate
        run: terraform init
        working-directory: terraform/environments/dev

      - name: Terraform Plan
        run: |
          terraform plan \
            -var="project_id=${{ secrets.GCP_PROJECT_ID }}" \
            -var="region=${{ secrets.GCP_REGION }}" \
            -out=tfplan
        working-directory: terraform/environments/dev

  terraform-apply:
    name: Terraform Apply
    runs-on: ubuntu-latest
    needs: terraform-plan
    # Solo aplica en main y requiere aprobación manual via GitHub Environment 'production'
    # Configurar en GitHub: Settings → Environments → production → Required reviewers
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.0"

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Terraform Init
        run: terraform init
        working-directory: terraform/environments/dev

      - name: Terraform Apply
        run: |
          terraform apply -auto-approve \
            -var="project_id=${{ secrets.GCP_PROJECT_ID }}" \
            -var="region=${{ secrets.GCP_REGION }}"
        working-directory: terraform/environments/dev
```

- [ ] **Step 5: Commit**

```bash
git add .github/
git commit -m "feat: agregar workflows de GitHub Actions (GitFlow: PR validation, develop CI, app pipeline, infra pipeline)"
```

---

## Task 14: Validación final

- [ ] **Step 1: Ejecutar suite completa de tests**

```bash
pytest -v --tb=short
```

Resultado esperado: todos los tests pasan. Ejemplo:
```
tests/unit/test_entities.py::TestSale::test_sale_can_be_created_with_all_fields PASSED
tests/unit/test_entities.py::TestSale::test_sale_equality_based_on_fields PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_corrects_region_encoding PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_parses_month_string_to_date PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_parses_december PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_strips_whitespace_from_strings PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_generates_valid_uuid_v4 PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_raises_value_error_for_zero_sales PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_raises_value_error_for_negative_sales PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_calls_repository_save_exactly_once PASSED
tests/unit/test_use_cases.py::TestProcessSaleUseCase::test_converts_string_monthly_sales_to_int PASSED
tests/unit/test_use_cases.py::TestPublishSaleUseCase::test_returns_message_id_from_publisher PASSED
tests/unit/test_use_cases.py::TestPublishSaleUseCase::test_calls_publisher_with_sale_entity PASSED
tests/unit/test_csv_reader.py::TestCsvReader::test_reads_csv_and_returns_list_of_dicts PASSED
tests/unit/test_csv_reader.py::TestCsvReader::test_returns_empty_list_for_header_only_csv PASSED
tests/unit/test_csv_reader.py::TestCsvReader::test_preserves_encoding_artifact_for_use_case PASSED
tests/unit/test_csv_reader.py::TestCsvReader::test_reads_multiple_rows PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_valid_payload_returns_200_and_sale_id PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_valid_payload_saves_correct_schema_to_repository PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_negative_sales_returns_422_and_does_not_save PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_malformed_json_in_base64_returns_400 PASSED
tests/acceptance/test_pipeline.py::TestPipeline::test_health_check_returns_200 PASSED
22 passed
```

- [ ] **Step 2: Verificar cobertura ≥ 80% en domain y application**

```bash
pytest --cov=src/domain --cov=src/application --cov-report=term-missing
```

Resultado esperado: cobertura ≥ 80% en ambas capas.

- [ ] **Step 3: Ejecutar linter**

```bash
ruff check src/ tests/ publisher.py
```

Resultado esperado: sin errores.

- [ ] **Step 4: Commit final y tag**

```bash
git add -A
git commit -m "chore: validación final — todos los tests pasan, linter OK"
git tag v1.0.0-dev
```

---

## Secrets requeridos en GitHub

Configurar en **Settings → Secrets and variables → Actions**:

| Secret | Descripción | Ejemplo |
|---|---|---|
| `GCP_PROJECT_ID` | ID del proyecto GCP | `test-fif-platform-engineer` |
| `GCP_SA_KEY` | JSON de la SA maestra (tf-deployer) en base64 | `{ "type": "service_account", ... }` |
| `GCP_REGION` | Región GCP | `us-central1` |
| `AR_REPO` | Nombre del repositorio en Artifact Registry | `docker-fif-ventas` |
| `CLOUDRUN_SERVICE_NAME` | Nombre del servicio Cloud Run | `fif-sales-subscriber` |
| `TF_STATE_BUCKET` | Nombre del bucket GCS para tfstate | `tf-state-fif-prueba` |
