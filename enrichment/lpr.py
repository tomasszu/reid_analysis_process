import numpy as np
from collections import defaultdict

from license_plate_detection.lpr_annotator import LPRAnnotator


class LPREnricher:
    def __init__(self, storage):
        self.annotator = LPRAnnotator(storage)

    def process_event(self, sightings):
        """
        Run LPR on all sightings and aggregate into single event-level plate
        """

        # reuse existing logic → annotate sightings first
        wrapped = [DummySighting(s) for s in sightings]
        self.annotator.process(wrapped)

        # collect all LPR blocks
        lprs = [s.data.get("LPR") for s in wrapped if s.data.get("LPR")]

        if not lprs:
            return {
                "plate": None,
                "confidence": 0.0,
                "status": "none",
                "char_scores": [],
            }

        # pick best (same logic as before)
        best = max(lprs, key=lambda l: np.mean(l["char_scores"]) if l["char_scores"] else 0)

        return best


class DummySighting:
    def __init__(self, data):
        self.data = data