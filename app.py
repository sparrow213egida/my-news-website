from flask import Flask, render_template, request
import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from calendar import monthrange
from dotenv import load_dotenv


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_calendar_events(duration: str, offset: int) -> list[dict] | str:
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        now = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3)))

        if duration == "day":
            start_time = now.replace(hour=0, minute=0, second=0)
            end_time = now.replace(hour=23, minute=59, second=59)
        elif duration == "week":
            days_in_week = 7
            start_time_day = now - datetime.timedelta(days=now.weekday()) + datetime.timedelta(weeks=offset)
            start_time = start_time_day.replace(hour=0, minute=0, second=0)
            end_time_day = (now + datetime.timedelta(days=days_in_week - now.isoweekday())
                            + datetime.timedelta(weeks=offset))
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

        event_colors = ["#9E9E9E", "#7986CB", "#33B679", "#8E24AA", "#E67C73", "#F6C026",
                        "#F5511D", "#039BE5", "#0D904F", "#7B1FA2", "#D23C34", "#616161"]

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            request_ans.append({"start": start, "summary": event["summary"],
                                "color": event_colors[event.get("colorId", 0)]})
        return request_ans

    except HttpError as error:
        return f"An error occurred: {error}"

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


def shift_time_zone(created_at: str) -> str:
    created_at_date_time = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    created_at_date_time += datetime.timedelta(hours=3)
    return datetime.datetime.strftime(created_at_date_time, "%Y-%m-%d %H:%M:%S")


@app.route('/', methods=["GET"])
def main_page():
    cur_offset = request.args.get("offset", default=0, type=int)
    week_events = get_calendar_events("week", cur_offset)

    if type(week_events) == str:
        return render_template("index.html", events=week_events, offset=cur_offset)

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    events = {weekday : [] for weekday in weekdays}
    for event in week_events:
        event_day = datetime.datetime.fromisoformat(event["start"])
        events[weekdays[event_day.weekday()]].append(event)

    return render_template("index.html", events=events, offset=cur_offset)


@app.route('/week')
def week_calendar():
    return get_calendar_events("week", 0)


if __name__ == "__main__":
    app.run(debug=True)
