import dateparser
import datetime
import re

def parse_nlp_time(text):
    """
    Extract reminder time and task from a natural language string.
    Example input: "remind me tomorrow at 5 pm to call mom"
    
    Returns:
      - datetime object of reminder time (or None)
      - task string (or None)
    """
    # Try to extract the date/time phrase
    # Assume the format "remind me <time phrase> to <task>"
    pattern = r"remind me (.+?) to (.+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None, None
    
    time_str = match.group(1).strip()
    task = match.group(2).strip()

    # Parse the time string using dateparser
    reminder_time = dateparser.parse(time_str, settings={'PREFER_DATES_FROM': 'future'})
    
    # If time parsing fails
    if not reminder_time:
        return None, None
    
    # If reminder time is in the past, push to next day
    now = datetime.datetime.now()
    if reminder_time < now:
        reminder_time += datetime.timedelta(days=1)
    
    return reminder_time, task
