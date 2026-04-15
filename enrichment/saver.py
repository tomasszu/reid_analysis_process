import json
from enrichment.utils import make_enriched_event_key


def save_enriched_event(storage, vehicle_event_key, enriched_event):
    enriched_key = make_enriched_event_key(vehicle_event_key)

    json_bytes = json.dumps(enriched_event, indent=2).encode("utf-8")
    storage.put_object(enriched_key, json_bytes)

    return enriched_key