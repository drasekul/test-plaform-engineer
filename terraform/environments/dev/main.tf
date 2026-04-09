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
