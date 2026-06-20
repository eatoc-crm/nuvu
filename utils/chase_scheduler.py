"""Background cadence for Chase Engine (15-minute interval, Phase A brief §1.2)."""

from __future__ import annotations

import os
import threading
import time


def start_chase_cadence_scheduler() -> None:
    """Start a daemon thread that calls run_cadence_check every 15 minutes."""
    if os.environ.get("CHASE_SCHEDULER_DISABLED", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        print("[chase_scheduler] disabled (CHASE_SCHEDULER_DISABLED)")
        return

    def _loop() -> None:
        # Immediate startup sync — populate local tables before first dashboard request.
        try:
            from utils.adapter_sync import run_adapter_sync

            run_adapter_sync()
        except Exception as e:
            print(f"[chase_scheduler] startup adapter_sync error: {e}")

        time.sleep(60)
        while True:
            try:
                from utils.adapter_sync import run_adapter_sync
                from routes.chase_engine import run_cadence_check
                from routes.chain_chase import run_chain_cadence_check

                run_adapter_sync()
                run_cadence_check()
                run_chain_cadence_check()
            except Exception as e:
                print(f"[chase_scheduler] cadence error: {e}")
            time.sleep(900)

    t = threading.Thread(
        target=_loop, daemon=True, name="nuvu-chase-cadence"
    )
    t.start()
    print("[chase_scheduler] started (15m cadence after 60s initial delay)")
