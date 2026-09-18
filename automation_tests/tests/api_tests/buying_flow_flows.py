from datetime import datetime, timezone

from automation_infra.core.api.buying_flow import book_seats
from automation_infra.core.api.catalog import get_events
from automation_infra.core.api.seats import get_seat_status

COUNT = 2


def is_upcoming(event: dict) -> bool:
    starts_at = datetime.fromisoformat(event["starts_at"].replace("Z", "+00:00"))
    return starts_at > datetime.now(timezone.utc)


def get_upcoming_events(base_url: str, api_key: str = None) -> list[dict]:
    events = get_events(base_url, api_key)["items"]
    return [event for event in events if is_upcoming(event)]


def available_seat_ids(base_url: str, event_id: str, api_key: str = None) -> list[str]:
    seats = get_seat_status(base_url, event_id, api_key)
    return [seat["seat_id"] for seat in seats if seat["status"] == "available"]


def unavailable_seat_ids(base_url: str, event_id: str, api_key: str = None) -> list[str]:
    seats = get_seat_status(base_url, event_id, api_key)
    return [seat["seat_id"] for seat in seats if seat["status"] != "available"]


def book_only_available_seats(base_url: str, api_key: str = None):
    for event in get_upcoming_events(base_url, api_key):
        seat_ids = available_seat_ids(base_url, event["id"], api_key)[:COUNT]
        if seat_ids:
            book_seats(base_url, event["id"], seat_ids, api_key)


def book_only_unavailable_seats(base_url: str, api_key: str = None):
    for event in get_upcoming_events(base_url, api_key):
        seat_ids = unavailable_seat_ids(base_url, event["id"], api_key)[:COUNT]
        if seat_ids:
            book_seats(base_url, event["id"], seat_ids, api_key)


def book_mixed_available_and_unavailable_seats(base_url: str, api_key: str = None):
    half = COUNT // 2
    for event in get_upcoming_events(base_url, api_key):
        seat_ids = (
            available_seat_ids(base_url, event["id"], api_key)[:half]
            + unavailable_seat_ids(base_url, event["id"], api_key)[:COUNT - half]
        )
        if len(seat_ids) == COUNT:
            book_seats(base_url, event["id"], seat_ids, api_key)
