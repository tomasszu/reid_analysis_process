import json
import numpy as np
from collections import defaultdict
from typing import List
from PIL import Image
from io import BytesIO

from ultralytics import YOLO
from fast_plate_ocr import LicensePlateRecognizer

from license_plate_detection.test_model_imports import run_lpr_test


class LPRAnnotator:
    def __init__(self, storage, plate_length: int = 9):
        self.storage = storage
        self.lpr_detection_model = YOLO('license_plate_detection/license-plate-finetune-v1l.pt')

        onnx_providers = [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
        self.lpr_recognition_model = LicensePlateRecognizer('cct-xs-v1-global-model', providers=onnx_providers)

        self.plate_length = plate_length

        self.min_char_score = 0.45 # This can be changed, but from some examples this seemed correct

    # ---------------------------------------------------------

    def run_test(self):

        return run_lpr_test(self.lpr_detection_model, self.lpr_recognition_model)

    def process(self, sightings: List):
        """
        sightings = output of load_analysis_day(...)
        """

        # ---- group by track_id ----
        tracks = defaultdict(list)
        for s in sightings:
            track_id = s.data.get("track_id")
            if track_id is not None:
                tracks[track_id].append(s)

        # ---- process each track ----
        for track_sightings in tracks.values():
            self._process_track(track_sightings)

    # ---------------------------------------------------------

    def _process_track(self, track_sightings: List):

        plate_chars = ["_"] * self.plate_length
        char_scores = np.zeros(self.plate_length)

        any_detection = False

        for sighting in track_sightings:

            if not sighting.data.get("adequate_size"):
                continue

            if sighting.data.get("duplicate"):
                continue

            image_key = sighting.data.get("image_path")
            if not image_key:
                continue

            # ---- load image from MinIO ----
            try:
                img_bytes = self.storage.get_object(image_key)
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
            except Exception:
                continue

            # ---- run LPR model ----
            try:
                texts, scores = self._detect_and_read(img)
                # (['KV534____'], array([[          1,     0.99962,     0.99858,     0.99984,           1,     0.99716,     0.99999,           1,           1]], dtype=float32))
            except Exception:
                continue

            if not texts:
                continue

            text = texts[0] 
            per_char_scores = scores[0]

            any_detection = True

            # ---- character-wise fusion ----
            for i in range(min(self.plate_length, len(text))):
                new_score = float(per_char_scores[i])

                if new_score > char_scores[i]:
                    plate_chars[i] = text[i]
                    char_scores[i] = new_score

        # ---- finalize track result ----

        if not any_detection:
            final_plate = None
            overall_conf = 0.0
            status = "none"

        else:
            final_plate = "".join(plate_chars).rstrip("_")

            valid_scores = char_scores[char_scores > self.min_char_score]
            overall_conf = float(valid_scores.mean()) if len(valid_scores) else 0.0

            if "_" in plate_chars:
                status = "partial"
            else:
                status = "ok"

        # ---- attach same LPR block to ALL sightings in track ----

        lpr_block = {
            "plate": final_plate,
            "char_scores": char_scores.tolist(),
            "confidence": overall_conf,
            "status": status,
        }

        for sighting in track_sightings:
            sighting.data["LPR"] = lpr_block

    def _detect_and_read(self, Image):

        img_np = np.array(Image)  # shape (H, W, 3)
        
        det_results = self.lpr_detection_model.predict(source=img_np)[0]

        license_plate = det_results.boxes.data.tolist()[0]

        x1, y1, x2, y2, score, class_id = license_plate

        # crop license plate
        license_plate_crop = img_np[int(y1):int(y2), int(x1): int(x2), :]

        read, scores = self.lpr_recognition_model.run(source = license_plate_crop, return_confidence=True)

        return read, scores

