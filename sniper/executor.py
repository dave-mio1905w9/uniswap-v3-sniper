import asyncio
import logging
from web3 import AsyncWeb3
from eth_account import Account
from sniper.config import Config
from sniper.abi import ROUTER_V3_ABI

logger = logging.getLogger(__name__)


class SwapExecutor:
    def __init__(self, w3: AsyncWeb3, config: Config):
        self.w3 = w3
        self.config = config
        self.account = Account.from_key(config.private_key)
        self.router = self.w3.eth.contract(
            address=AsyncWeb3.to_checksum_address(config.router_address),
            abi=ROUTER_V3_ABI,
        )

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
        base_fee = latest_block["baseFeePerGas"]
        
        # 20% over base + static priority
        max_priority = AsyncWeb3.to_wei(self.config.priority_fee_gwei, "gwei")
        max_fee = int(base_fee * 1.2) + max_priority

        deadline = latest_block["timestamp"] + 180

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

        tx = {
            "to": self.router.address,
            "from": self.account.address,
            "value": amount_in_wei if token_in.lower() == self.config.weth_address.lower() else 0,
            "data": tx_data,
            "nonce": nonce,
            "chainId": self.config.chain_id,
            "type": 2,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority,
            "gas": self.config.gas_limit,
        }

        signed = self.account.sign_transaction(tx)
        tx_hash = await self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()
