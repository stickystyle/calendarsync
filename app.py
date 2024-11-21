import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from icalevents.icalevents import events
import caldav
import environs

my_tz = ZoneInfo("America/New_York")

env = environs.Env()
environs.Env.read_env()

logging.basicConfig(level=env("LOG_LEVEL", "INFO"))  # Set the desired logging level

# TODO: There is a potential issue if the script runs at the same time as tuckers software is updating the calendar
#  as the script would delete all events that are not in the source calendar.
#  This would be resolved the next time the script runs though.


def sync_calendar(src_events_dict, dest_events_dict, destination_cal):

    # Remove any events that are not in the SRC calendar
    for event_id, dest_event in dest_events_dict.items():
        if event_id not in src_event_dict:
            logging.info("Deleting event: %s", dest_event)
            dest_event.delete()

    # Add any new events from the SRC calendar to the DEST calendar
    for event_id, src_event in src_events_dict.items():
        if event_id not in dest_event_dict:
            logging.info("Adding event: %s", src_event)
            destination_cal.add_event(src_event.component.to_ical())


with caldav.DAVClient(
    url="https://caldav.icloud.com",
    username=env("USER_NAME"),
    password=env("PASSWD"),
) as client:
    now = datetime.now(my_tz)
    src_events = events(
        env("SRC_CAL"), fix_apple=True, sort=True, end=now + timedelta(days=21)
    )
    src_event_dict = {
        f"{event.summary}-{event.start.isoformat()}-{event.end.isoformat()}": event
        for event in src_events
    }

    my_principal = client.principal()
    calendars = my_principal.calendars()

    logging.info("Filtering calendars")
    dest_cal = [c for c in calendars if c.name == env("DEST_CAL")][0]
    dest_events = [
        event
        for event in dest_cal.events()
        if event.vobject_instance.vevent.dtstart.value >= datetime.now(tz=my_tz)
    ]

    dest_event_dict = {
        f"{event.vobject_instance.vevent.summary.value}-{event.vobject_instance.vevent.dtstart.value.isoformat()}-{event.vobject_instance.vevent.dtend.value.isoformat()}": event
        for event in dest_events
    }

    logging.info("Syncing calendars")
    sync_calendar(src_event_dict, dest_event_dict, dest_cal)
