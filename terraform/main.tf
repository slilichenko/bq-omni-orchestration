provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project" "main" {
  name       = "BigQuery Transfer Demo"
  project_id = var.project_id
  billing_account = var.billing_account
}