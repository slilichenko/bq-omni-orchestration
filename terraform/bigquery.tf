resource "google_bigquery_dataset" "exported_data" {
  dataset_id = "bq_omni_export"
  friendly_name = "BQ Omni Exported Data"
  location = var.bigquery_dataset_location

  access {
    role = "OWNER"
    user_by_email = google_service_account.composer-worker-sa.email
  }
}

resource "google_bigquery_dataset" "udfs" {
  dataset_id                  = "udfs"
  friendly_name               = "UDFs and Stored Procedures for Data Extraction and Transfer"
  description                 = "UDFs and Stored Procedures for Data Extraction and Transfer"
  location                    = var.bigquery_dataset_location
}

resource "google_bigquery_routine" "generate_extract_id" {
  dataset_id = google_bigquery_dataset.udfs.dataset_id
  routine_id     = "generate_extract_id"
  routine_type = "PROCEDURE"
  language = "SQL"
  arguments {
    name = "extract_id"
    data_type = "{\"typeKind\": \"STRING\"}"
    mode = "OUT"
  }
  definition_body = <<EOR
DECLARE
  user_email STRING;
SET
  user_email = (
  SELECT
    SESSION_USER());
SET
  extract_id = (
  SELECT
    FORMAT("%s-%s", SPLIT(user_email, '@')[ OFFSET(0)], FORMAT_DATETIME("%Y%m%d-%H%M%E3S",
        CURRENT_DATETIME())));
EOR
}

resource "google_bigquery_routine" "transfer_s3_data_to_gcs" {
  dataset_id = google_bigquery_dataset.udfs.dataset_id
  routine_id     = "transfer_s3_data_to_gcs"
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
  user_email = (SELECT SESSION_USER());

CALL ${google_bigquery_dataset.udfs.dataset_id}.
      ${google_bigquery_routine.generate_extract_id.routine_id}(extract_id);

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

resource "google_bigquery_routine" "transfer_s3_data_to_bq" {
  dataset_id = google_bigquery_dataset.udfs.dataset_id
  routine_id     = "transfer_s3_data_to_bq"
  routine_type = "PROCEDURE"
  language = "SQL"
  arguments {
    name = "sql_query"
    data_type = "{\"typeKind\": \"STRING\"}"
  }
  arguments {
    name = "destination_dataset_name"
    data_type = "{\"typeKind\": \"STRING\"}"
  }
  arguments {
    name = "destination_table_name"
    data_type = "{\"typeKind\": \"STRING\"}"
  }
  definition_body = <<EOR
DECLARE
  user_email,
  extract_id STRING;
DECLARE
  gcs_bucket STRING DEFAULT('${google_storage_bucket.transfer-jobs.name}');
SET
  user_email = (SELECT SESSION_USER());

CALL ${google_bigquery_dataset.udfs.dataset_id}.
      ${google_bigquery_routine.generate_extract_id.routine_id}(extract_id);

EXPORT DATA
  OPTIONS( uri=CONCAT('gs://', gcs_bucket, '/', extract_id, '/*.json'),
    format='JSON',
    overwrite=TRUE) AS
SELECT
  extract_id
  , sql_query
  , user_email
  , STRUCT(
    destination_dataset_name as dataset_name
    , destination_table_name as table_name
    , @@project_id as project_id
  ) as bq_destination
;

EOR
}