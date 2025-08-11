import re
import datetime

def parse_nlp_time(text):
    """
    Extracts time from natural language like 'remind me at 5 pm to call mom'
    Returns: (datetime_obj, task)
    """
    match = re.search(r"(\d{1,2}):?(\d{2})?\s*(am|pm)?", text.lower())
    if not match:
        return None, None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    am_pm = match.group(3)

    if am_pm == "pm" and hour != 12:
        hour += 12
    elif am_pm == "am" and hour == 12:
        hour = 0

    reminder_time = datetime.datetime.now().replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    if reminder_time < datetime.datetime.now():
        reminder_time += datetime.timedelta(days=1)

    task = re.sub(r"remind me.*?(am|pm|\d)", "", text, flags=re.I).strip()
    return reminder_time, task
