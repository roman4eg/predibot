import aiohttp
from typing import Optional
from dataclasses import dataclass
from config import (
    ANKR_API_URL,
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


class AnkrAPI:
    def __init__(self):
        self.api_url = ANKR_API_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_id = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _rpc_request(self, method: str, params: dict) -> dict:
        session = await self._get_session()
        self._request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id
        }

        async with session.post(self.api_url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if "error" in data:
                    print(f"[DEBUG API] Error: {data['error']}")
                    return {}
                return data.get("result", {})
            else:
                text = await response.text()
                print(f"[DEBUG API] Request failed: {response.status} - {text}")
                return {}

    async def get_transactions(self, address: str) -> list[Transaction]:
        """Get all transactions for a wallet address using ANKR API."""
        all_transactions = []

        # 1. Get transactions by address
        try:
            params = {
                "address": address,
                "blockchain": ["bsc"],
                "pageSize": 50,
                "descOrder": True,
            }
            result = await self._rpc_request("ankr_getTransactionsByAddress", params)
            txs = result.get("transactions", [])
            print(f"[DEBUG] Regular txs: {len(txs)} for {address[:10]}...")

            for item in txs:
                tx = self._parse_transaction(item)
                if tx:
                    to_lower = tx.to_address.lower() if tx.to_address else ""
                    if to_lower in MONITORED_CONTRACTS:
                        print(f"[DEBUG] Found Predict tx: {tx.tx_hash[:16]}... to {tx.contract_name}")
                        all_transactions.append(tx)
        except Exception as e:
            print(f"Error fetching transactions: {e}")

        # 2. Get token transfers
        try:
            params = {
                "address": [address],
                "blockchain": ["bsc"],
                "pageSize": 50,
                "descOrder": True,
            }
            result = await self._rpc_request("ankr_getTokenTransfers", params)
            transfers = result.get("transfers", [])
            print(f"[DEBUG] Token transfers: {len(transfers)} for {address[:10]}...")

            for item in transfers:
                to_addr = item.get("toAddress", "").lower()
                from_addr = item.get("fromAddress", "").lower()
                contract_addr = item.get("contractAddress", "").lower()

                # Check if transfer involves Predict.fun contracts
                if to_addr in MONITORED_CONTRACTS or from_addr in MONITORED_CONTRACTS or contract_addr in MONITORED_CONTRACTS:
                    value = float(item.get("value", "0"))
                    decimals = int(item.get("tokenDecimals", 18))
                    value = value / (10 ** decimals) if decimals > 0 else value

                    tx = Transaction(
                        tx_hash=item.get("transactionHash", ""),
                        block_number=str(item.get("blockNumber", "")),
                        timestamp=item.get("timestamp", ""),
                        from_address=from_addr,
                        to_address=to_addr,
                        value=value,
                        contract_address=contract_addr,
                        method_id="",
                        function_name=f"{item.get('tokenSymbol', 'Token')} Transfer",
                        is_error=False,
                    )
                    print(f"[DEBUG] Found token transfer: {tx.tx_hash[:16]}... {value} {item.get('tokenSymbol')}")
                    all_transactions.append(tx)
        except Exception as e:
            print(f"Error fetching token transfers: {e}")

        return all_transactions

    def _parse_transaction(self, item: dict) -> Optional[Transaction]:
        """Parse transaction data from ANKR API response."""
        try:
            value_str = item.get("value", "0")
            # Handle hex values
            if isinstance(value_str, str) and value_str.startswith("0x"):
                value_wei = int(value_str, 16)
            else:
                value_wei = int(value_str) if value_str else 0
            value_bnb = value_wei / 1e18

            input_data = item.get("input", "")
            method_id = input_data[:10] if len(input_data) >= 10 else ""

            # Get method name from input or use default
            method_name = item.get("method", "")
            if not method_name and method_id:
                method_name = method_id

            return Transaction(
                tx_hash=item.get("hash", item.get("transactionHash", "")),
                block_number=str(item.get("blockNumber", "")),
                timestamp=str(item.get("timestamp", "")),
                from_address=item.get("from", item.get("fromAddress", "")),
                to_address=item.get("to", item.get("toAddress", "")),
                value=value_bnb,
                contract_address=item.get("contractAddress", ""),
                method_id=method_id,
                function_name=method_name,
                is_error=item.get("status") == "0" if "status" in item else False,
            )
        except Exception as e:
            print(f"Error parsing transaction: {e}")
            return None


# Global API instance
ankr_api = AnkrAPI()
