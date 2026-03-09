from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class VehicleEvent:

    event_id: int
    camera_id: str

    start_ts: int
    end_ts: int
    last_seen_ts: int

    tracks: List[int] = field(default_factory=list)
    sightings: List[object] = field(default_factory=list)

    plate: Optional[str] = None
    plate_confidence: float = 0.0

    embedding_centroid: Optional[np.ndarray] = None
    representative_image: Optional[str] = None