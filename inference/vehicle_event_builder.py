from collections import defaultdict
from io import BytesIO
import numpy as np
from inference.vehicle_event import VehicleEvent
from license_plate_detection.plate_similarity import plate_similarity_weighted
from datetime import datetime, timezone


class VehicleEventBuilder:

    def __init__(
        self,
        storage,
        max_event_gap_sec: float = 300.0,
        merge_threshold: float = 0.8,
        feature_extraction_model_name: str = 'sp4_ep6_ft_noCEL_070126_26ep.engine',
        merge_weights: dict = None,
    ):
        self.storage = storage
        self.embedding_model = feature_extraction_model_name
        self.max_event_gap_ns = int(max_event_gap_sec * 1e9)
        self.max_gap_sec = max_event_gap_sec
        self.merge_threshold = merge_threshold
        self.events = []
        self.next_event_id = 1
        self.merge_weights = merge_weights or {"time": 0.3, "plate": 0.4, "embedding": 0.3}

    # ------------------- Public API -------------------

    def build_events(self, sightings):
        sightings = self._filter_sightings(sightings)
        sightings.sort(key=lambda s: s.data["timestamp_ns"])
        tracks = self._group_by_track(sightings)
        ordered_tracks = sorted(tracks.values(), key=lambda t: t[0].data["timestamp_ns"])
        for track_sightings in ordered_tracks:
            self._process_track(track_sightings)
        return self.events

    # ------------------- Filtering & Grouping -------------------

    def _filter_sightings(self, sightings):
        return [
            s for s in sightings
            if s.data.get("adequate_size") and not s.data.get("duplicate") and s.data.get("daytime")
        ]

    def _group_by_track(self, sightings):
        tracks = defaultdict(list)
        for s in sightings:
            key = (s.data["camera_id"], s.data["track_id"])
            tracks[key].append(s)
        return tracks

    # ------------------- Track Processing -------------------

    def _process_track(self, track_sightings):

        first = track_sightings[0]
        start_ts = first.data["timestamp_ns"]
        cam_id = first.data["camera_id"]
        track_id = first.data["track_id"]

        candidates = self._find_candidate_events(cam_id, start_ts)

        best_event = None
        best_total_score = -1
        best_merge_scores = None

        # compute track embedding once
        track_emb, best_sighting = self.track_representative_embedding(track_sightings)

        for event in candidates:

            total_score, time_score, plate_score, embedding_score = \
                self.score_track_to_event(track_sightings, event, track_emb)

            merge_scores = {
                "time": time_score,
                "plate": plate_score,
                "embedding": embedding_score,
                "total": total_score,
            }

            if total_score > best_total_score:
                best_total_score = total_score
                best_event = event
                best_merge_scores = merge_scores

        if best_event and self._passes_merge_rules(best_merge_scores):

            if not hasattr(best_event, "track_merge_scores"):
                best_event.track_merge_scores = {}

            best_event.track_merge_scores[track_id] = best_merge_scores

            self._attach_track(best_event, track_sightings)

        else:
            self._create_event(track_sightings)

    # ------------------- Candidate Events -------------------

    def _find_candidate_events(self, cam_id, track_start_ns):
        candidates = []
        for event in reversed(self.events):
            if event.last_seen_ts < track_start_ns - self.max_event_gap_ns:
                break
            if event.camera_id != cam_id:
                continue
            time_gap = track_start_ns - event.last_seen_ts
            if 0 <= time_gap <= self.max_event_gap_ns:
                candidates.append(event)
        return candidates

    # ------------------- Event Creation & Attachment -------------------

    def ns_to_day(self, ts_ns):
        dt = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)
        return dt.strftime("%Y/%m/%d")
    
    def make_event_key(self, camera_id, event_id, ts_ns):
        day = self.ns_to_day(ts_ns)
        return f"vehicle_events/{day}/{camera_id}/{event_id}_{ts_ns}.json"

    def _create_event(self, track_sightings):
        first = track_sightings[0]
        last = track_sightings[-1]
        event = VehicleEvent(
            event_id=self.next_event_id,
            camera_id=first.data["camera_id"],
            start_ts=first.data["timestamp_ns"],
            end_ts=last.data["timestamp_ns"],
            last_seen_ts=last.data["timestamp_ns"],
        )

        # generate storage key
        event.obj_key = self.make_event_key(
            event.camera_id,
            event.event_id,
            event.start_ts
        )

        self._attach_track(event, track_sightings)
        self.events.append(event)
        self.next_event_id += 1

    def _attach_track(self, event, track_sightings):
        last = track_sightings[-1]

        # append sightings and track
        event.sightings.extend(track_sightings)
        track_id = track_sightings[0].data["track_id"]
        event.tracks.append(track_id)

        event.end_ts = last.data["timestamp_ns"]
        event.last_seen_ts = last.data["timestamp_ns"]

        # 1️⃣ Update embedding centroid & variance
        track_emb, _ = self.track_representative_embedding(track_sightings)
        if track_emb is not None:
            self._update_event_embedding(event, track_emb)

        # 2️⃣ Update representative image
        best_sighting = max(track_sightings, key=self.score_sighting)
        event.representative_image = best_sighting.data.get("image_path")

        # 3️⃣ Update composite LPR
        lpr_list = [s.data.get("LPR") for s in event.sightings if s.data.get("LPR")]
        if lpr_list:
            best_lpr = max(lpr_list, key=lambda l: np.mean(l["char_scores"]))
            event.plate = best_lpr["plate"]
            event.plate_confidence = np.mean(best_lpr["char_scores"])
            event.plate_char_scores = best_lpr["char_scores"]
            event.LPR = best_lpr

    # ------------------- Scoring -------------------

    def score_sighting(self, sighting):
        if not sighting.data.get("adequate_size") or sighting.data.get("duplicate"):
            return -1
        width = sighting.data.get("width", 0)
        height = sighting.data.get("height", 0)
        res_score = width * height
        lpr = sighting.data.get("LPR")
        lpr_score = np.mean(lpr["char_scores"]) if lpr else 0.0
        return res_score * (1 + lpr_score)

    def score_track_to_event(self, track_sightings, event, track_emb=None):
        start_ts = track_sightings[0].data["timestamp_ns"]

        # --- Time score ---
        delta_ns = start_ts - event.last_seen_ts

        if 0 <= delta_ns <= self.max_event_gap_ns:
            time_score = 1.0 - (delta_ns / self.max_event_gap_ns)
        else:
            time_score = 0.0

        # --- Plate score ---
        track_lpr = track_sightings[0].data.get("LPR")
        event_lpr = getattr(event, "LPR", None)

        if (
            track_lpr
            and event_lpr
            and track_lpr.get("confidence") != 0
            and track_lpr.get("plate")
            and event_lpr.get("plate")
        ):
            plate_score = plate_similarity_weighted(track_lpr, event_lpr)
        else:
            plate_score = 0.5

        # --- Embedding score ---
        if track_emb is None:
            track_emb, _ = self.track_representative_embedding(track_sightings)

        if track_emb is None or event.embedding_centroid is None:
            embedding_score = 0.0
        else:
            embedding_score = float(np.dot(track_emb, event.embedding_centroid))

            # convert [-1,1] → [0,1]
            embedding_score = (embedding_score + 1) / 2

        # --- weighted merge score ---
        w = self.merge_weights

        total_score = (
            w["time"] * time_score
            + w["plate"] * plate_score
            + w["embedding"] * embedding_score
        )

        return total_score, time_score, plate_score, embedding_score
    
    def _passes_merge_rules(self, scores):

        # Hardoded criteria

        t = scores["time"]
        p = scores["plate"]
        e = scores["embedding"]
        total = scores["total"]

        # hard rejection

        if p < 0.3 and e < 0.85:
            return False

        # strong signals
        if p > 0.95:
            return True

        if t > 0.9 and e > 0.8:
            return True

        if p > 0.5 and e > 0.85:
            return True

        # fallback
        if total > self.merge_threshold:
            return True

        return False

    # ------------------- Embeddings -------------------

    def track_representative_embedding(self, track_sightings):
        """
        Returns the representative embedding for a track and the sighting that produced it.
        """
        if not track_sightings:
            return None, None

        # Pick best sighting by score
        best_sighting = max(track_sightings, key=self.score_sighting)

        # Get embedding path from nested embeddings dict
        embeddings_dict = best_sighting.data.get("embeddings", {})
        model_emb_info = embeddings_dict.get(self.embedding_model, None)

        if not model_emb_info:
            return None, best_sighting

        key = model_emb_info.get("path", None)
        if not key:
            return None, best_sighting

        # Load embedding from storage
        try:
            raw = self.storage.get_object(key)
            with BytesIO(raw) as f:
                embedding = np.load(f)
            return embedding, best_sighting
        except Exception as e:
            print(f"Failed to load embedding {key}: {e}")
            return None, best_sighting

    def _update_event_embedding(self, event, track_emb):
        if event.embedding_centroid is None:
            event.embedding_centroid = track_emb.copy()
            event.embedding_variance = np.zeros_like(track_emb)
            event.embedding_count = 1
        else:
            old_centroid = event.embedding_centroid
            old_var = getattr(event, "embedding_variance", np.zeros_like(old_centroid))
            old_count = getattr(event, "embedding_count", len(event.sightings) - 1)

            new_count = old_count + 1
            new_centroid = (old_centroid * old_count + track_emb) / new_count

            delta = track_emb - new_centroid
            old_delta = old_centroid - new_centroid
            new_var = (old_var * old_count + delta ** 2 + old_count * old_delta ** 2) / new_count

            event.embedding_centroid = new_centroid
            event.embedding_centroid /= np.linalg.norm(event.embedding_centroid)
            event.embedding_variance = new_var
            event.embedding_count = new_count