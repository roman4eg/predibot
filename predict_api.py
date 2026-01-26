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
                print(f"[DEBUG API] status={data.get('status')} message={data.get('message')}")
                if data.get("status") == "1":
                    return data.get("result", [])
                elif data.get("message") == "No transactions found":
                    return []
                else:
                    print(f"[DEBUG API] Full response: {data}")
                    return []
            else:
                text = await response.text()
                raise Exception(f"BscScan API request failed: {response.status} - {text}")

    async def get_transactions(self, address: str, start_block: int = 0) -> list[Transaction]:
        """Get all transactions for a wallet address."""
        all_transactions = []

        # 1. Get regular transactions
        try:
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": start_block,
                "endblock": 99999999,
                "sort": "desc",
                "page": 1,
                "offset": 50,
            }
            results = await self._request(params)
            print(f"[DEBUG] Regular txs: {len(results) if isinstance(results, list) else 0} for {address[:10]}...")
            for item in results:
                tx = self._parse_transaction(item)
                if tx and tx.to_address.lower() in MONITORED_CONTRACTS:
                    print(f"[DEBUG] Found Predict tx: {tx.tx_hash[:16]}... to {tx.contract_name}")
                    all_transactions.append(tx)
        except Exception as e:
            print(f"Error fetching regular txs: {e}")

        # 2. Get ERC-1155 NFT transfers (Conditional Tokens)
        try:
            params = {
                "module": "account",
                "action": "token1155tx",
                "address": address,
                "startblock": start_block,
                "endblock": 99999999,
                "sort": "desc",
                "page": 1,
                "offset": 50,
            }
            results = await self._request(params)
            print(f"[DEBUG] ERC-1155 txs: {len(results) if isinstance(results, list) else 0} for {address[:10]}...")
            for item in results:
                contract_addr = item.get("contractAddress", "").lower()
                if contract_addr == PREDICT_CONTRACTS["CONDITIONAL_TOKENS"].lower():
                    tx = Transaction(
                        tx_hash=item.get("hash", ""),
                        block_number=item.get("blockNumber", ""),
                        timestamp=item.get("timeStamp", ""),
                        from_address=item.get("from", ""),
                        to_address=item.get("to", ""),
                        value=float(item.get("tokenValue", 0)),
                        contract_address=contract_addr,
                        method_id="",
                        function_name="ERC1155 Transfer",
                        is_error=False,
                    )
                    print(f"[DEBUG] Found ERC-1155 tx: {tx.tx_hash[:16]}...")
                    all_transactions.append(tx)
        except Exception as e:
            print(f"Error fetching ERC-1155 txs: {e}")

        # 3. Get ERC-20 token transfers (USDT)
        try:
            params = {
                "module": "account",
                "action": "tokentx",
                "address": address,
                "startblock": start_block,
                "endblock": 99999999,
                "sort": "desc",
                "page": 1,
                "offset": 50,
            }
            results = await self._request(params)
            print(f"[DEBUG] ERC-20 txs: {len(results) if isinstance(results, list) else 0} for {address[:10]}...")
            for item in results:
                to_addr = item.get("to", "").lower()
                from_addr = item.get("from", "").lower()
                # Check if USDT transfer to/from Predict contracts
                if to_addr in MONITORED_CONTRACTS or from_addr in MONITORED_CONTRACTS:
                    decimals = int(item.get("tokenDecimal", 18))
                    value = float(item.get("value", 0)) / (10 ** decimals)
                    tx = Transaction(
                        tx_hash=item.get("hash", ""),
                        block_number=item.get("blockNumber", ""),
                        timestamp=item.get("timeStamp", ""),
                        from_address=from_addr,
                        to_address=to_addr,
                        value=value,
                        contract_address=item.get("contractAddress", ""),
                        method_id="",
                        function_name=f"{item.get('tokenSymbol', 'Token')} Transfer",
                        is_error=False,
                    )
                    print(f"[DEBUG] Found token tx: {tx.tx_hash[:16]}... {value} {item.get('tokenSymbol')}")
                    all_transactions.append(tx)
        except Exception as e:
            print(f"Error fetching ERC-20 txs: {e}")

        return all_transactions

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
