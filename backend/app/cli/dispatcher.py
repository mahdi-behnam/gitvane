"""CLI entrypoint for gitvane-dispatcher daemon service."""

import argparse
import asyncio
import logging
import sys

from app.db.session import SessionLocal
from app.execution.outbox_dispatcher import OutboxDispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gitvane-dispatcher")


def main() -> None:
    """Run gitvane-dispatcher daemon."""
    parser = argparse.ArgumentParser(description="GitVane Outbox Dispatcher Service")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds (default: 1.0)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch limit per claim (default: 100)")
    parser.add_argument("--dispatcher-id", type=str, default=None, help="Custom dispatcher identifier")

    args = parser.parse_args()

    dispatcher = OutboxDispatcher(dispatcher_id=args.dispatcher_id)
    logger.info("Initializing GitVane Outbox Dispatcher...")

    try:
        asyncio.run(
            dispatcher.run_forever(
                db_factory=SessionLocal,
                poll_interval=args.interval,
                batch_size=args.batch_size,
            )
        )
    except KeyboardInterrupt:
        logger.info("Outbox Dispatcher stopped by KeyboardInterrupt.")
    except Exception as exc:
        logger.exception("Outbox Dispatcher failed with unhandled exception: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
