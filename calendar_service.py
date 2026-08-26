import datetime
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import SCOPES

def get_todays_google_meet_link() -> str:
    """Authenticates with Google Calendar and fetches the Meet link for today's 7 PM session."""
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if os.path.exists('credentials.json'):
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                else:
                    return "https://meet.google.com/rgx-ysrj-heo"

        service = build('calendar', 'v3', credentials=creds)

        now = datetime.datetime.utcnow()
        start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0).isoformat() + 'Z'
        end_of_day = datetime.datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', '').lower()
            
            if '19:00' in start or 'discussion' in summary or 'class' in summary or 'mock' in summary:
                meet_link = event.get('hangoutLink')
                if meet_link:
                    print(f"Found Google Meet Link from Calendar event '{event.get('summary')}': {meet_link}")
                    return meet_link

    except Exception as e:
        print(f"Calendar fetch error: {e}")

    return "https://meet.google.com/rgx-ysrj-heo"