import json
import time

from enrichment.utils import make_enriched_event_key
from enrichment.loader import load_vehicle_event, load_sightings_for_event
from enrichment.saver import save_enriched_event
from enrichment.lpr import LPREnricher


class EnrichmentPipeline:
    def __init__(
        self,
        storage,
        enable_lpr=True,
        skip_existing=True,
        dry_run=False,
        limit=None,
    ):
        self.storage = storage
        self.enable_lpr = enable_lpr
        self.skip_existing = skip_existing
        self.dry_run = dry_run
        self.limit = limit

        if self.enable_lpr:
            self.lpr = LPREnricher(storage)

    def _process_event(self, event_key: str):
        # ---- load event ----
        event = load_vehicle_event(self.storage, event_key)

        print(f"[DEBUG] processing event: {event_key}")

        # ---- load sightings ----
        sightings = load_sightings_for_event(self.storage, event)

        if not sightings:
            raise RuntimeError("No sightings found")

        # ---- LPR enrichment ----
        if self.enable_lpr:
            event["LPR"] = self.lpr.process_event(sightings)

        # ---- stats (useful later for filtering/debugging) ----
        event["enrichment"] = {
            "num_sightings_loaded": len(sightings),
            "lpr_enabled": self.enable_lpr,
        }

        # ---- save ----
        if not self.dry_run:
            save_enriched_event(self.storage, event_key, event)

    # -----------------------------------------------------



    def run(self, days):
        global_processed = 0

        for day in days:
            start_time = time.time()

            prefix = f"vehicle_events/{day}/"
            print(f"\n[Enrichment] === DAY {day} ===")

            total = 0
            processed = 0
            skipped = 0
            failed = 0

            for key in self.storage.list_objects(prefix):

                if not key.endswith(".json"):
                    continue

                total += 1

                enriched_key = make_enriched_event_key(key)

                # ---- skip existing ----
                if self.skip_existing:
                    try:
                        self.storage.get_object(enriched_key)
                        skipped += 1
                        continue
                    except:
                        pass

                try:
                    self._process_event(key)
                    processed += 1
                    global_processed += 1

                    if self.limit and global_processed >= self.limit:
                        print("\n[Enrichment] LIMIT REACHED")
                        return

                except Exception as e:
                    failed += 1
                    print(f"[ERROR] {key}: {e}")

            elapsed = time.time() - start_time

            print(
                f"[Enrichment][{day}] "
                f"total={total} processed={processed} skipped={skipped} failed={failed} "
                f"time={elapsed:.2f}s"
            )

        print(f"\n[Enrichment] DONE. Total processed: {global_processed}")