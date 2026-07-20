import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Any, Optional
import websockets
from eth_abi import decode

from sniper.abi import POOL_CREATED_TOPIC0

logger = logging.getLogger("sniper.listener")


def _topic_to_address(hex_topic: str) -> str:
    clean = hex_topic[2:] if hex_topic.startswith("0x") else hex_topic
    # take last 20 bytes (40 hex chars)
    return "0x" + clean[-40:].lower()


def decode_pool_created(log: Dict[str, Any]) -> Dict[str, Any]:
    """Extract token0, token1, fee, tickSpacing and pool from raw eth_subscribe log."""
    topics = log.get("topics", [])
    if len(topics) < 4:
        raise ValueError(f"unexpected topics count for PoolCreated: {len(topics)}")

    token0 = _topic_to_address(topics[1])
    token1 = _topic_to_address(topics[2])
    fee = int(topics[3], 16)

    data_bytes = bytes.fromhex(log["data"][2:] if log["data"].startswith("0x") else log["data"])
    tick_spacing, pool_raw = decode(["int24", "address"], data_bytes)

    return {
        "token0": token0,
        "token1": token1,
        "fee": fee,
        "tick_spacing": tick_spacing,
        "pool": pool_raw.lower(),
        "block_number": int(log.get("blockNumber", "0x0"), 16),
        "tx_hash": log.get("transactionHash"),
        "log_index": int(log.get("logIndex", "0x0"), 16),
    }


class EventListener:
    """Maintains persistent WebSocket subscription to block headers and factory logs."""

    def __init__(self, ws_url: str, factory_address: str, max_retry_delay: float = 30.0):
        self.ws_url = ws_url
        self.factory_address = factory_address.lower()
        self.max_retry_delay = max_retry_delay
        self._req_id = 0
        self._running = True

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def stop(self):
        self._running = False

    async def events(self) -> AsyncIterator[Dict[str, Any]]:
        retry_delay = 1.0
        while self._running:
            try:
                logger.info(f"connecting to ws: {self.ws_url}")
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=2**22,  # 4MB just in case
                ) as ws:
                    retry_delay = 1.0  # reset on good connection

                    # subscribe heads
                    await ws.send(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": self._next_id(),
                                "method": "eth_subscribe",
                                "params": ["newHeads"],
                            }
                        )
                    )
                    heads_resp = json.loads(await ws.recv())
                    heads_sub_id = heads_resp.get("result")
                    if not heads_sub_id:
                        raise RuntimeError(f"failed heads subscription: {heads_resp}")

                    # subscribe pool creation logs
                    await ws.send(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": self._next_id(),
                                "method": "eth_subscribe",
                                "params": [
                                    "logs",
                                    {
                                        "address": self.factory_address,
                                        "topics": [POOL_CREATED_TOPIC0],
                                    },
                                ],
                            }
                        )
                    )
                    logs_resp = json.loads(await ws.recv())
                    logs_sub_id = logs_resp.get("result")
                    if not logs_sub_id:
                        raise RuntimeError(f"failed pool logs subscription: {logs_resp}")

                    logger.info(
                        f"connected, active subs: heads={heads_sub_id} logs={logs_sub_id}"
                    )

                    async for raw_msg in ws:
                        if not self._running:
                            break
                        msg = json.loads(raw_msg)
                        if "params" not in msg:
                            continue

                        sub_id = msg["params"].get("subscription")
                        res = msg["params"].get("result")
                        if not res:
                            continue

                        # print("raw event", sub_id, res)
                        if sub_id == heads_sub_id:
                            # block header
                            block_num = int(res.get("number", "0x0"), 16)
                            base_fee = int(res.get("baseFeePerGas", "0x0"), 16) if "baseFeePerGas" in res else None
                            yield {
                                "kind": "block",
                                "number": block_num,
                                "hash": res.get("hash"),
                                "base_fee": base_fee,
                                "timestamp": int(res.get("timestamp", "0x0"), 16),
                            }
                        elif sub_id == logs_sub_id:
                            try:
                                parsed = decode_pool_created(res)
                                yield {"kind": "pool_created", "data": parsed}
                            except Exception as e:
                                logger.warning(f"failed decoding pool log: {e}")

            except (websockets.exceptions.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                if not self._running:
                    break
                logger.warning(f"ws disconnected ({e}), retrying in {retry_delay:.1f}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.8, self.max_retry_delay)
            except Exception as e:
                if not self._running:
                    break
                logger.exception(f"unexpected listener crash: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2.0, self.max_retry_delay)
