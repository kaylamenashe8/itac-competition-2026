from automation_infra.core.api.arena_api_client import get

SEATS = "/events/{event_id}/seats"


def get_seat_status(base_url: str, event_id: str, api_key: str = None):
    return get(base_url, SEATS.format(event_id=event_id), api_key)["seats"]


def find_available_seats(base_url: str, event_id: str, count: int, api_key: str = None):
    seats = get_seat_status(base_url, event_id, api_key)
    available = [seat["seat_id"] for seat in seats if seat["status"] == "available"]
    if len(available) < count:
        raise ValueError(f"Not enough seats >> {len(available)} available seats for event {event_id}, but {count} was requested")
    return available[:count]
