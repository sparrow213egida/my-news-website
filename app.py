from flask import Flask, render_template
import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from calendar import monthrange

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_calendar_events(duration: str) -> list[dict] | str:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3)))
        if duration == "day":
            start_time = now.replace(hour=0, minute=0, second=0)
            end_time = now.replace(hour=23, minute=59, second=59)
        elif duration == "week":
            days_in_week = 7
            start_time_day = now - datetime.timedelta(days=now.weekday())
            start_time = start_time_day.replace(hour=0, minute=0, second=0)
            end_time_day = now + datetime.timedelta(days=days_in_week - now.isoweekday())
            end_time = end_time_day.replace(hour=23, minute=59, second=59)
        elif duration == "month":
            start_time = now.replace(day=1, hour=0, minute=0, second=0)
            days_in_month = monthrange(now.year, now.month)[1]
            end_time = now.replace(day=days_in_month, hour=23, minute=59, second=59)
        else:
            return "An error occurred: wrong duration selected"

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            return []

        request_ans = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            request_ans.append({"start": start, "summary": event["summary"]})
        return request_ans

    except HttpError as error:
        return f"An error occurred: {error}"

app = Flask(__name__)

@app.route('/')
def main_page():
    day_events = get_calendar_events("day")
    week_events = get_calendar_events("week")
    month_events = get_calendar_events("month")
    events = {"day": day_events, "week": week_events, "month": month_events}
    return render_template("index.html", events=events)

@app.route('/day')
def day_calendar():
    return get_calendar_events("day")

@app.route('/week')
def week_calendar():
    return get_calendar_events("week")

@app.route('/month')
def month_calendar():
    return get_calendar_events("month")

if __name__ == "__main__":
    app.run(debug=True)