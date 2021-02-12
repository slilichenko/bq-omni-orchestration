# Grant permissions to the transfer service account
resource "google_project_iam_member" "transfer-service-worker-storage-admin-role" {
  role    = "roles/storage.admin"
  member = "serviceAccount:project-${data.google_project.main.number}@storage-transfer-service.iam.gserviceaccount.com"
  depends_on = [google_project_service.storage-transfer-api]
}