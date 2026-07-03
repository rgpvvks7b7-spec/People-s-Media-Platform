DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def structured_windows(listing):
    windows = []
    for item in listing.available_windows or []:
        if not isinstance(item, dict):
            continue
        start = str(item.get("start") or "").strip()
        end = str(item.get("end") or "").strip()
        date = str(item.get("date") or "").strip()
        if date and start and end:
            windows.append({"date": date, "start": start, "end": end, "type": "date"})
            continue
        day = str(item.get("day") or "").strip().lower()[:3]
        if day in DAY_KEYS and start and end:
            windows.append({"day": day, "start": start, "end": end, "type": "weekly"})
    return windows


def time_to_minutes(value):
    hours, minutes = str(value or "0:0").split(":")
    return int(hours) * 60 + int(minutes or 0)


def validate_booking_window(listing, starts_at, ends_at):
    windows = structured_windows(listing)
    if not windows:
        return ""

    if starts_at.date() != ends_at.date():
        return "Booking must start and end on the same host availability day."

    date_windows = [item for item in windows if item.get("type") == "date"]
    if date_windows:
        date_key = starts_at.date().isoformat()
        window = next((item for item in date_windows if item["date"] == date_key), None)
        if not window:
            return f"This venue is not available on {starts_at.strftime('%A %d %b %Y')}."
    else:
        day_key = DAY_KEYS[starts_at.weekday()]
        window = next((item for item in windows if item.get("day") == day_key), None)
        if not window:
            return f"This venue is not available on {starts_at.strftime('%A')}s."

    window_start = time_to_minutes(window["start"])
    window_end = time_to_minutes(window["end"])
    booking_start = starts_at.hour * 60 + starts_at.minute
    booking_end = ends_at.hour * 60 + ends_at.minute

    if booking_start < window_start or booking_end > window_end:
        return f"Choose a time within the host window ({window['start']}–{window['end']})."
    if booking_end <= booking_start:
        return "End time must be after start time."
    return ""
