"""CLI entrypoint for gitvane-reconciler daemon service."""

import argparse
import asyncio
import logging
import sys

from app.db.session import SessionLocal
from app.execution.outbox_reconciler import OutboxReconciler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gitvane-reconciler")


def main() -> None:
    """Run gitvane-reconciler daemon."""
    parser = argparse.ArgumentParser(description="GitVane Outbox Reconciler Service")
    parser.add_argument("--interval", type=float, default=10.0, help="Reconciliation pass interval in seconds (default: 10.0)")
    parser.add_argument("--outbox-lease-timeout", type=int, default=300, help="Outbox processing lease timeout in seconds (default: 300)")
    parser.add_argument("--finalizing-threshold", type=int, default=120, help="Finalizing safety threshold in seconds (default: 120)")
    parser.add_argument("--reconciler-id", type=str, default=None, help="Custom reconciler identifier")

    args = parser.parse_args()

    reconciler = OutboxReconciler(reconciler_id=args.reconciler_id)
    logger.info("Initializing GitVane Outbox Reconciler...")

    try:
        asyncio.run(
            reconciler.run_forever(
                db_factory=SessionLocal,
                poll_interval=args.interval,
                outbox_lease_seconds=args.outbox_lease_timeout,
                finalizing_threshold_seconds=args.finalizing_threshold,
            )
        )
    except KeyboardInterrupt:
        logger.info("Outbox Reconciler stopped by KeyboardInterrupt.")
    except Exception as exc:
        logger.exception("Outbox Reconciler failed with unhandled exception: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
