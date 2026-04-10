# Diseño — Pipeline Serverless GCP (Prueba Técnica Platform Engineer)

**Fecha:** 2026-04-09  
**Proyecto GCP:** `test-fif-platform-engineer`  
**Autor:** drasekul

---

## Contexto

Pipeline serverless en GCP que ingesta datos de ventas desde un CSV, los publica en Pub/Sub, los procesa mediante Cloud Run y los almacena en BigQuery para su visualización en Looker Studio. El stack completo debe estar versionado en GitHub con CI/CD (GitHub Actions) e infraestructura provisionada mediante Terraform.

---

## Decisiones de Diseño

### Patrón Arquitectónico: Hexagonal estricto

Se usa el patrón hexagonal (puertos y adaptadores) para mantener la lógica de negocio completamente desacoplada de los SDKs de GCP. Esto permite testear el dominio y los casos de uso sin credenciales reales ni conexiones externas.

- `domain/` — entidades y puertos (interfaces abstractas). Sin dependencias externas.
- `application/` — casos de uso que orquestan el flujo usando solo los puertos.
- `infrastructure/` — adaptadores concretos (Pub/Sub, BigQuery, FastAPI).

### Framework: FastAPI + uvicorn

FastAPI sobre Flask por tipado estático nativo, validación automática con Pydantic, y rendimiento superior. El endpoint Cloud Run es un servidor uvicorn que expone `POST /` para el push de Pub/Sub.

### Idioma del código

- **Código** (clases, variables, funciones, archivos): inglés
- **Comentarios**: español (para facilitar revisión por el equipo evaluador)

---

## Estructura del Repositorio

```
test-platform-engineer/
├── src/
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities.py        # Dataclass Sale
│   │   └── ports.py           # ABCs: MessagePublisher, DataRepository
│   ├── application/
│   │   ├── __init__.py
│   │   └── use_cases.py       # ProcessSaleUseCase, PublishSaleUseCase
│   └── infrastructure/
│       ├── __init__.py
│       ├── pubsub_adapter.py  # PubSubPublisher(MessagePublisher)
│       ├── bigquery_adapter.py # BigQueryRepository(DataRepository)
│       ├── csv_reader.py      # Lectura de ventas.csv
│       └── main.py            # FastAPI app
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_entities.py
│   │   ├── test_use_cases.py
│   │   └── test_csv_reader.py
│   └── acceptance/
│       ├── __init__.py
│       └── test_pipeline.py
├── terraform/
│   ├── modules/platform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── environments/dev/
│       ├── main.tf
│       └── backend.tf
├── .github/workflows/
│   ├── pr-validation.yml
│   ├── develop-ci.yml
│   ├── app-pipeline.yml
│   └── infra-pipeline.yml
├── ventas.csv
├── publisher.py
├── schema.json
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

---

## Flujo de Datos

```
ventas.csv → publisher.py → Pub/Sub topic
                                  ↓ (HTTP push subscription)
                           Cloud Run POST /
                                  ↓
                          ProcessSaleUseCase
                          (limpieza + transform)
                                  ↓
                            BigQuery tabla
                                  ↓
                           Looker Studio
```

---

## Capa de Dominio

### `domain/entities.py` — Dataclass `Sale`

| Campo | Tipo | Descripción |
|---|---|---|
| `sale_id` | `str` | UUID v4 generado automáticamente |
| `product` | `str` | Nombre del producto normalizado |
| `region` | `str` | Región con encoding corregido |
| `month` | `str` | Mes y año original ("Enero 2022") |
| `monthly_sales` | `int` | Ventas mensuales validadas como entero positivo |
| `date` | `date` | Primer día del mes parseado (2022-01-01) |
| `year` | `int` | Año extraído para facilitar queries en BigQuery |

### `domain/ports.py` — Interfaces abstractas

```python
class MessagePublisher(ABC):
    @abstractmethod
    def publish(self, sale: Sale) -> str: ...  # retorna message_id

class DataRepository(ABC):
    @abstractmethod
    def save(self, sale: Sale) -> None: ...
