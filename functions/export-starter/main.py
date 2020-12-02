import os

import google.auth
import google.auth.transport.requests
import requests
import six.moves.urllib.parse
import sys
import json
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google.cloud import storage

IAM_SCOPE = 'https://www.googleapis.com/auth/iam'
OAUTH_TOKEN_URI = 'https://www.googleapis.com/oauth2/v4/token'


def trigger_dag(event, context=None):
  bucket = event['bucket']
  file = event['name']

  data = read_gcs_file_content_as_json(bucket, file)

  tenant_project_id = os.environ['TENANT_PROJECT_ID']
  project_id = os.environ['PROJECT_ID']
  location = os.environ['LOCATION']
  composer_env = os.environ['COMPOSER_ENV']

  client_id = get_client_id(project_id, location, composer_env)

  dag_name = 's3-data-export'

  webserver_url = (
      'https://'
      + tenant_project_id
      + '.appspot.com/api/experimental/dags/'
      + dag_name
      + '/dag_runs'
  )
  # Make a POST request to IAP which then Triggers the DAG
  make_iap_request(
      webserver_url, client_id, method='POST', json={"conf": json.dumps(data)})


def read_gcs_file_content_as_json(bucket, file):
  storage_client = storage.Client()
  bucket = storage_client.get_bucket(bucket)
  blob = bucket.get_blob(file)
  json_data = json.loads(blob.download_as_string())
  return json_data

def make_iap_request(url, client_id, method='GET', **kwargs):
  """Makes a request to an application protected by Identity-Aware Proxy.
  Args:
    url: The Identity-Aware Proxy-protected URL to fetch.
    client_id: The client ID used by Identity-Aware Proxy.
    method: The request method to use
            ('GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE')
    **kwargs: Any of the parameters defined for the request function:
              https://github.com/requests/requests/blob/master/requests/api.py
              If no timeout is provided, it is set to 90 by default.
  Returns:
    The page body, or raises an exception if the page couldn't be retrieved.
  """
  # Set the default timeout, if missing
  if 'timeout' not in kwargs:
    kwargs['timeout'] = 90

  # Obtain an OpenID Connect (OIDC) token from metadata server or using service
  # account.
  google_open_id_connect_token = id_token.fetch_id_token(Request(), client_id)

  # Fetch the Identity-Aware Proxy-protected URL, including an
  # Authorization header containing "Bearer " followed by a
  # Google-issued OpenID Connect token for the service account.
  resp = requests.request(
      method, url,
      headers={'Authorization': 'Bearer {}'.format(
          google_open_id_connect_token)}, **kwargs)
  if resp.status_code == 403:
    raise Exception('Service account does not have permission to '
                    'access the IAP-protected application.')
  elif resp.status_code != 200:
    raise Exception(
        'Bad response from application: {!r} / {!r} / {!r}'.format(
            resp.status_code, resp.headers, resp.text))
  else:
    return resp.text


def get_client_id(project_id, location, composer_environment):
  # Authenticate with Google Cloud.
  # See: https://cloud.google.com/docs/authentication/getting-started
  credentials, _ = google.auth.default(
      scopes=['https://www.googleapis.com/auth/cloud-platform'])
  authed_session = google.auth.transport.requests.AuthorizedSession(
      credentials)

  environment_url = (
    'https://composer.googleapis.com/v1beta1/projects/{}/locations/{}'
    '/environments/{}').format(project_id, location, composer_environment)
  composer_response = authed_session.request('GET', environment_url)
  environment_data = composer_response.json()
  airflow_uri = environment_data['config']['airflowUri']

  # The Composer environment response does not include the IAP client ID.
  # Make a second, unauthenticated HTTP request to the web server to get the
  # redirect URI.
  redirect_response = requests.get(airflow_uri, allow_redirects=False)
  redirect_location = redirect_response.headers['location']

  # Extract the client_id query parameter from the redirect.
  parsed = six.moves.urllib.parse.urlparse(redirect_location)
  query_string = six.moves.urllib.parse.parse_qs(parsed.query)
  return query_string['client_id'][0]


if __name__ == "__main__":
  trigger_dag(json.loads(sys.argv[1]))
