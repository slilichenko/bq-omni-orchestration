"""A simple Airflow DAG that is triggered externally by a Cloud Function when a
file lands in a GCS bucket.
Once triggered the DAG performs the following steps:
1. Triggers a Google Cloud Dataflow job with the input file information received
   from the Cloud Function trigger.
2. Upon completion of the Dataflow job, the input file is moved to a
   gs://<target-bucket>/<success|failure>/YYYY-MM-DD/ location based on the
   status of the previous step.
"""

import datetime

from airflow import models
from airflow.operators import email_operator
from airflow.operators import python_operator
from airflow.contrib.operators import bigquery_operator

# We set the start_date of the DAG to the previous date. This will
# make the DAG immediately available for scheduling.
USER_EMAIL_EXPR = '{{ dag_run.conf["user_email"] }}'
EXTRACT_ID_EXPR = '{{ dag_run.conf["extract_id"] }}'
SQL_EXPR = '{{ dag_run.conf["sql_query"] }}'

YESTERDAY = datetime.datetime.combine(
    datetime.datetime.today() - datetime.timedelta(1),
    datetime.datetime.min.time())

DS_TAG = '{{ ds }}'

DEFAULT_DAG_ARGS = {
  'start_date': YESTERDAY
}

def validate_request(**context):
  print("Context conf", context['dag_run'].conf)

# Setting schedule_interval to None as this DAG is externally triggered by
# a Cloud Function
with models.DAG(dag_id='s3-data-export',
                description='An S3 Export to GCS',
                schedule_interval=None, default_args=DEFAULT_DAG_ARGS) as dag:
  validation = python_operator.PythonOperator(task_id='validate-request',
                                              python_callable=validate_request,
                                              provide_context=True)

  start_notification = email_operator.EmailOperator(
    task_id='start-notification',
    to=USER_EMAIL_EXPR,
    subject='S3 to GCS extract job start',
    html_content="""
        Starting export job.
        """.format())

  success_notification = email_operator.EmailOperator(
      task_id='success-notification',
      to=USER_EMAIL_EXPR,
      subject='S3 to GCS extract job completion',
      html_content="""
        Processed the transfer
        """.format())

  failure_notification = email_operator.EmailOperator(
      trigger_rule='one_failed',
      task_id='failure-notification',
      to=USER_EMAIL_EXPR,
      subject='S3 to GCS extract job failure',
      html_content="""
        Failed to process the transfer
        """.format(
          # min_date=min_query_date,
          # max_date=max_query_date,
          # question_title=(
          #   '{{ ti.xcom_pull(task_ids=\'bq_read_most_popular\', '
          #   'key=\'return_value\')[0][0] }}'
          # ),
          # view_count=(
          #   '{{ ti.xcom_pull(task_ids=\'bq_read_most_popular\', '
          #   'key=\'return_value\')[0][1] }}'
          # ),
          # export_location=output_file
      ))

  bigquery_export = bigquery_operator.BigQueryOperator(
      task_id='bigquery-export',
      sql=(
          'EXPORT DATA OPTIONS(' +
           'uri=\'gs://bq-omni-sa-demo-296222-transfer-jobs/'
           + EXTRACT_ID_EXPR +
           '/*.avro\',' +
           'format=\'avro\','
           'overwrite=true) AS ' +
           SQL_EXPR),
      use_legacy_sql=False
  )

  start_notification \
  >> validation \
  >> bigquery_export \
  >> success_notification

  [validation, bigquery_export] >> failure_notification
