import aiohttp
from typing import Optional
from dataclasses import dataclass
from config import (
    BSCSCAN_API_URL,
    BSCSCAN_API_KEY,
    PREDICT_WEB_URL,
    PREDICT_CONTRACTS,
    MONITORED_CONTRACTS,
)


@dataclass
class Transaction:
    tx_hash: str
    block_number: str
    timestamp: str
    from_address: str
    to_address: str
    value: float
    contract_address: str
    method_id: str
    function_name: str
    is_error: bool

    @property
    def url(self) -> str:
        return f"https://bscscan.com/tx/{self.tx_hash}"

    @property
    def contract_name(self) -> str:
        to_lower = self.to_address.lower()
        for name, addr in PREDICT_CONTRACTS.items():
            if addr.lower() == to_lower:
                return name.replace("_", " ").title()
        return "Unknown Contract"


class BscScanAPI:
    def __init__(self):
        self.api_url = BSCSCAN_API_URL
        self.api_key = BSCSCAN_API_KEY
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, params: dict) -> dict:
        session = await self._get_session()
        if self.api_key:
            params["apikey"] = self.api_key
        async with session.get(self.api_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "1":
                    return data.get("result", [])
                elif data.get("message") == "No transactions found":
                    return []
                else:
                    return []
            else:
                text = await response.text()
                raise Exception(f"BscScan API request failed: {response.status} - {text}")

    async def get_transactions(self, address: str, start_block: int = 0) -> list[Transaction]:
        """Get all transactions for a wallet address."""
        try:
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": start_block,
                "endblock": 99999999,
                "sort": "desc",
                "page": 1,
                "offset": 100,
            }
            results = await self._request(params)
            transactions = []
            for item in results:
                tx = self._parse_transaction(item)
                if tx and tx.to_address.lower() in MONITORED_CONTRACTS:
                    transactions.append(tx)
            return transactions
        except Exception as e:
            print(f"Error fetching transactions for {address}: {e}")
            return []

    async def get_internal_transactions(self, address: str, start_block: int = 0) -> list[Transaction]:
        """Get internal transactions for a wallet address."""
        try:
            params = {
                "module": "account",
                "action": "txlistinternal",
                "address": address,
                "startblock": start_block,
                "endblock": 99999999,
                "sort": "desc",
                "page": 1,
                "offset": 100,
            }
            results = await self._request(params)
            transactions = []
            for item in results:
                tx = self._parse_transaction(item)
                if tx:
                    transactions.append(tx)
            return transactions
        except Exception as e:
            print(f"Error fetching internal transactions for {address}: {e}")
            return []

    async def get_token_transfers(self, address: str, start_block: int = 0) -> list[dict]:
        """Get ERC20 token transfers for a wallet address."""
        try:
            params = {
                "module": "account",
                "action": "tokentx",
                "address": address,
                "startblock": start_block,
                "endblock": 99999999,
                "sort": "desc",
                "page": 1,
                "offset": 100,
            }
            results = await self._request(params)
            transfers = []
            for item in results:
                # Filter for USDT transfers to/from Predict contracts
                contract_addr = item.get("contractAddress", "").lower()
                to_addr = item.get("to", "").lower()
                from_addr = item.get("from", "").lower()

                if contract_addr == PREDICT_CONTRACTS["USDT"].lower():
                    if to_addr in MONITORED_CONTRACTS or from_addr in MONITORED_CONTRACTS:
                        transfers.append({
                            "tx_hash": item.get("hash", ""),
                            "block_number": item.get("blockNumber", ""),
                            "timestamp": item.get("timeStamp", ""),
                            "from": item.get("from", ""),
                            "to": item.get("to", ""),
                            "value": float(item.get("value", 0)) / 1e18,
                            "token_symbol": item.get("tokenSymbol", ""),
                            "token_decimal": item.get("tokenDecimal", "18"),
                        })
            return transfers
        except Exception as e:
            print(f"Error fetching token transfers for {address}: {e}")
            return []

    def _parse_transaction(self, item: dict) -> Optional[Transaction]:
        """Parse transaction data from BscScan API response."""
        try:
            value_wei = int(item.get("value", 0))
            value_bnb = value_wei / 1e18

            input_data = item.get("input", "")
            method_id = input_data[:10] if len(input_data) >= 10 else ""
            function_name = item.get("functionName", "").split("(")[0] if item.get("functionName") else ""

            return Transaction(
                tx_hash=item.get("hash", ""),
                block_number=item.get("blockNumber", ""),
                timestamp=item.get("timeStamp", ""),
                from_address=item.get("from", ""),
                to_address=item.get("to", ""),
                value=value_bnb,
                contract_address=item.get("contractAddress", ""),
                method_id=method_id,
                function_name=function_name,
                is_error=item.get("isError", "0") == "1",
            )
        except Exception as e:
            print(f"Error parsing transaction: {e}")
            return None


# Global API instance
bscscan_api = BscScanAPI()
