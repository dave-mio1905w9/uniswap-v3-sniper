import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Any
import websockets

from sniper.abi import POOL_CREATED_TOPIC0

logger = logging.getLogger(__name__)


class EventListener:
    def __init__(self, ws_url: str, factory_address: str):
        self.ws_url = ws_url
        self.factory_address = factory_address.lower()
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def listen(self) -> AsyncIterator[Dict[str, Any]]:
        async with websockets.connect(self.ws_url) as ws:
            # subscribe to newHeads
            heads_payload = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "eth_subscribe",
                "params": ["newHeads"],
            }
            await ws.send(json.dumps(heads_payload))
            heads_resp = json.loads(await ws.recv())
            heads_sub_id = heads_resp.get("result")
            logger.info(f"subscribed to newHeads: {heads_sub_id}")

            # subscribe to factory logs
            logs_payload = {
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
            await ws.send(json.dumps(logs_payload))
            logs_resp = json.loads(await ws.recv())
            logs_sub_id = logs_resp.get("result")
            logger.info(f"subscribed to pool logs: {logs_sub_id}")

            async for raw_msg in ws:
                msg = json.loads(raw_msg)
                if "params" not in msg:
                    continue
                sub_id = msg["params"].get("subscription")
                result = msg["params"].get("result")
                if sub_id == heads_sub_id:
                    yield {"kind": "block", "data": result}
                elif sub_id == logs_sub_id:
                    yield {"kind": "pool_created", "data": result}
