# ReID Event Enrichment

Post-processing enrichment pipeline for ReID vehicle events.

The enrichment container loads `vehicle_events`, gathers associated sightings, performs optional enrichment steps (currently License Plate Recognition / LPR), and stores the result as `enriched_events`.

---

# Launching

---

## Server Dry Run

```sh id="5d40ul"
docker run --rm \
  -e MINIO_ENDPOINT=d42edgeai:9090 \
  -e MINIO_ACCESS_KEY=reid-test \
  -e MINIO_SECRET_KEY=labaparole \
  -e MINIO_BUCKET=reid-test \
  ghcr.io/tomasszu/reideventenrichment:latest \
  --start-date 2026-05-05 \
  --dry-run \
  --limit 10 \
  --enable-lpr
```

---

## Full Server Run

```sh id="j4cfqi"
docker run --rm -d \
  -e MINIO_ENDPOINT=d42edgeai:9090 \
  -e MINIO_ACCESS_KEY=reid-test \
  -e MINIO_SECRET_KEY=labaparole \
  -e MINIO_BUCKET=reid-test \
  ghcr.io/tomasszu/reideventenrichment:latest \
  --start-date 2026-04-17 \
  --end-date 2026-04-18 \
  --enable-lpr
```

---

# What the Pipeline Does

For every object inside:

```text id="v1s8r9"
vehicle_events/YYYY/MM/DD/
```

the pipeline:

1. Loads the vehicle event JSON
2. Loads all associated sightings
3. Runs enrichment modules
4. Saves the enriched output to:

```text id="2jjqfo"
enriched_events/YYYY/MM/DD/
```

---

# Current Enrichment Features

## License Plate Recognition (LPR)

When enabled:

```text id="d4x16e"
--enable-lpr
```

the pipeline performs license plate extraction using the event sightings.

Example enriched structure:

```json id="a8t26d"
{
  "LPR": {
    "plate": "AB1234",
    "confidence": 0.91
  }
}
```

---

# Generated Metadata

The pipeline also stores enrichment metadata:

```json id="u90lfm"
{
  "enrichment": {
    "num_sightings_loaded": 18,
    "lpr_enabled": true
  }
}
```

Useful for:

* debugging
* filtering
* enrichment validation
* pipeline statistics

---

# Important CLI Flags

## Date Range

```text id="9jzq71"
--start-date YYYY-MM-DD
--end-date YYYY-MM-DD
```

Processes all days inside the range. Can select only start date for one only day to be processed.

---

## Dry Run

```text id="v2ksf4"
--dry-run
```

Runs the full pipeline without saving results.

Useful for:

* debugging
* validating MinIO connectivity
* testing enrichment logic

---

## Limit

```text id="bb84yc"
--limit N
```

Stops processing after `N` events globally.

Useful for:

* fast validation
* profiling
* development testing

---

## Skip Existing

Existing enriched events are skipped automatically by default.

This prevents recomputing already processed data.

---

# Expected Input Structure

## Vehicle Events

```text id="z1l7nr"
vehicle_events/YYYY/MM/DD/<event>.json
```

Each event is expected to contain references to sightings.

---

## Sightings

```text id="0te6jv"
sightings/YYYY/MM/DD/<sighting>.json
```

Used for:

* LPR processing
* representative image extraction
* future enrichment modules

---

# Output Structure

## Enriched Events

```text id="n9rlu2"
enriched_events/YYYY/MM/DD/<event>.json
```

The original event is preserved and extended with additional fields.

---

# Container LPR Workflow

```text id="nq1kn4"
vehicle_events
    ↓
load sightings
    ↓
run LPR
    ↓
attach enrichment metadata
    ↓
save enriched_events
```

---

# Notes

The enrichment pipeline is designed to be modular.

Additional enrichers can later be added for:

* vehicle color
* vehicle type
* anomaly detection
* representative crop selection
* embedding statistics
* trajectory analytics
