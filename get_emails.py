import mailbox
import re
import requests
import wget
from glob import glob
import icalendar
import os
import datetime
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from helpers import build_indico_request

SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/calendar.events']

# Path to mailbox file to read emails from and to move after processing
source_mailbox_path = os.path.expanduser('')
dest_mailbox_path = os.path.expanduser('')

# Standard regex string for identifying indico events in email text
url_regex_string = '.*https://indico.cern.ch/event/.*/.*'
url_regex_compiled = re.compile(url_regex_string)

# Path to download indico event .ics file to on your local system
event_file_path = ''
event_regex_string = 'event*.ics'

# ID of your Google calendar
google_calendar_id = ''

# Indico API variables
INDICO_API_KEY = ''
INDICO_SECRET_KEY = ''
INDICO_PARAMS = {
    'limit': 123
}

# Remove event.ics if it exists in the Download folder
try:
    os.remove(event_file_path+'/event.ics')
except:
    pass

source_mailbox = mailbox.mbox(source_mailbox_path)
dest_mailbox = mailbox.mbox(dest_mailbox_path)

# Google Calendar setup taken wholesale from quickstart.py
creds = None
# The file token.pickle stores the user's access and refresh tokens, and is created automatically when the authorization flow completes for the first time
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    #Save the credentials for next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('calendar', 'v3', credentials=creds)

# Loop through emails found in mailbox
for message in source_mailbox:
    # Identify indico link in message body
    body = message.as_string()
    match = url_regex_compiled.search(body)

    # If we don't find an indico link, move to the next email
    if not match:
        print('Following email does not have an indico link')
        print(message['Subject'])
        continue

    # If a link is found, download from the url
    # First extract event number from link
    url = match.group(0)
    print(url)
    event_num_regex = '/[0-9]+/'
    event_num_compiled = re.compile(event_num_regex)
    event_num = event_num_compiled.search(url).group(0)
    event_num = event_num[1:len(event_num)-1]
    print(event_num)
    # THEN CALL BUILD_INDICO_REQUEST
    INDICO_PATH = '/export/event/{}.ics'.format(event_num)
    download_url = build_indico_request(INDICO_PATH, INDICO_PARAMS, INDICO_API_KEY, INDICO_SECRET_KEY)
    print(download_url)
    wget.download(download_url, event_file_path+'/event.ics')
    # Download retrieves an html file and the ics, don't care about the html, so remove it and rename the ics to event.ics
    print('Downloaded {} from email {}'.format(download_url, message['Subject']))

    downloaded_path = event_file_path + '/event.ics'
    g = open(downloaded_path, 'rb')
    c = icalendar.Calendar.from_ical(g.read())
    for component in c.walk():
        if component.name == 'VEVENT':
            file_summary = str(component.get('summary'))
            file_start = str(component.get('dtstart').dt)
            file_end = str(component.get('dtend').dt)
            file_uid = str(component.get('uid'))
            file_description = str(component.get('description'))
            file_location = str(component.get('location'))
            break

    file_start = file_start.replace(' ', 'T')
    file_start = file_start.replace('+00:00', '.000+00:00')
    file_end = file_end.replace(' ', 'T')
    file_end = file_end.replace('+00:00', '.000+00:00')
    event = {
        'summary': file_summary,
        'location': file_location,
        'description': file_description,
        'start': {
            'dateTime': file_start
            },
        'end': {
            'dateTime': file_end
            },
        'iCalUID': file_uid
    }

    import_event = service.events().import_(calendarId=google_calendar_id, body=event).execute()

    dest_mailbox.lock()
    dest_mailbox.add(message)
    dest_mailbox.flush()
    dest_mailbox.unlock()

    os.remove(downloaded_path)

# For some reason, deleting the emails in Thunderbird does not actually delete them from the mailbox file
# To avoid this, delete the mailbox and recreate to ensure only those emails exist that have not been imported yet
os.remove(source_mailbox_path)
new_source_mailbox = mailbox.mbox(source_mailbox_path)

