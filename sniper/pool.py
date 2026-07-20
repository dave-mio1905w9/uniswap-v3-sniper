import math
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Tuple

getcontext().prec = 50

Q96 = 2 ** 96
MIN_TICK = -887272
MAX_TICK = 887272


@dataclass
class PoolState:
    address: str
    token0: str
    token1: str
    fee: int
    sqrt_price_x96: int
    tick: int
    liquidity: int
    unlocked: bool


def sqrt_price_x96_to_price(sqrt_price_x96: int, dec0: int, dec1: int) -> Decimal:
    """Converts Q64.96 sqrtPrice to human-readable price of token0 in terms of token1."""
    if sqrt_price_x96 == 0:
        return Decimal(0)
    
    ratio = Decimal(sqrt_price_x96) / Decimal(Q96)
    price = ratio * ratio
    
    # adjust for decimal differences
    diff = dec0 - dec1
    if diff != 0:
        return price * (Decimal(10) ** diff)
    return price


def tick_to_price(tick: int, dec0: int, dec1: int) -> Decimal:
    base = Decimal("1.0001") ** tick
    diff = dec0 - dec1
    if diff != 0:
        return base * (Decimal(10) ** diff)
    return base


def price_to_tick(price_dec: Decimal, dec0: int, dec1: int) -> int:
    diff = dec0 - dec1
    raw_price = price_dec / (Decimal(10) ** diff)
    # 1.0001 base log
    return int(math.floor(math.log(float(raw_price)) / math.log(1.0001)))


def decode_slot0(data_hex: str) -> Tuple[int, int, bool]:
    # strip 0x prefix if present
    raw = data_hex[2:] if data_hex.startswith("0x") else data_hex
    
    # slot0 returns: (uint160 sqrtPriceX96, int24 tick, uint16 observationIndex,
    # uint16 observationCardinality, uint16 observationCardinalityNext, uint8 feeProtocol, bool unlocked)
    sqrt_price = int(raw[0:64], 16)
    
    tick_raw = int(raw[64:128], 16)
    # int24 two's complement sign fix
    if tick_raw >= 2**23:
        tick = tick_raw - 2**24
    else:
        tick = tick_raw
        
    unlocked = int(raw[384:448], 16) == 1
    return sqrt_price, tick, unlocked
