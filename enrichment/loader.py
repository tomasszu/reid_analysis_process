import json


def load_vehicle_event(storage, key):
    data = storage.get_object(key)
    return json.loads(data)


def load_sightings_for_event(storage, event):
    sightings = []

    for s_key in event.get("sightings", []):
        full_key = f"sightings/{s_key}.json"

        try:
            data = storage.get_object(full_key)
            sightings.append(json.loads(data))
        except Exception as e:
            print(f"[Loader] Failed {full_key}: {e}")

    return sightings