```

---

## Transformaciones de Datos

Aplicadas en `ProcessSaleUseCase.execute()`:

| # | Transformación | Motivo |
|---|---|---|
| 1 | Fix encoding `RegiÃ³n` → `Región` | El CSV tiene error de encoding latin-1/utf-8 |
| 2 | `strip()` en todos los strings | Evitar espacios invisibles que rompan queries BQ |
| 3 | Parse `"Enero 2022"` → `date(2022, 1, 1)` | BigQuery requiere tipo DATE para filtros temporales |
| 4 | Generar `sale_id` con `uuid4()` | Identificador único por registro |
| 5 | Validar `monthly_sales > 0` | Rechazar datos corruptos antes de insertar en BQ |

---

## Schema JSON para Pub/Sub (`schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SaleRecord",
  "type": "object",
  "required": ["sale_id", "product", "region", "month", "monthly_sales", "date"],
  "properties": {
    "sale_id":       { "type": "string", "format": "uuid" },
    "product":       { "type": "string" },
    "region":        { "type": "string" },
    "month":         { "type": "string" },
    "monthly_sales": { "type": "integer", "minimum": 1 },
    "date":          { "type": "string", "format": "date" },
    "year":          { "type": "integer" }
  }
}
```

---

## Capa de Aplicación

### `ProcessSaleUseCase`
- Recibe `raw_data: dict` desde Pub/Sub
- Aplica las 5 transformaciones listadas arriba
- Llama a `repository.save(sale)` 
- Retorna la entidad `Sale` transformada

### `PublishSaleUseCase`
- Recibe una entidad `Sale`
- Serializa a JSON
- Delega a `publisher.publish(sale)`
- Retorna `message_id` para trazabilidad

---

## Capa de Infraestructura

### `infrastructure/main.py` — FastAPI

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | POST | Recibe push de Pub/Sub, decodifica base64, ejecuta `ProcessSaleUseCase` |
| `/health` | GET | Health check para Cloud Run |

Cloud Run retorna HTTP 200 en éxito. Si retorna != 2xx, Pub/Sub reintenta automáticamente.

### `infrastructure/bigquery_adapter.py`
- Mapea `Sale` → dict
- Agrega campo `ingested_at: datetime.utcnow()` (timestamp de ingesta)
- Usa `insert_rows_json` hacia la tabla destino

### `publisher.py` (raíz)
- Simulador de la célula de BI
- Lee `ventas.csv` via `csv_reader`
- Publica cada fila como mensaje independiente
- Acepta `--file` y `--batch-size` como args CLI
- Loguea `message_id` por cada mensaje para trazabilidad

---

## Tests

### Unit (`tests/unit/`)
Sin dependencias GCP. Usan `pytest-mock` para simular los puertos.

Casos cubiertos:
- Encoding fix: `RegiÃ³n 1` → `Región 1`
- Parse fecha: `"Enero 2022"` → `date(2022, 1, 1)`
- Strip strings: `"  Producto A  "` → `"Producto A"`
- UUID generado es válido
- `monthly_sales <= 0` lanza `ValueError`
- `repository.save()` es llamado exactamente una vez

### Acceptance (`tests/acceptance/`)
Flujo completo con `TestClient` de FastAPI y mocks de integración.

Casos cubiertos:
- POST con payload Pub/Sub válido → HTTP 200 + `save()` llamado
- POST con `monthly_sales <= 0` → HTTP 422
- POST con JSON malformado → HTTP 400
- El registro guardado tiene todos los campos del schema

### Configuración (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
markers = [
    "unit: tests unitarios sin dependencias externas",
    "acceptance: tests de aceptación del flujo completo",
]
```

Cobertura objetivo: ≥ 80% en capas `domain` y `application`.

---

## Terraform

### Módulo `terraform/modules/platform/`

Recursos gestionados:
- `google_pubsub_topic` — tópico de mensajes
- `google_pubsub_subscription` — suscripción push al Cloud Run
- `google_cloud_run_v2_service` — servicio Cloud Run
- `google_bigquery_dataset` + `google_bigquery_table` — almacén de datos
- `google_service_account` — SA de ejecución (runtime)
- `google_project_iam_member` — bindings IAM con mínimos privilegios

### Cloud Run — Recursos mínimos viables

| Parámetro | Valor | Motivo |
|---|---|---|
| `cpu` | `1` | Suficiente para procesamiento de mensajes individuales |
| `memory` | `256Mi` | Mínimo para FastAPI + GCP SDKs |
| `min_instances` | `0` | Cold start aceptable; reduce costos en inactividad |
| `max_instances` | `5` | Permite escalar ante volumen alto sin costos descontrolados |
| `concurrency` | `80` | Default Cloud Run; maneja múltiples push simultáneos |
| `ingress` | `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER` | Solo Pub/Sub y load balancer pueden invocar el servicio; no expuesto públicamente |

### Service Accounts

| SA | Rol | Propósito |
|---|---|---|
| `tf-deployer` (maestra) | `run.admin`, `pubsub.admin`, `bigquery.admin`, `storage.admin`, `iam.serviceAccountUser` | Solo para ejecutar Terraform |
| `cloudrun-sa` (ejecución) | `pubsub.subscriber`, `bigquery.dataEditor` | Runtime del Cloud Run |

### Backend remoto

```hcl
# terraform/environments/dev/backend.tf
terraform {
  backend "gcs" {
    bucket = "tf-state-fif-prueba"
    prefix = "terraform/state"
  }
}
```

---

## GitHub Actions — Flujo GitFlow

### Estrategia de ramas

```
feature/* ──PR──→ develop ──PR──→ main
hotfix/*  ──────────────────PR──→ main
```

### Workflows

| Archivo | Trigger | Pasos | Propósito |
|---|---|---|---|
| `pr-validation.yml` | PR → `develop` o `main` | lint → unit tests → acceptance tests → cobertura | Proteger ramas principales; bloquea merge si falla |
| `develop-ci.yml` | push → `develop` | unit tests → acceptance tests → build Docker (sin push) | Validar estado de integración post-merge |
| `app-pipeline.yml` | push → `main` | test → build → push AR → deploy Cloud Run | Deploy a producción |
| `infra-pipeline.yml` | manual / cambios en `terraform/` | tf init → tf plan → tf apply (aprobación manual en main) | Gestión de infraestructura como código |

### Secrets requeridos en GitHub

```
GCP_PROJECT_ID
GCP_SA_KEY
GCP_REGION
AR_REPO              # Artifact Registry repository name
CLOUDRUN_SERVICE_NAME
TF_STATE_BUCKET
```

---

## Convenciones Generales

- **Código**: inglés (clases, variables, funciones, archivos, recursos Terraform)
- **Comentarios**: español (explican el *por qué* de cada decisión)
- **Python**: 3.11
- **Linter**: ruff
- **Tests**: pytest con markers `unit` y `acceptance`
- **Docker image tag**: SHA del commit para trazabilidad
