import datetime
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import caldav
import environs

my_tz = ZoneInfo("America/New_York")

env = environs.Env()
environs.Env.read_env()

logging.basicConfig(level=env("LOG_LEVEL", "INFO"))  # Set the desired logging level

# TODO: There is a potential issue if the script runs at the same time as tuckers software is updating the calendar
#  as the script would delete all events that are not in the source calendar.
#  This would be resolved the next time the script runs though.


def sync_calendar(src_cal, dest_cal):
    # Fetch all events from both calendars
    src_events = [
        event
        for event in src_cal.events()
        if event.vobject_instance.vevent.dtstart.value >= datetime.now(tz=my_tz)
    ]
    dest_events = [
        event
        for event in dest_cal.events()
        if event.vobject_instance.vevent.dtstart.value >= datetime.now(tz=my_tz)
    ]

    # Create dictionaries for quick lookup
    src_event_dict = {
        event.vobject_instance.vevent.uid.value: event for event in src_events
    }
    dest_event_dict = {
        event.vobject_instance.vevent.uid.value: event for event in dest_events
    }

    # 1. Remove any events that are not in the SRC calendar
    for uid, dest_event in dest_event_dict.items():
        if uid not in src_event_dict:
            logging.info("Deleting event: %s", dest_event)
            dest_event.delete()

    # 2. Check for updates to existing events
    for uid, src_event in src_event_dict.items():
        if uid in dest_event_dict:
            dest_event = dest_event_dict[uid]
            src_vevent = src_event.vobject_instance.vevent
            dest_vevent = dest_event.vobject_instance.vevent

            # Check if the event has changed
            if (
                src_vevent.contents["last-modified"]
                != dest_vevent.contents["last-modified"]
            ) and (src_vevent.contents["summary"] != dest_vevent.contents["summary"]):
                logging.info("Updating event: %s", src_event)
                dest_event.delete()
                dest_cal.add_event(src_event.data)

    # 3. Add any new events from the SRC calendar to the DEST calendar
    for uid, src_event in src_event_dict.items():
        if uid not in dest_event_dict:
            logging.info("Adding event: %s", src_event)
            dest_cal.add_event(src_event.data)


with caldav.DAVClient(
    url="https://caldav.icloud.com",
    username=env("USER_NAME"),
    password=env("PASSWD"),
) as client:
    my_principal = client.principal()

    calendars = my_principal.calendars()
    logging.info("Filtering calendars")
    work_cal = [c for c in calendars if c.name == env("SRC_CAL")][0]
    family_cal = [c for c in calendars if c.name == env("DEST_CAL")][0]
    logging.info("Syncing calendars")
    sync_calendar(work_cal, family_cal)
