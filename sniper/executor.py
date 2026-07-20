import asyncio
import logging
import time
from web3 import AsyncWeb3
from eth_account import Account
from sniper.config import Config
from sniper.abi import ROUTER_V3_ABI

logger = logging.getLogger(__name__)


class SwapExecutor:
    """Builds and submits target buy transactions with gas escalation."""

    def __init__(self, w3: AsyncWeb3, config: Config):
        self.w3 = w3
        self.config = config
        self.account = Account.from_key(config.private_key)
        self.router = self.w3.eth.contract(
            address=AsyncWeb3.to_checksum_address(config.router_address),
            abi=ROUTER_V3_ABI,
        )

    async def calculate_gas_fees(self, bump_count: int = 0) -> tuple[int, int]:
        latest_block = await self.w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", 0)
        
        # Baseline multiplier + 12.5% per replacement round to satisfy geth node rules
        multiplier = 1.25 + (0.125 * bump_count)
        base_priority = AsyncWeb3.to_wei(self.config.priority_fee_gwei, "gwei")
        
        if bump_count > 0:
            # Geth requires at least 10% bump on priority fee too
            priority_fee = int(base_priority * (1.15 ** bump_count))
        else:
            priority_fee = base_priority

        max_fee = int(base_fee * multiplier) + priority_fee
        return max_fee, priority_fee

    async def submit_buy(
        self,
        token_in: str,
        token_out: str,
        fee: int,
        amount_in_wei: int,
        min_amount_out: int = 0,
    ) -> str:
        nonce = await self.w3.eth.get_transaction_count(self.account.address, "pending")
        latest_block = await self.w3.eth.get_block("latest")
        deadline = latest_block["timestamp"] + self.config.tx_deadline_seconds

        params = {
            "tokenIn": AsyncWeb3.to_checksum_address(token_in),
            "tokenOut": AsyncWeb3.to_checksum_address(token_out),
            "fee": fee,
            "recipient": self.account.address,
            "deadline": deadline,
            "amountIn": amount_in_wei,
            "amountOutMinimum": min_amount_out,
            "sqrtPriceLimitX96": 0,
        }

        tx_data = self.router.encode_abi("exactInputSingle", [params])
        is_eth_swap = token_in.lower() == self.config.weth_address.lower()

        for attempt in range(self.config.max_bump_retries + 1):
            max_fee, priority_fee = await self.calculate_gas_fees(bump_count=attempt)
            
            tx = {
                "to": self.router.address,
                "from": self.account.address,
                "value": amount_in_wei if is_eth_swap else 0,
                "data": tx_data,
                "nonce": nonce,
                "chainId": self.config.chain_id,
                "type": 2,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
                "gas": self.config.gas_limit,
            }

            # logger.debug("raw tx dict: %s", tx)
            signed = self.account.sign_transaction(tx)
            
            try:
                tx_hash = await self.w3.eth.send_raw_transaction(signed.rawTransaction)
                hash_hex = tx_hash.hex()
                logger.info("submitted swap attempt=%d hash=%s max_fee_gwei=%.2f", 
                            attempt, hash_hex, max_fee / 1e9)
            except Exception as e:
                err_msg = str(e).lower()
                if "already known" in err_msg or "replacement transaction underpriced" in err_msg:
                    logger.warning("mempool rejected tx on attempt %d: %s", attempt, e)
                    await asyncio.sleep(1.0)
                    continue
                raise e

            # Poll for receipt before next escalation round
            confirmed = await self._wait_for_receipt(tx_hash, timeout=self.config.bump_interval_seconds)
            if confirmed:
                return hash_hex
                
            logger.warning("tx %s not mined in %ds, bumping gas...", hash_hex, self.config.bump_interval_seconds)

        # FIXME: if all bump attempts expire, send a zero-value cancellation to unstick the nonce
        raise TimeoutError(f"swap tx with nonce {nonce} was not mined after {self.config.max_bump_retries} bumps")

    async def _wait_for_receipt(self, tx_hash, timeout: float) -> bool:
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    if receipt.get("status") == 1:
                        logger.info("tx confirmed in block %d gas_used=%d", receipt["blockNumber"], receipt["gasUsed"])
                        return True
                    else:
                        logger.error("tx reverted in block %d!", receipt["blockNumber"])
                        return True
            except Exception:
                pass
            await asyncio.sleep(1.0)
        return False
