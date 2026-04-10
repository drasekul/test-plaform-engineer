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
