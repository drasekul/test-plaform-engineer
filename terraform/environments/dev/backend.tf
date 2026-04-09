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
