# Vehicle Event Enrichment Pipeline

## Overview

This service processes pre-existing **vehicle event JSONs** stored in MinIO and generates enriched versions under `enriched_events/`.

It operates *after* the re-identification stage and focuses on dataset augmentation tasks such as:

* License plate recognition (LPR)
* Event-level aggregation of sighting-level signals
* Optional future enrichment steps (embeddings, heuristics, metadata augmentation)

The pipeline is designed to be **idempotent**: if an enriched event already exists, it will be skipped unless explicitly overridden.

---

## Data Model

### Input: `vehicle_events/YYYY/MM/DD/<event_id>.json`

Contains:

* vehicle_id (from ReID stage)
* sightings (list of sighting keys)
* timestamps, camera_id
* embeddings (optional)
* representative sighting

Sightings live in:

```
sightings/YYYY/MM/DD/<sighting_id>.json
```

---

### Output: `enriched_events/YYYY/MM/DD/<event_id>.json`

Adds:

* `LPR` (event-level aggregated plate)
* `enrichment` metadata (debug + pipeline stats)

---

## Features

### 1. LPR Enrichment (enabled via `--enable-lpr`)

* Runs YOLO-based plate detection
* OCR decoding via ONNX model
* Aggregates per-sighting results into a single event-level plate
* Uses confidence-aware character fusion across sightings

---

### 2. Skip Logic

* If enriched event already exists → skip
* Prevents recomputation on repeated runs

---

### 3. Batch Processing

Supports:

* Single day
* Date range (inclusive)

Example:

```
--start-date 2026-04-15
--end-date 2026-04-20
```

If only `--start-date` is provided → only that day is processed.

---

### 4. Limits & Debugging

* `--limit N` stops after N processed events globally
* `--dry-run` disables writes
* Verbose logging per event + per day

---

## CLI Usage

```bash
python main.py \
  --start-date 2026-04-15 \
  --end-date 2026-04-20 \
  --enable-lpr \
  --limit 100
```

Single day:

```bash
python main.py --start-date 2026-04-15 --enable-lpr
```

Dry run:

```bash
python main.py --start-date 2026-04-15 --dry-run --enable-lpr
```

---

## Docker container Usage

```sh

#local desktop test dry run for one day:

docker run --rm \
  --network host \
  -e MINIO_ENDPOINT=localhost:9000 \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=minioadmin \
  -e MINIO_BUCKET=reid-service \
  reideventenrichment:latest \
  --start-date 2026-04-15 \
  --dry-run \
  --limit 10 \
  --enable-lpr
```

## Architecture

```
MinIO
 ├── vehicle_events/
 ├── sightings/
 ├── images/
 ├── embeddings/
 └── enriched_events/   ← output

EnrichmentPipeline
 ├── load event
 ├── load sightings
 ├── run LPR (optional)
 ├── aggregate event-level metadata
 └── save enriched event
```

---

## Current TODOs

### Core Improvements

* [ ] Parallelize event processing (per-day batching)
* [ ] Add retry mechanism for corrupted sighting JSONs
* [ ] Add structured logging (replace prints)

### LPR Improvements

* [ ] Cache detection results per sighting (avoid repeated OCR on reruns)
* [ ] Improve plate confidence calibration
* [ ] Add multi-frame plate voting across tracks

### Data Model

* [ ] Store explicit enrichment versioning in event JSON
* [ ] Add `"enriched_at"` timestamp field
* [ ] Separate enrichment layers (LPR, embeddings, analytics)

### Performance

* [ ] Batch MinIO reads (reduce per-object latency)
* [ ] Optional multiprocessing per event batch

### Future Enrichments

* [ ] Vehicle re-clustering (post-ReID refinement)
* [ ] Cross-camera trajectory stitching validation
* [ ] Embedding recomputation / model version upgrades
* [ ] Anomaly detection on event durations / gaps