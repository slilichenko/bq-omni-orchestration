provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project" "main" {
  name       = "BigQuery Omni Transfer Demo"
  project_id = var.project_id
  billing_account = var.billing_account

  lifecycle {
    prevent_destroy = true
    ignore_changes = [name, billing_account]
  }
}