# Using BigQuery Omni to Selectively Transfer Data from AWS or Azure to GCP

This is a fully functional demo to show how BigQuery Omni can be used to transfer data from another cloud to GCP.

## Overview
This diagram describes how the overall solution works:
![Solution Diagram](/docs/BigQuery%20Omni%20Selective%20Migration.svg)

Users initiate the transfer process by providing SQL query to run and specify whether the result
needs to be transferred to a GCS bucket or stored in a BigQuery table. Cloud Composer executes
the workflow shown below:

![Workflowo Diagram](/docs/Transfer%20Workflow.png)

## BigQuery Omni Setup
Before you can run the demo you would need to [set up BigQuery Omni on AWS](https://cloud.google.com/bigquery-omni/docs/aws/create-connection) (currently the Terraform scripts don't
automatically provision the AWS portion of the demo).

Besides the connection to query the data and the table to query also create an S3 bucket to be used for data export and an additional
connection to be used for data export process. That connection need to be associated with a policy which allows writes to the output bucket:
```.env
...        
{
    "Effect": "Allow",
    "Action": [
        "s3:PutObject"
    ],
    "Resource": "arn:aws:s3:::output-bucket-name/*"
}
...
```

## Deploying GCP components
All the resources in GCP are created using Terraform. We recommend creating a new project for the ease of cleaning up.

### Get SendGrid API key
The workflow sends an email to the user who initiated the transfer in the beginning of the workflow and when the workflow is completed (either successfully or failed).
In order to receive these emails create a SendGrid account and create an API key using [this process](https://cloud.google.com/composer/docs/how-to/managing/creating#configuring_sendgrid_email_services).

### Create Terraform variables file
[Terraform variables](https://www.terraform.io/docs/configuration/variables.html) are used to customize the deployment. 
You can provide them on the command line or through environment variables, but the easiest way is to create a file in `terraform` directory. 
`terraform.tfvars` is the default and will be automatically used.
An example of such a file:
```hcl-terraform
project_id = "project-id"
aws_extract_bucket = "s3-extract-bucket"
bq_aws_connection_name = "aws-us-east-1.aws-s3-connection"
email_from = "'Data Extract Notifications'<data.extract.notification@example.com>"
sendgrid_api_key = "api-key"
``` 
All the variables and their defaults are defined in [variables.tf](terraform/variables.tf).

### Deploy
```.env
cd terraform
terraform init
terraform apply
```

### Create AWS Credentials
Follow [Storage Transfer Service instructions](https://cloud.google.com/storage-transfer/docs/configure-access#amazon-s3)
on how to create a pair of access/secret key pair. You will need to use them to configure Composer in the next step.

### Configuring Cloud Composer
Once the Cloud Composer instance is running it needs to be configured to [create AWS Connection](https://cloud.google.com/composer/docs/how-to/managing/connections) to
the export bucket (used by Storage Data Transfer):
* Go to the Composer Airflow Webserver UI
* Select Admin -> Connections -> Create
* Parameters:
  * Conn Id = aws-bucket-conn
  * Conn Type = S3
  * Login = \<AWS access key\>
  * Password = \<AWS secret key\>

## Running data transfers
Three are several BigQuery stored procedures that are created by the Terraform script. They are located in `udfs` dataset.
Two of them are meant to be executed by the end users.

### Transferring data to a GCS bucket
Prepare your query and execute:
```.sql
DECLARE sql_query STRING DEFAULT "SELECT col1, col2 FROM myproject.aws_dataset.table1 WHERE col3 = 'my criteria'";
DECLARE destination_folder STRING DEFAULT 'extract-123';
CALL `myproject.udfs.transfer_s3_data_to_gcs`(sql_query, destination_folder);
```
### Transferring data to a BigQuery table
Prepare your query and execute:
```sql
DECLARE sql_query STRING DEFAULT "SELECT col1, col2 FROM myproject.aws_dataset.table1 WHERE col3 = 'my criteria'";
DECLARE destination_dataset_name STRING DEFAULT 'gcp_dataset';
DECLARE destination_table_name STRING DEFAULT 'extracted_data';
CALL `bq-omni-sa-demo-296222.udfs.transfer_s3_data_to_bq`(sql_query, destination_dataset_name, destination_table_name);
```
### Other ways to run transfers
The transfer workflows can also be started by:
* Calling stored procedures from `bq` CLI or via BigQuery APIs
* Triggering Cloud Composer workflow programmatically (see [export starter](functions/export-starter) function)
* Triggering Cloud Composer manually from the Composer UI.

## Cleaning up
If you created a separate project to run this demo - delete the project.

If you deployed in an existing project:
```.env
terraform destroy
```