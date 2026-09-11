#!/usr/bin/env python3
"""
Fetch the group's public Google Calendar feed and write events.json.

Run by .github/workflows/calendar.yml on a schedule. The website reads
events.json directly, so visitors never contact Google and no cookies are set.

To point this at a different calendar, change CALENDAR_ID below.
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events

CALENDAR_ID = "89e77a42702e3c17c4758e949b02ee768225794c6403771b40d170dc15a7b87b%40group.calendar.google.com"
FEED = f"https://calendar.google.com/calendar/ical/{CALENDAR_ID}/public/basic.ics"

TZ = ZoneInfo("America/Los_Angeles")
DAYS_AHEAD = 120          # how far forward to look
MAX_EVENTS = 12           # how many to show on the page
OUT = "events.json"


def fmt_date(dt):
    # "Tue, Oct 7" — no year unless it's a different one from today
    s = dt.strftime("%a, %b %-d")
    if dt.year != datetime.now(TZ).year:
        s += dt.strftime(", %Y")
    return s


def fmt_time(start, end):
    t = start.strftime("%-I:%M%p").lower().replace(":00", "")
    if end and end != start:
        t += "–" + end.strftime("%-I:%M%p").lower().replace(":00", "")
    return t


def main():
    try:
        req = urllib.request.Request(FEED, headers={"User-Agent": "ea-ucsd-site/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except Exception as e:
        # Never overwrite good data with nothing if Google is having a bad day.
        print(f"Could not fetch the feed: {e}", file=sys.stderr)
        return 1

    cal = icalendar.Calendar.from_ical(raw)
    start = datetime.now(TZ)
    occurrences = recurring_ical_events.of(cal).between(start, start + timedelta(days=DAYS_AHEAD))

    events = []
    for ev in occurrences:
        s = ev.get("DTSTART").dt
        e = ev.get("DTEND").dt if ev.get("DTEND") else None

        all_day = not isinstance(s, datetime)
        if all_day:
            s_local = datetime(s.year, s.month, s.day, tzinfo=TZ)
            e_local = None
        else:
            s_local = s.astimezone(TZ)
            e_local = e.astimezone(TZ) if isinstance(e, datetime) else None

        events.append({
            "iso": s_local.isoformat(),
            "date": fmt_date(s_local),
            "time": "All day" if all_day else fmt_time(s_local, e_local),
            "title": str(ev.get("SUMMARY", "Untitled event")),
            "location": str(ev.get("LOCATION", "")).strip(),
        })

    events.sort(key=lambda x: x["iso"])
    events = events[:MAX_EVENTS]

    payload = {
        "updated": datetime.now(TZ).isoformat(timespec="minutes"),
        "events": events,
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(f"Wrote {len(events)} events to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
