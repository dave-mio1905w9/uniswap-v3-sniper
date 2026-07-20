import math
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Tuple

getcontext().prec = 60

Q96 = 2 ** 96
MIN_TICK = -887272
MAX_TICK = 887272
MIN_SQRT_RATIO = 4295128739
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342


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
    if sqrt_price_x96 <= 0:
        return Decimal(0)
    
    # don't convert to float midway, precision drops hard on large price gaps (e.g. SHIB/WETH)
    ratio = Decimal(sqrt_price_x96) / Decimal(Q96)
    price = ratio * ratio
    
    # shift by token decimal difference: token1_amount = token0_amount * price * 10^(dec1 - dec0)
    shift = Decimal(10) ** (dec0 - dec1)
    return price * shift


def tick_to_price(tick: int, dec0: int, dec1: int) -> Decimal:
    if tick < MIN_TICK or tick > MAX_TICK:
        raise ValueError(f"tick {tick} out of bounds [{MIN_TICK}, {MAX_TICK}]")
    base = Decimal("1.0001") ** tick
    shift = Decimal(10) ** (dec0 - dec1)
    return base * shift


def price_to_tick(price_dec: Decimal, dec0: int, dec1: int) -> int:
    if price_dec <= 0:
        return MIN_TICK
    shift = Decimal(10) ** (dec0 - dec1)
    raw_price = price_dec / shift
    # print(f"raw_price={raw_price}")
    t = int(math.floor(math.log(float(raw_price)) / math.log(1.0001)))
    return max(MIN_TICK, min(MAX_TICK, t))


def decode_slot0(data_bytes: bytes) -> Tuple[int, int, bool]:
    if len(data_bytes) < 32 * 7:
        # some RPCs return tightly packed or padded tuples differently
        data_bytes = data_bytes.rjust(224, b'\x00')

    sqrt_price = int.from_bytes(data_bytes[0:32], byteorder="big")
    
    # int24 is in the lowest 3 bytes of the 32-byte slot
    raw_tick = int.from_bytes(data_bytes[32:64], byteorder="big")
    # handle signed 24-bit
    val = raw_tick & 0xFFFFFF
    if val >= 0x800000:
        tick = val - 0x1000000
    else:
        tick = val
        
    unlocked = data_bytes[223] == 1
    return sqrt_price, tick, unlocked


def get_amount0_delta(sqrt_ratio_a: int, sqrt_ratio_b: int, liquidity: int) -> int:
    if sqrt_ratio_a > sqrt_ratio_b:
        sqrt_ratio_a, sqrt_ratio_b = sqrt_ratio_b, sqrt_ratio_a
    if sqrt_ratio_a == 0:
        return 0
    numerator = (liquidity << 96) * (sqrt_ratio_b - sqrt_ratio_a)
    return (numerator // sqrt_ratio_b) // sqrt_ratio_a


def get_amount1_delta(sqrt_ratio_a: int, sqrt_ratio_b: int, liquidity: int) -> int:
    if sqrt_ratio_a > sqrt_ratio_b:
        sqrt_ratio_a, sqrt_ratio_b = sqrt_ratio_b, sqrt_ratio_a
    return (liquidity * (sqrt_ratio_b - sqrt_ratio_a)) // Q96

# TODO: add liquidity delta support for tick range bounds if we ever do multi-tick swap estimation
