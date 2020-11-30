variable "project_id" {
  type = string
}

variable "composer_env" {
  type = string
  default = "bq-omni-demo"
}
variable "region" {
  type = string
  default = "us-central1"
}
variable "composer_zone" {
  type = string
  default = "us-central1-c"
}
variable "local_output_path" {
  type = string
  default = "./output"
}