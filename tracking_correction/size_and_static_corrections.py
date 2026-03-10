# analysis/static_corrections.py
import os
from typing import List
from PIL import Image
from io import BytesIO

from data_loader import Sighting, StorageBackend  # adjust import if needed


class StaticVehicleCorrector:
    """
    Phase 1 analysis: mark inadequate images and static vehicle duplicates
    """
    def __init__(
        self,
        storage: StorageBackend,
        time_window_sec: int = 5*60,
        res_tolerance: float = 0.025,
        size_tolerance: float = 0.07,
        min_width: int = 70,
        min_height: int = 70
    ):
        """
        Args:
            time_window_sec: look-back window for duplicates (seconds)
            res_tolerance: allowable % difference in width/height for duplicates
            size_tolerance: allowable % difference in file size
            min_width/min_height: minimum image dimensions
        """
        self.storage = storage
        self.time_window_sec = time_window_sec
        self.res_tolerance = res_tolerance
        self.size_tolerance = size_tolerance
        self.min_width = min_width
        self.min_height = min_height

        # cache per camera_id: list of previous sightings
        self.cache = {}

    def mark_sightings(self, sightings: List[Sighting]) -> List[Sighting]:
        """
        Process all sightings for a day.
        Updates Sighting.data in-place with:
            - adequate_size: bool
            - duplicate: bool
        """
        # Ensure the list is sorted by object key or sighting_id for proper rolling cache behavior
        sightings.sort(key=lambda s: s.obj_key)

        for sighting in sightings:
            img_key = sighting.data["image_path"]
            cam_id = sighting.data["camera_id"]
            ts_ns = sighting.data["timestamp_ns"]
            track_id = sighting.data["track_id"]

            # --- check image size ---
            try:
                img_bytes = self.storage.get_object(img_key)
                with Image.open(BytesIO(img_bytes)) as img:
                    width, height = img.size

                file_size = len(img_bytes)

                sighting.data["width"] = width
                sighting.data["height"] = height
                sighting.data["file_size"] = file_size

                sighting.data["adequate_size"] = (
                    width >= self.min_width and height >= self.min_height
                )

            except Exception:
                sighting.data["adequate_size"] = False
                sighting.data["duplicate"] = False
                print("Error while establishing image size and reolution. File may not have been loaded properly.")
                continue

            # Skip duplicate check if not adequate
            if not sighting.data["adequate_size"]:
                sighting.data["duplicate"] = False
                continue

            # --- initialize camera cache ---
            if cam_id not in self.cache:
                self.cache[cam_id] = []

            # --- rolling cache cleanup ---
            self.cache[cam_id] = [
                prev for prev in self.cache[cam_id]
                if (ts_ns - prev["timestamp_ns"]) / 1e9 <= self.time_window_sec
            ]

            # --- duplicate detection ---
            is_duplicate = False

            for prev in self.cache[cam_id]:
                # Only check sightings with DIFFERENT track_id
                if prev["track_id"] == track_id:
                    continue

                # Time difference
                dt_sec = abs(ts_ns - prev["timestamp_ns"]) / 1e9
                if dt_sec > self.time_window_sec:
                    continue

                # Resolution difference
                width_diff = abs(width - prev["width"]) / prev["width"]
                height_diff = abs(height - prev["height"]) / prev["height"]
                if width_diff > self.res_tolerance or height_diff > self.res_tolerance:
                    continue

                # File size difference
                size_diff = abs(file_size - prev["file_size"]) / prev["file_size"]
                if size_diff > self.size_tolerance:
                    continue

                # All conditions satisfied → duplicate
                is_duplicate = True
                break

            sighting.data["duplicate"] = is_duplicate

            # Add to cache if not duplicate
            if not is_duplicate:
                self.cache[cam_id].append({
                    "timestamp_ns": ts_ns,
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                    "track_id": track_id
                })

        return sightings