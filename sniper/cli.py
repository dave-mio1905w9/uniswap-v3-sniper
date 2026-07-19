import argparse
import asyncio
import logging
import sys

from sniper.config import Config
from sniper.listener import PoolListener
from sniper.executor import SwapExecutor


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Uniswap v3 pool listener and sniper")
    parser.add_argument("--dry-run", action="store_true", help="simulate swaps without sending txs")
    parser.add_argument("--amount", type=float, default=None, help="override buy amount in ETH")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    return parser.parse_args(argv)


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def main_async() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    log = logging.getLogger("sniper.cli")

    try:
        cfg = Config.load()
    except ValueError as e:
        log.error("config error: %s", e)
        return 1

    if args.dry_run:
        cfg.dry_run = True
    if args.amount is not None:
        cfg.buy_amount_eth = args.amount

    log.info("starting sniper daemon (dry_run=%s, amount=%.4f ETH)", cfg.dry_run, cfg.buy_amount_eth)

    executor = SwapExecutor(cfg)
    listener = PoolListener(cfg, on_pool_detected=executor.handle_new_pool)

    try:
        await listener.run_forever()
    except asyncio.CancelledError:
        log.info("shutting down")
    return 0


def main() -> None:
    try:
        code = asyncio.run(main_async())
        sys.exit(code)
    except KeyboardInterrupt:
        sys.exit(130)
