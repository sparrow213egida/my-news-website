from flask import Flask, render_template, request
import datetime
import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly",
          "https://www.googleapis.com/auth/tasks.readonly"]

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.calendar_list = os.getenv("CALENDAR_ID_LIST", "primary")
app.credentials_contents = os.getenv("CREDENTIALS_CONTENTS")
app.token_contents = os.getenv("TOKEN_CONTENTS")
app.tasklist = os.getenv("TASKLIST_ID")

if app.credentials_contents:
    with open("credentials.json", "w") as credentials_file:
        credentials_file.write(app.credentials_contents)

if app.token_contents:
    with open("token.json", "w") as token_file:
        token_file.write(app.token_contents)


def get_calendar_events(offset: int) -> dict[str, list[dict]] | str:
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service_calendar = build("calendar", "v3", credentials=creds)
        service_tasks = build("tasks", "v1", credentials=creds)

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
        label_ids = {}

        for calendar in calendars:
            calendar_labels = (
                service_calendar.calendars().get(calendarId=calendar).execute())["labelProperties"]["eventLabels"]

            for label in calendar_labels:
                label_ids[label["id"]] = label["backgroundColor"]

            shifted_start_time = start_time + datetime.timedelta(hours=3)
            shifted_end_time = end_time + datetime.timedelta(hours=3)
            events_result = service_calendar.events().list(calendarId=calendar,
                                                           timeMin=shifted_start_time.isoformat(),
                                                           timeMax=shifted_end_time.isoformat(),
                                                           singleEvents=True,
                                                           orderBy="startTime").execute()
            events += events_result.get("items", [])

        calendar_request_ans = []

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))

            event_color = "#87CEFA"

            if event.get("eventLabelId", 0) != 0:
                event_color = label_ids[event["eventLabelId"]]

            calendar_request_ans.append({"start": start, "end": end, "summary": event["summary"],
                                         "color": event_color})

        print(start_time.isoformat())
        print(end_time.isoformat())
        first_list = service_tasks.tasks().list(tasklist=app.tasklist).execute()["items"]
        for event in first_list:
            print(event)

        tasks_list = service_tasks.tasks().list(tasklist=app.tasklist,
                                                dueMin=start_time.isoformat(),
                                                dueMax=end_time.isoformat(),
                                                showCompleted=True,
                                                showHidden=True).execute()["items"]

        tasks_request_ans = []

        for task in tasks_list:
            tasks_request_ans.append({"title": task["title"], "due": task["due"], "status": task["status"]})

        return {"calendar_ans": calendar_request_ans, "task_ans": tasks_request_ans}

    except HttpError as error:
        return f"An error occurred: {error}"


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
    events_and_tasks = get_calendar_events(cur_offset)

    week_events = events_and_tasks["calendar_ans"]

    week_start, week_end = get_week_info(cur_offset)

    if type(week_events) == str:
        return render_template("index.html", grid=[], offset=cur_offset,
                               week_start=week_start, week_end=week_end)

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    events = {weekday: [] for weekday in weekdays}
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

    week_tasks = events_and_tasks["task_ans"]
    tasks = [[] for _ in range(7)]

    for task in week_tasks:
        deadline = datetime.datetime.fromisoformat(task["due"])
        tasks[deadline.weekday()].append(task)

    max_task_count = max(len(task_list) for task_list in tasks)

    return render_template("index.html", grid=grid, offset=cur_offset,
                           week_start=week_start, week_end=week_end, tasks=tasks,
                           max_task_count=max_task_count)


if __name__ == "__main__":
    app.run(debug=True)
