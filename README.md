# FIF Sales Pipeline — Platform Engineer Technical Test

Pipeline de ingesta de ventas mensuales usando Google Cloud Platform con arquitectura hexagonal.

## Arquitectura

```
ventas.csv → publisher.py → Pub/Sub → Cloud Run (FastAPI) → BigQuery
```

- **publisher.py**: lee `ventas.csv` y publica cada fila como mensaje independiente al tópico de Pub/Sub.
- **Cloud Run**: suscriptor HTTP que recibe mensajes de Pub/Sub vía push, los transforma y los inserta en BigQuery via streaming insert.
- **Terraform**: gestiona toda la infraestructura (Cloud Run, Pub/Sub, BigQuery, Service Accounts, IAM).
- **GitHub Actions**: cuatro pipelines GitFlow — `pr-validation`, `develop-ci`, `app-pipeline` e `infra-pipeline`.

## Estructura del proyecto

```
.
├── src/
│   ├── domain/          # Entidades y puertos (interfaces ABC)
│   ├── application/     # Casos de uso (lógica de negocio)
│   └── infrastructure/  # Adaptadores GCP (FastAPI, BigQuery, Pub/Sub)
├── terraform/
│   ├── modules/platform/ # Módulo reutilizable (Cloud Run + Pub/Sub + BigQuery + SA)
│   └── environments/dev/ # Configuración del entorno dev con backend GCS
├── tests/
│   ├── unit/            # Tests sin dependencias externas
│   └── acceptance/      # Tests de integración con TestClient
├── .github/workflows/   # GitFlow CI/CD (pr-validation, develop-ci, app-pipeline, infra-pipeline)
├── publisher.py         # Simulador de publicación desde CSV
├── ventas.csv           # Dataset de ventas mensuales
├── schema.json          # Schema JSON del mensaje Pub/Sub
└── Dockerfile           # Imagen optimizada para Cloud Run
```

## Ejecución local

### Requisitos previos

- Python 3.11+
- Google Cloud SDK con credenciales configuradas (`GOOGLE_APPLICATION_CREDENTIALS`)

### Instalar dependencias

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # para tests
```

### Ejecutar tests

```bash
# Tests unitarios
pytest -m unit

# Tests de aceptación
pytest -m acceptance

# Todos los tests con cobertura
pytest --cov=src
```

### Publicar ventas a Pub/Sub

Requiere la key JSON de la SA `publisher-sa` (incluida por separado). Esta SA tiene únicamente el permiso `roles/pubsub.publisher`, siguiendo el principio de mínimo privilegio.

```bash
export PUBSUB_TOPIC=projects/test-fif-platform-engineer/topics/ventas-topic
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/publisher-sa-key.json

python publisher.py --file ventas.csv
```

## Infraestructura GCP

| Recurso | Nombre |
|---|---|
| Proyecto | `test-fif-platform-engineer` |
| Región | `southamerica-west1` |
| Cloud Run | `fif-sales-subscriber` |
| Pub/Sub Topic | `ventas-topic` |
| BigQuery Dataset | `fif_sales` |
| BigQuery Table | `sales_records` |
| Artifact Registry | `docker-fif-sales` |

### Desplegar infraestructura

```bash
cd terraform/environments/dev
terraform init
terraform plan -var="project_id=test-fif-platform-engineer" -var="region=southamerica-west1"
terraform apply -var="project_id=test-fif-platform-engineer" -var="region=southamerica-west1"
```

## CI/CD (GitFlow)

| Workflow | Disparo | Acción |
|---|---|---|
| `pr-validation` | Pull Request a `develop` o `main` | ruff lint + pytest (unit + acceptance) |
| `develop-ci` | Push a `develop` | ruff lint + pytest (unit + acceptance) |
| `app-pipeline` | Push a `main` (cambios en `src/` o `Dockerfile`) | build image → push Artifact Registry → deploy Cloud Run |
| `infra-pipeline` | Push a `main` (cambios en `terraform/`) | terraform plan → terraform apply (con aprobación manual en Environment `production`) |

## Decisiones de diseño

- **Arquitectura hexagonal**: el dominio no conoce GCP; los adaptadores implementan los puertos (interfaces ABC). Facilita testing y cambio de infraestructura.
- **lifecycle.ignore_changes en Cloud Run**: Terraform gestiona la estructura del servicio; `app-pipeline` gestiona la imagen. Evita conflictos de estado entre pipelines.
- **SA de mínimo privilegio**: tres SAs con responsabilidades separadas — `tf-deployer` (Terraform), `cloudrun-sa` (runtime Cloud Run) y `publisher-sa` (simulador local). Cada una tiene solo los permisos necesarios para su función.
- **Pub/Sub push con OIDC**: la suscripción usa token OIDC de `cloudrun-sa` para autenticar las llamadas HTTP al endpoint de Cloud Run.
