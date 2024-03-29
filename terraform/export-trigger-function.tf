data "archive_file" "local_export_starter_source" {
  type = "zip"
  source_dir = "../functions/export-starter"
  output_path = "${var.local_output_path}/export-starter.zip"
}

resource "google_storage_bucket_object" "gcs_export_starter_source" {
  name = "functions/export-starter.zip"
  bucket = google_storage_bucket.deployments.name
  source = data.archive_file.local_export_starter_source.output_path
}

resource "google_cloudfunctions_function" "function_export_starter" {
  name = "export_starter"
  project = var.project_id
  region = var.region
  available_memory_mb = "256"
  entry_point = "trigger_dag"
  runtime = "python37"
  source_archive_bucket = google_storage_bucket.deployments.name
  source_archive_object = google_storage_bucket_object.gcs_export_starter_source.name
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource = google_storage_bucket.transfer-jobs.name
  }
  environment_variables = {
    AIRFLOW_URI = google_composer_environment.bq-export-and-transfer.config[0].airflow_uri
    PROJECT_ID = data.google_project.main.project_id
    LOCATION = google_composer_environment.bq-export-and-transfer.region
    COMPOSER_ENV = google_composer_environment.bq-export-and-transfer.name
  }

  depends_on = [google_project_service.cloud-functions-api]
}