resource "google_bigquery_dataset" "udfs" {
  dataset_id                  = "udfs"
  friendly_name               = "UDFs for Data Extraction and Transfer"
  description                 = "A set of UDFs to support data extraction and transfer"
  location                    = var.bigquery_udf_dataset_location
}

resource "google_bigquery_routine" "transfer_s3_data" {
  dataset_id = google_bigquery_dataset.udfs.dataset_id
  routine_id     = "transfer_s3_data"
  routine_type = "PROCEDURE"
  language = "SQL"
  arguments {
    name = "sql_query"
    data_type = "{\"typeKind\": \"STRING\"}"
  }
  arguments {
    name = "destination_folder"
    data_type = "{\"typeKind\": \"STRING\"}"
  }
  definition_body = <<EOR
DECLARE
  user_email,
  extract_id STRING;
DECLARE
  gcs_bucket STRING DEFAULT('${google_storage_bucket.transfer-jobs.name}');
SET
  user_email = (
  SELECT
    SESSION_USER());
SET
  extract_id = (
  SELECT
    FORMAT("%s-%s", SPLIT(user_email, '@')[ OFFSET(0)], FORMAT_DATETIME("%Y%m%d-%H%M%E3S",
        CURRENT_DATETIME())));
EXPORT DATA
  OPTIONS( uri=CONCAT('gs://', gcs_bucket, '/', extract_id, '/*.json'),
    format='JSON',
    overwrite=TRUE) AS
SELECT
  extract_id,
  destination_folder,
  user_email,
  sql_query;

EOR
}