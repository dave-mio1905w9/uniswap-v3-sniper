import argparse
import asyncio
import logging
import signal
import sys

from sniper.config import Config
from sniper.listener import PoolListener
from sniper.executor import SwapExecutor


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sniper", description="Uniswap v3 pool listener and sniper")
    parser.add_argument("--dry-run", action="store_true", help="simulate swaps without sending txs")
    parser.add_argument("--amount", type=float, default=None, help="override buy amount in ETH")
    parser.add_argument("--test-pool", type=str, default=None, help="manually trigger check on existing pool address and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    return parser.parse_args(argv)


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def _shutdown(loop, sig=None):
    if sig:
        logging.getLogger("sniper.cli").info("received exit signal %s, stopping tasks", sig.name)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


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

    log.info("initialized config (dry_run=%s, amount=%.4f ETH, slippage=%.1f%%)", 
             cfg.dry_run, cfg.buy_amount_eth, cfg.max_slippage)

    executor = SwapExecutor(cfg)

    if args.test_pool:
        log.info("running manual test check on pool %s", args.test_pool)
        # print(f"DEBUG: inspecting pool {args.test_pool}")
        await executor.inspect_pool(args.test_pool)
        return 0

    listener = PoolListener(cfg, on_pool_detected=executor.handle_new_pool)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(_shutdown(loop, s)))
        except NotImplementedError:
            # windows loop support fallback
            pass

    try:
        await listener.run_forever()
    except asyncio.CancelledError:
        pass
    finally:
        log.info("listener stopped")
    return 0


def main() -> None:
    try:
        code = asyncio.run(main_async())
        sys.exit(code)
    except KeyboardInterrupt:
        sys.exit(130)
