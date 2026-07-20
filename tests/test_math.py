import pytest
import math
from sniper.pool import sqrt_price_x96_to_price, tick_to_price, tick_to_sqrt_price_x96


def test_sqrt_price_x96_one_to_one():
    # 1 << 96 in Q64.96 format represents price ratio = 1.0
    q96 = 2 ** 96
    price = sqrt_price_x96_to_price(q96, decimals_0=18, decimals_1=18)
    assert pytest.approx(price, rel=1e-6) == 1.0


def test_sqrt_price_x96_usdc_weth():
    # Realistic mainnet USDC/WETH pool state (USDC=6 dec, WETH=18 dec)
    # 1 token0 (USDC) = ~0.000333 token1 (WETH) when ETH is ~3000
    sqrt_price = 1445778809420042456456000000000
    price = sqrt_price_x96_to_price(sqrt_price, decimals_0=6, decimals_1=18)
    assert price > 0
    eth_price_in_usd = 1.0 / price
    assert 2000 < eth_price_in_usd < 5000


def test_inverted_decimals_8_and_18():
    # WBTC (8 dec) vs WETH (18 dec)
    q96 = 2 ** 96
    # price calculation must correctly scale 10^(8 - 18) = 10^-10
    price = sqrt_price_x96_to_price(q96, decimals_0=8, decimals_1=18)
    assert pytest.approx(price, rel=1e-6) == 1e-10


def test_tick_to_price_zero():
    # tick 0 is always 1.0 if decimals are equal
    price = tick_to_price(0, decimals_0=18, decimals_1=18)
    assert pytest.approx(price, rel=1e-9) == 1.0


def test_tick_to_sqrt_price_roundtrip():
    test_ticks = [-887220, -200000, -100, 0, 500, 85176, 887220]
    for tick in test_ticks:
        sqrt_p = tick_to_sqrt_price_x96(tick)
        # sqrt(1.0001^tick) * 2^96
        expected_sqrt = int(math.sqrt(1.0001 ** tick) * (2 ** 96))
        assert abs(sqrt_p - expected_sqrt) <= 1
