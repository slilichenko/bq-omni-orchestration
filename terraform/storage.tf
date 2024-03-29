resource "google_storage_bucket" "transfer-jobs" {
  name = "${var.project_id}-transfer-jobs"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "deployments" {
  name = "${var.project_id}-deployments"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "data-extracts" {
  name = "${var.project_id}-data-extracts"
  uniform_bucket_level_access = true
  location = var.bigquery_dataset_location
  force_destroy = true
}