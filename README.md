# sniper

Daemon listening to Uniswap v3 `PoolCreated` events over websocket, filtering by quote asset and pool size, then firing buy txs through the router.

Tested against Arbitrum and mainnet nodes (Alchemy & local Reth).

## setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy the example config:

```bash
cp .env.example .env
```

Key settings in `.env`:

- `RPC_WS_URL`: Full node websocket endpoint (needs `eth_subscribe`).
- `RPC_HTTP_URL`: HTTP endpoint for contract reads and simulation.
- `PRIVATE_KEY`: Signing key for router execution.
- `BUY_AMOUNT_ETH`: Size of buy in WETH/ETH.
- `GAS_BUMP_PERCENT`: Tip bump percentage on replacement tx (default: 20).
- `DRY_RUN`: Set to `true` to simulate txs without broadcasting.

## usage

```bash
# standard run with defaults from .env
sniper

# dry run listening to events without sending txs
sniper --dry-run

# override buy amount and quote token
sniper --amount 0.25 --quote 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
```

## tests

```bash
pytest
```

<!-- refreshed: 2026-09-25 -->
