variable "project_id" {
  type = string
}

variable "composer_env" {
  type = string
  default = "bq-extract-transfer"
}
variable "region" {
  type = string
  default = "us-central1"
}
variable "bigquery_dataset_location" {
  type = string
  default = "us-east1"
}
variable "composer_zone" {
  type = string
  default = "us-central1-c"
}
variable "local_output_path" {
  type = string
  default = "./output"
}
variable "aws_extract_bucket" {
  type = string
}

variable "bq_aws_connection_name" {
  type = string
}

variable "email_from" {
  type = string
}

variable "sendgrid_api_key" {
  type = string
}
