import os
from dataclasses import dataclass
from typing import Optional


def _get_env_or_fail(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise ValueError(f"missing required env var: {key}")
    return val.strip()


def _get_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes")


@dataclass
class Config:
    """Runtime configuration loaded from environment variables."""
    ws_url: str
    http_url: str
    private_key: str
    factory_address: str
    router_address: str
    weth_address: str
    buy_amount_eth: float
    max_slippage: float
    dry_run: bool = False

    @classmethod
    def load(cls) -> "Config":
        dry_run = _get_bool("DRY_RUN", False)
        
        # don't explode on empty key if we're only simulating
        pk = os.getenv("PRIVATE_KEY", "").strip()
        if not dry_run and not pk:
            raise ValueError("PRIVATE_KEY is required unless DRY_RUN=1")

        return cls(
            ws_url=_get_env_or_fail("RPC_WS_URL"),
            http_url=_get_env_or_fail("RPC_HTTP_URL"),
            private_key=pk,
            factory_address=os.getenv("FACTORY_ADDRESS", "0x1F98431c8aD98523631AE4a59f267346ea31F984"),
            router_address=os.getenv("ROUTER_ADDRESS", "0xE592427A0AEce92De3Edee1F18E0157C05861564"),
            weth_address=os.getenv("WETH_ADDRESS", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            buy_amount_eth=float(os.getenv("BUY_AMOUNT_ETH", "0.05")),
            max_slippage=float(os.getenv("MAX_SLIPPAGE_PCT", "2.5")),
            dry_run=dry_run,
        )
