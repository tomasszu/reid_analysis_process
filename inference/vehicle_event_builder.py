from collections import defaultdict
from vehicle_event import VehicleEvent
import List


class VehicleEventBuilder:

    def __init__(
        self,
        max_event_gap_sec: float = 300.0,
        merge_threshold: float = 0.85,
    ):
        """
        Parameters
        ----------
        max_event_gap : float
            Maximum seconds between tracks for same event
        merge_threshold : float
            Score threshold for merging tracks into existing event
        """

        self.max_event_gap_ns = int(max_event_gap_sec * 1e9) # convert to nanoseconds
        self.merge_threshold = merge_threshold

        self.events = []
        self.next_event_id = 1

    def _filter_sightings(self, sightings):

        filtered = []

        for sighting in sightings:

            data = sighting.data

            if not data.get("adequate_size"):
                continue

            if data.get("duplicate"):
                continue

            if not data.get("daytime"):
                continue

            filtered.append(sighting)

        return filtered

    def build_events(self, sightings):

        # Step 1 — filter invalid sightings
        sightings = self._filter_sightings(sightings)

        # Step 2 — sort chronologically
        sightings = sorted(
            sightings,
            key=lambda s: s.data["timestamp_ns"]
        )

        # Step 3 — group sightings into tracks
        tracks = self._group_by_track(sightings)

        # Step 4 — process tracks in time order
        ordered_tracks = sorted(
            tracks.values(),
            key=lambda t: t[0].data["timestamp_ns"]
        )

        for track_sightings in ordered_tracks:
            self._process_track(track_sightings)

        return self.events

    def _group_by_track(self, sightings):

        tracks = defaultdict(list)

        for s in sightings:

            cam = s.data["camera_id"]
            track = s.data["track_id"]

            key = (cam, track)

            tracks[key].append(s)

        return tracks

    def _process_track(self, track_sightings):

        first = track_sightings[0]
        last = track_sightings[-1]

        cam_id = first.data["camera_id"]

        start_ts = first.data["timestamp_ns"]
        end_ts = last.data["timestamp_ns"]

        # candidate events
        candidates = self._find_candidate_events(cam_id, start_ts)

        # scoring not implemented yet
        best_event = None

        if best_event:
            self._attach_track(best_event, track_sightings)
        else:
            self._create_event(track_sightings)

    def _find_candidate_events(self, cam_id, track_start_ts):

        candidates = []

        for event in self.events:

            if event.camera_id != cam_id:
                continue

            time_gap = track_start_ts - event.last_seen_ts

            if 0 <= time_gap <= self.max_event_gap_ns:
                candidates.append(event)

        return candidates

    def _create_event(self, track_sightings):

        first = track_sightings[0]
        last = track_sightings[-1]

        start_ts = first.data["timestamp_ns"]
        end_ts = last.data["timestamp_ns"]

        cam_id = first.data["camera_id"]
        track_id = first.data["track_id"]

        event = VehicleEvent(
            event_id=self.next_event_id,
            camera_id=cam_id,
            start_ts=start_ts,
            end_ts=end_ts,
            last_seen_ts=end_ts,
        )

        event.sightings.extend(track_sightings)
        event.tracks.append(track_id)

        self.events.append(event)

        self.next_event_id += 1

    def _attach_track(self, event, track_sightings):

        last = track_sightings[-1]

        event.sightings.extend(track_sightings)

        track_id = track_sightings[0].data["track_id"]
        event.tracks.append(track_id)

        event.end_ts = last.data["timestamp_ns"]
        event.last_seen_ts = last.data["timestamp_ns"]

    def plate_similarity(plateA, scoresA, plateB, scoresB):

        max_len = max(len(plateA), len(plateB))

        score_sum = 0
        weight_sum = 0

        for i in range(max_len):

            charA = plateA[i] if i < len(plateA) else "_"
            charB = plateB[i] if i < len(plateB) else "_"

            confA = scoresA[i] if i < len(scoresA) else 0
            confB = scoresB[i] if i < len(scoresB) else 0

            if charA == "_" or charB == "_":
                continue

            weight = (confA + confB) / 2

            weight_sum += weight

            if charA == charB:
                score_sum += weight
            else:
                score_sum -= weight * 0.5

        if weight_sum == 0:
            return 0

        score = score_sum / weight_sum
        return max(0, min(1, score))
