from datetime import datetime, timezone
import json


def ns_to_day(ts_ns):
    dt = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)
    return dt.strftime("%Y/%m/%d")


def make_enriched_event_key(vehicle_event_key: str) -> str:
    """
    Convert:
    vehicle_events/YYYY/MM/DD/<event_id>.json
    →
    enriched_events/YYYY/MM/DD/<event_id>.json
    """

    if not vehicle_event_key.startswith("vehicle_events/"):
        raise ValueError(f"Unexpected vehicle event key: {vehicle_event_key}")

    return vehicle_event_key.replace("vehicle_events/", "enriched_events/", 1)

def make_original_event_key(enriched_key: str) -> str:
    return enriched_key.replace("enriched_events/", "vehicle_events/", 1)


def save_enriched_event(storage, vehicle_event_key: str, enriched_event: dict):
    enriched_key = make_enriched_event_key(vehicle_event_key)

    json_bytes = json.dumps(enriched_event, indent=2).encode("utf-8")
    storage.put_object(enriched_key, json_bytes)

    return enriched_key