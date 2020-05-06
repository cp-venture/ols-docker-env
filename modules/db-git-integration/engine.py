import pandas as pd
import json

from google.oauth2 import service_account
from apiclient import discovery

CREDENTIALS_FILE_PATH = './cp-venture-276b42c80e37.json'
# SCOPES = []
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE_PATH)
service = discovery.build('drive', 'v3', credentials=credentials)
a = service.about()


print(a.get().execute())