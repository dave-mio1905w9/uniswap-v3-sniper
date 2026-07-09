# sniper

Daemon listening to Uniswap v3 `PoolCreated` events over websocket, filtering by quote asset and pool size, then firing buy txs through the router.

## setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Set environment variables in `.env`:

```env
RPC_WS_URL=wss://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
RPC_HTTP_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
PRIVATE_KEY=0x...
BUY_AMOUNT_ETH=0.1
MAX_SLIPPAGE_BPS=300
```

## run

```bash
python -m sniper
```
