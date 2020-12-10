resource "google_composer_environment" "bq-export-and-transfer" {
  name   = var.composer_env
  region = var.region
  config {
    node_count = 3
    node_config {
      zone = var.composer_zone
      service_account = google_service_account.composer-worker-sa.name
    }
    software_config {
      env_variables = {
        AIRFLOW_VAR_TRANSFER_JOBS_PROJECT_ID = var.project_id
        AIRFLOW_VAR_DATA_EXTRACT_GCS_BUCKET = google_storage_bucket.data-extracts.name
        AIRFLOW_VAR_DATA_EXTRACT_AWS_BUCKET = var.aws_extract_bucket
        AIRFLOW_VAR_BQ_AWS_CONNECTION_NAME = var.bq_aws_connection_name
        SENDGRID_API_KEY = var.sendgrid_api_key
        SENDGRID_MAIL_FROM = var.email_from
      }
      pypi_packages = {
        boto3 = ""
      }
      python_version = "3"
    }
  }

  timeouts {
    create = "90m"
    update = "60m"
    delete = "10m"
  }
  depends_on = [google_project_iam_member.composer-worker-role]
}

resource "google_service_account" "composer-worker-sa" {
  account_id   = "composer-worker-sa"
  display_name = "Service Account for Composer Environment"
}

resource "google_project_iam_member" "composer-worker-role" {
  role   = "roles/composer.worker"
  member = "serviceAccount:${google_service_account.composer-worker-sa.email}"
}

resource "google_project_iam_member" "composer-worker-bq-admin-role" {
  role    = "roles/bigquery.user"
  member = "serviceAccount:${google_service_account.composer-worker-sa.email}"
}

resource "google_project_iam_member" "composer-worker-storage-transfer-admin-role" {
  role    = "roles/storagetransfer.admin"
  member = "serviceAccount:${google_service_account.composer-worker-sa.email}"
}

resource "google_project_iam_member" "composer-worker-storage-admin-role" {
  role    = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.composer-worker-sa.email}"
}

resource "google_project_iam_member" "composer-worker-bq-connection-user-role" {
  role    = "roles/bigquery.connectionUser"
  member = "serviceAccount:${google_service_account.composer-worker-sa.email}"
}

resource "google_storage_bucket_object" "dags" {
  for_each = fileset("${path.module}/../composer/dags/", "**")
  name     = "dags/${each.value}"
  source   = "${path.module}/../composer/dags/${each.value}"
  bucket   = element(split("/", google_composer_environment.bq-export-and-transfer.config[0].dag_gcs_prefix), 2)
}

output "dag_gcs_bucket" {
  value = element(split("/", google_composer_environment.bq-export-and-transfer.config[0].dag_gcs_prefix), 2)
}

output "airflow_uri" {
  value = google_composer_environment.bq-export-and-transfer.config[0].airflow_uri
}


