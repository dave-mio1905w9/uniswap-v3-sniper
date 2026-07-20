import os
from dataclasses import dataclass


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


def _normalize_address(addr: str) -> str:
    addr = addr.strip()
    if not addr.startswith("0x") or len(addr) != 42:
        raise ValueError(f"invalid ethereum address: {addr}")
    return addr.lower()


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
    min_liquidity_eth: float
    gas_bump_percent: int
    max_gas_price_gwei: float
    dry_run: bool = False

    @classmethod
    def load(cls) -> "Config":
        dry_run = _get_bool("DRY_RUN", False)
        
        pk = os.getenv("PRIVATE_KEY", "").strip()
        if not dry_run and not pk:
            raise ValueError("PRIVATE_KEY is required unless DRY_RUN=1")

        factory = _normalize_address(os.getenv("FACTORY_ADDRESS", "0x1F98431c8aD98523631AE4a59f267346ea31F984"))
        router = _normalize_address(os.getenv("ROUTER_ADDRESS", "0xE592427A0AEce92De3Edee1F18E0157C05861564"))
        weth = _normalize_address(os.getenv("WETH_ADDRESS", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"))

        # gas bump shouldn't be under 10% or geth/reth drops the replacement tx
        bump_pct = int(os.getenv("GAS_BUMP_PERCENT", "15"))
        if bump_pct < 10:
            bump_pct = 10

        return cls(
            ws_url=_get_env_or_fail("RPC_WS_URL"),
            http_url=_get_env_or_fail("RPC_HTTP_URL"),
            private_key=pk,
            factory_address=factory,
            router_address=router,
            weth_address=weth,
            buy_amount_eth=float(os.getenv("BUY_AMOUNT_ETH", "0.05")),
            max_slippage=float(os.getenv("MAX_SLIPPAGE_PCT", "2.5")),
            min_liquidity_eth=float(os.getenv("MIN_LIQUIDITY_ETH", "0.5")),
            gas_bump_percent=bump_pct,
            max_gas_price_gwei=float(os.getenv("MAX_GAS_PRICE_GWEI", "120.0")),
            dry_run=dry_run,
        )
