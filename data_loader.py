from abc import ABC, abstractmethod
from typing import Iterable, Dict, Optional
from dataclasses import dataclass
import json

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