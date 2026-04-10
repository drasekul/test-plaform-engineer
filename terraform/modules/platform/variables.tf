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
