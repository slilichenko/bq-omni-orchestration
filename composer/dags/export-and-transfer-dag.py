from airflow import models
from airflow.operators import email_operator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators import python_operator
from airflow.contrib.operators import bigquery_operator
from airflow.models import Variable

from datetime import datetime, timedelta

from airflow.contrib.hooks.gcp_transfer_hook import (
  GcpTransferOperationStatus,
  GcpTransferJobsStatus,
  TRANSFER_OPTIONS,
  PROJECT_ID,
  BUCKET_NAME,
  GCS_DATA_SINK,
  STATUS,
  DESCRIPTION,
  START_TIME_OF_DAY,
  SCHEDULE_END_DATE,
  SCHEDULE_START_DATE,
  SCHEDULE,
  AWS_S3_DATA_SOURCE,
  TRANSFER_SPEC,
  ALREADY_EXISTING_IN_SINK,
)
from airflow.contrib.operators.gcp_transfer_operator import (
  GcpTransferServiceJobCreateOperator
)

from airflow.contrib.sensors.gcp_transfer_sensor import GCPTransferServiceWaitForJobStatusSensor
from airflow.utils.dates import days_ago

OP_WAIT_FOR_TRANSFER_COMPLETION = 'wait-for-transfer-to-finish'

TRANSFER_OP_DETAILS_EXPR = 'ti.xcom_pull(\'' \
                           + OP_WAIT_FOR_TRANSFER_COMPLETION + '\', ' \
                                    'key=\'sensed_operations\')' \
                           '[0][\'metadata\']'
USER_EMAIL_EXPR = '{{ dag_run.conf["user_email"] }}'
EXTRACT_ID_EXPR = '{{ dag_run.conf["extract_id"] }}'
DESTINATION_FOLDER_EXPR = '{{ dag_run.conf["destination_folder"] }}'
SQL_EXPR = '{{ dag_run.conf["sql_query"] }}'

WAIT_FOR_OPERATION_POKE_INTERVAL = 5

utcnow = datetime.utcnow()
run_date = utcnow.date()
run_time = (utcnow + timedelta(minutes=2)).time()
if(run_time < utcnow.time()):
  # Handle the case where +2 minutes moves the clock in the new day
  run_date = (utcnow + timedelta(days=1)).date()

transfer_jobs_project_id = Variable.get('TRANSFER_JOBS_PROJECT_ID')

aws_to_gcs_transfer_body = {
  DESCRIPTION: 'Transfer of BQ Extract ' + EXTRACT_ID_EXPR,
  STATUS: GcpTransferJobsStatus.ENABLED,
  PROJECT_ID: transfer_jobs_project_id,
  SCHEDULE: {
    SCHEDULE_START_DATE: run_date,
    SCHEDULE_END_DATE: run_date,
    START_TIME_OF_DAY: run_time,
  },
  TRANSFER_SPEC: {
    AWS_S3_DATA_SOURCE: {BUCKET_NAME: Variable.get('DATA_EXTRACT_AWS_BUCKET')},
    GCS_DATA_SINK: {BUCKET_NAME: Variable.get('DATA_EXTRACT_GCS_BUCKET')},
    TRANSFER_OPTIONS: {
      ALREADY_EXISTING_IN_SINK: True,
      "deleteObjectsFromSourceAfterTransfer": True
    },
    "objectConditions": {
      "includePrefixes": [DESTINATION_FOLDER_EXPR + '/']
    }
  },
}

def report_failure(context):
  send_email = email_operator.EmailOperator(
      task_id="failure",
      to=USER_EMAIL_EXPR,
      start_date=days_ago(1),
      subject='Data extract and transfer job failed - ' + EXTRACT_ID_EXPR,
      html_content='email-template/transfer-failure.html'
  )

  # Set DAG, otherwise we will get errors
  send_email.dag = context['dag']

  # Manually render templates
  # template_env = send_email.get_template_env()
  # send_email.html_content = template_env.from_string(send_email.html_content).render(**context)
  # send_email.to = template_env.from_string(send_email.to).render(**context)
  # send_email.subject = template_env.from_string(send_email.subject).render(**context)

  send_email.render_template_fields(context=context)

  send_email.execute(context)

# We set the start_date of the DAG to the previous date. This will
# make the DAG immediately available for scheduling.
DEFAULT_DAG_ARGS = {
  'start_date': days_ago(1)
}

def validate_request(**context):
  # TODO: add real validation
  print("Context conf", context['dag_run'].conf)

def check_transfer_status_function(**context):
  ti = context['ti']
  transfer_status = ti.xcom_pull(task_ids=OP_WAIT_FOR_TRANSFER_COMPLETION,
                                 key='sensed_operations')[0]['metadata']['status']
  if transfer_status == 'SUCCESS':
    return 'success-notification'
  else:
    return 'failure-notification'

# Setting schedule_interval to None as this DAG is externally triggered by
# a Cloud Function
with models.DAG(dag_id='bq-data-export',
                description='BigQuery Data Export and Transfer to GCS',
                schedule_interval=None, default_args=DEFAULT_DAG_ARGS) as dag:
  validation = python_operator.PythonOperator(task_id='validate-request',
                                              python_callable=validate_request,
                                              provide_context=True)

  start_notification = email_operator.EmailOperator(
    task_id='start-notification',
    to=USER_EMAIL_EXPR,
    subject='Data extract and transfer job started - ' + EXTRACT_ID_EXPR,
    html_content="email-template/transfer-start.html")

  success_notification = email_operator.EmailOperator(
      task_id='success-notification',
      to=USER_EMAIL_EXPR,
      subject='Data extract and transfer job completed - ' + EXTRACT_ID_EXPR,
      html_content="email-template/transfer-completion.html"
      )

  bigquery_export = bigquery_operator.BigQueryOperator(
      task_id='bigquery-export',
      sql=(
          # TODO: replace with AWS specific extract.
          'EXPORT DATA OPTIONS(' +
           'uri=\'gs://bq-omni-sa-demo-296222-transfer-jobs/'
           + EXTRACT_ID_EXPR +
           '/*.avro\',' +
           'format=\'avro\','
           'overwrite=true) AS ' +
           SQL_EXPR),
      use_legacy_sql=False,
      on_failure_callback=report_failure
  )

  create_transfer_job_from_aws = GcpTransferServiceJobCreateOperator(
      task_id='create-transfer-job',
      body=aws_to_gcs_transfer_body,
      aws_conn_id='aws-bucket-conn',
      on_failure_callback=report_failure
  )

  wait_for_operation_to_end = GCPTransferServiceWaitForJobStatusSensor(
      task_id=OP_WAIT_FOR_TRANSFER_COMPLETION,
      job_name="{{task_instance.xcom_pull('create-transfer-job')['name']}}",
      project_id=transfer_jobs_project_id,
      expected_statuses={GcpTransferOperationStatus.SUCCESS,
                         GcpTransferOperationStatus.FAILED,
                         GcpTransferOperationStatus.ABORTED},
      poke_interval=WAIT_FOR_OPERATION_POKE_INTERVAL,
      on_failure_callback=report_failure
  )

  check_transfer_status = BranchPythonOperator(
      task_id="check-transfer-status",
      provide_context=True,
      python_callable=check_transfer_status_function,
      on_failure_callback=report_failure
  )

  start_notification \
  >> validation \
  >> bigquery_export \
  >> create_transfer_job_from_aws \
  >> wait_for_operation_to_end \
  >> check_transfer_status \
  >> success_notification