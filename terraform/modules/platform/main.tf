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
  account_id   = "cloudrun-sa"
  display_name = "Cloud Run Runtime SA — ${var.service_name}"
  project      = var.project_id
  description  = "SA de ejecución para el suscriptor de Pub/Sub. Solo pubsub.subscriber, bigquery.dataEditor y artifactregistry.reader."
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

# Permiso para descargar imágenes Docker desde Artifact Registry al arrancar Cloud Run
resource "google_project_iam_member" "cloudrun_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
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
          # Cloud Run requiere mínimo 512Mi cuando la CPU no está throttled (always allocated).
          # FastAPI + GCP SDKs requieren ~100Mi en estado estable; 512Mi es suficiente.
          cpu    = "1"
          memory = "512Mi"
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
