from flask import Flask, render_template, request
import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_calendar_events(offset: int) -> list[dict] | str:
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

        days_in_week = 7
        start_time_day = now - datetime.timedelta(days=now.weekday()) + datetime.timedelta(weeks=offset)
        start_time = start_time_day.replace(hour=0, minute=0, second=0)
        end_time_day = (now + datetime.timedelta(days=days_in_week - now.isoweekday())
                        + datetime.timedelta(weeks=offset))
        end_time = end_time_day.replace(hour=23, minute=59, second=59)

        if app.calendar_list == '':
            calendars = []
        else:
            calendars = app.calendar_list.split(',')

        events = []

        for calendar in calendars:
            events_result = service.events().list(calendarId=calendar,
                                                   timeMin=start_time.isoformat(),
                                                   timeMax=end_time.isoformat(),
                                                   singleEvents=True,
                                                   orderBy="startTime").execute()
            events += events_result.get("items", [])

        if not events:
            return []

        request_ans = []

        event_colors = {"0": "#9E9E9E", "1": "#A4BDFC", "2": "#7AE7BF", "3": "#DBADFF", "4": "#FF887C",
                         "5": "#FBD75B", "6": "#FFB878", "7": "#46D6DB", "8": "#E1E1E1", "9": "#5484ED",
                         "10": "#51B749", "11": "#DC2127", "12": "#FFADAD", "13": "#FFD6A5", "14": "#FDFFB6",
                         "15": "#CAFFBF", "16": "#9BF6FF", "17": "#A0C4FF", "18": "#BDB2FF", "19": "#FFC6FF",
                         "20": "#E74C3C", "21": "#F39C12", "22": "#F1C40F", "23": "#2ECC71", "24": "#1ABC9C",
                         "25": "#3498DB", "26": "#9B59B6", "27": "#E84393", "28": "#8D6F47", "29": "#95A5A6",
                         "30": "#4E5D6C", "31": "#865A5A", "32": "#2C3E50"}

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            request_ans.append({"start": start, "end": end, "summary": event["summary"],
                                "color": event_colors[event.get("colorId", "0")]})
        return request_ans

    except HttpError as error:
        return f"An error occurred: {error}"

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.calendar_list = os.getenv("CALENDAR_ID_LIST", "primary")
app.credentials_contents = os.getenv("CREDENTIALS_CONTENTS")
app.token_contents = os.getenv("TOKEN_CONTENTS")

if app.credentials_contents != '':
    with open("credentials.json", "w") as credentials_file:
        credentials_file.write(app.credentials_contents)

if app.token_contents != '':
    with open("token.json", "w") as token_file:
        token_file.write(app.token_contents)


def shift_time_zone(created_at: str) -> str:
    created_at_date_time = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    created_at_date_time += datetime.timedelta(hours=3)
    return datetime.datetime.strftime(created_at_date_time, "%Y-%m-%d %H:%M:%S")


def get_week_info(offset: int) -> tuple[str, str]:
    now = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3)))

    offset_date = now + datetime.timedelta(weeks=offset)

    week_start = offset_date - datetime.timedelta(days=now.weekday())
    week_end = week_start + datetime.timedelta(days=6)

    return (datetime.datetime.strftime(week_start, "%d.%m.%Y"),
            datetime.datetime.strftime(week_end, "%d.%m.%Y"))


@app.route('/', methods=["GET"])
def main_page():
    cur_offset = request.args.get("offset", default=0, type=int)
    week_events = get_calendar_events(cur_offset)

    week_start, week_end = get_week_info(cur_offset)

    if type(week_events) == str:
        return render_template("index.html", grid=[], offset=cur_offset,
                               week_start = week_start, week_end = week_end)

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    events = {weekday : [] for weekday in weekdays}
    for event in week_events:
        event_start = datetime.datetime.fromisoformat(event["start"])
        events[weekdays[event_start.weekday()]].append(event)

    grid = []
    for weekday in weekdays:
        day_events = events[weekday]
        day_column = [{} for _ in range(16 * 12)]

        for event in day_events:
            event_start = datetime.datetime.fromisoformat(event["start"])
            start_period_number = (event_start.hour - 8) * 12 + event_start.minute // 5

            event_end = datetime.datetime.fromisoformat(event["end"])
            end_period_number = (event_end.hour - 8) * 12 + event_end.minute // 5

            if event_start.hour >= 8:
                for period in range(start_period_number, end_period_number):
                    day_column[period] = {"event_info": event,
                                      "start_period": start_period_number, "end_period": end_period_number}

        grid.append(day_column)

    return render_template("index.html", grid=grid, offset=cur_offset,
                           week_start=week_start, week_end = week_end)


if __name__ == "__main__":
    app.run(debug=True)
