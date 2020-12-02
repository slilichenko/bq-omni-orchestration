resource "google_composer_environment" "bq-demo" {
  name   = var.composer_env
  region = var.region
  config {
    node_count = 3
    node_config {
      zone = var.composer_zone
      service_account = google_service_account.composer-worker-sa.name
    }
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