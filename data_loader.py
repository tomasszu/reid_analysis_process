from abc import ABC, abstractmethod
from typing import Iterable, Dict, Optional
from dataclasses import dataclass
import json
from io import BytesIO

@dataclass
class Sighting:
    obj_key: str           # original path in storage
    data: Dict             # full JSON dict
    day: str               # optional, for convenience


class StorageBackend(ABC):
    @abstractmethod
    def list_objects(self, prefix: str = "", max_keys: Optional[int] = None) -> Iterable[str]:
        pass

    @abstractmethod
    def get_object(self, key: str) -> bytes:
        pass

    @abstractmethod
    def put_object(self, key: str, data: bytes) -> None:
        """Write or overwrite object at key"""
        pass

    @abstractmethod
    def bucket_exists(self) -> bool:
        pass


def load_day(storage: StorageBackend, day: str, model: str):
    '''
    Args:
        day - Str in the form of "YYYY/MM/DD"
        model - model version for embeddings in Str
    '''
    prefixes = []
    for folder in ["embeddings", "images", "sightings"]:
        if folder != "embeddings":
            prefixes.append(f"{folder}/{day}")
        else:
            prefixes.append(f"{folder}/{model}/{day}")

    for prefix in prefixes:
        for obj_key in storage.list_objects(prefix):
            raw_bytes = storage.get_object(obj_key)

            # parse embedding here
            print(obj_key, len(raw_bytes))

def load_sightings_day(storage: StorageBackend, day: str):
    prefix = f"sightings/{day}"
    sightings = []

    for obj_key in storage.list_objects(prefix):
        raw = storage.get_object(obj_key)
        data = json.loads(raw)

        sightings.append(Sighting(obj_key=obj_key, data=data, day=day))

    return sightings

def load_analysis_day(storage: StorageBackend, day: str):
    prefix = f"analysis/{day}"
    analysis = []

    for obj_key in storage.list_objects(prefix):
        raw = storage.get_object(obj_key)
        data = json.loads(raw)

        analysis.append(Sighting(obj_key=obj_key, data=data, day=day))

    return analysis

def save_analysis_sighting(storage: StorageBackend, sighting: Sighting):
    """
    Saves modified sighting JSON under analysis/ prefix.
    Does NOT delete anything. Only overwrites or creates.
    """

    # Convert:
    # sightings/YYYY/MM/DD/uuid.json
    # → analysis/YYYY/MM/DD/uuid.json

    if not sighting.obj_key.startswith("sightings/"):
        raise ValueError("Unexpected obj_key format")

    analysis_key = sighting.obj_key.replace("sightings/", "analysis/", 1)

    json_bytes = json.dumps(sighting.data, indent=2).encode("utf-8")

    storage.put_object(analysis_key, json_bytes)

def update_analysis(storage: StorageBackend, analysis: Sighting):
    """
    Merge-updates analysis JSON.
    Only adds/updates fields. Never deletes existing ones.
    """

    # → analysis/YYYY/MM/DD/uuid.json

    analysis_key = analysis.obj_key  # already analysis/ path


    try:
        # Try loading existing analysis file
        existing_raw = storage.get_object(analysis_key)
        existing_data = json.loads(existing_raw)
    except Exception:
        # If not existing, start fresh
        existing_data = {}

    # Merge: sighting.data overwrites existing_data keys
    merged = {**existing_data, **analysis.data}

    json_bytes = json.dumps(merged, indent=2).encode("utf-8")
    storage.put_object(analysis_key, json_bytes)