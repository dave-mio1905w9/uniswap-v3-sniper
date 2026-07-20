import pytest
from sniper.pool import sqrt_price_x96_to_price


def test_sqrt_price_x96_one_to_one():
    # 1 << 96 in Q64.96 format represents price ratio = 1.0
    q96 = 2 ** 96
    price = sqrt_price_x96_to_price(q96, decimals_0=18, decimals_1=18)
    assert pytest.approx(price, rel=1e-6) == 1.0


def test_sqrt_price_x96_usdc_weth():
    # Realistic mainnet USDC/WETH pool state (USDC=6 dec, WETH=18 dec)
    # If ETH is around $3000, 1 token0 (USDC) is ~0.000333 token1 (WETH)
    sqrt_price = 1445778809420042456456000000000
    price = sqrt_price_x96_to_price(sqrt_price, decimals_0=6, decimals_1=18)
    assert price > 0
    eth_price_in_usd = 1.0 / price
    assert 2000 < eth_price_in_usd < 5000
