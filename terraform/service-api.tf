resource "google_project_service" "cloud-functions-api" {
  service = "cloudfunctions.googleapis.com"
}
resource "google_project_service" "storage-transfer-api" {
  service = "storagetransfer.googleapis.com"
}
resource "google_project_service" "composer-api" {
  service = "composer.googleapis.com"
}