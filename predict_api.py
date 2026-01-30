import aiohttp
from typing import Optional
from dataclasses import dataclass
from config import PREDICT_API_URL, PREDICT_API_KEY, PREDICT_WEB_URL


@dataclass
class OrderMatch:
    """Represents a filled order match event."""
    match_id: str
    order_hash: str
    maker: str
    market_id: str
    market_slug: str
    market_title: str
    outcome_index: int
    outcome_title: str
    side: str  # BUY or SELL
    price: float  # Price per share (0-1)
    shares: float  # Number of shares
    amount: float  # Total USDT amount
    fee: float
    executed_at: str  # ISO timestamp
    tx_hash: str

    @property
    def url(self) -> str:
        if self.market_slug:
            return f"{PREDICT_WEB_URL}/markets/{self.market_slug}"
        return f"{PREDICT_WEB_URL}/markets/{self.market_id}"

    @property
    def tx_url(self) -> str:
        if self.tx_hash:
            return f"https://bscscan.com/tx/{self.tx_hash}"
        return ""


@dataclass
class Position:
    """Represents a user position."""
    market_id: str
    market_slug: str
    market_title: str
    outcome_index: int
    outcome_title: str
    shares: float
    avg_price: float
    current_price: float
    value: float

    @property
    def url(self) -> str:
        if self.market_slug:
            return f"{PREDICT_WEB_URL}/markets/{self.market_slug}"
        return f"{PREDICT_WEB_URL}/markets/{self.market_id}"


class PredictAPI:
    """Client for official Predict.fun API."""

    def __init__(self):
        self.api_url = PREDICT_API_URL
        self.api_key = PREDICT_API_KEY
        self._session: Optional[aiohttp.ClientSession] = None
        self._markets_cache: dict = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: dict = None) -> dict:
        session = await self._get_session()
        url = f"{self.api_url}{endpoint}"
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    print(f"[DEBUG API] Request failed: {response.status} - {text[:200]}")
                    return {}
        except Exception as e:
            print(f"[DEBUG API] Exception: {e}")
            return {}

    async def get_order_matches(self, signer: str, first: int = 50, after: str = None) -> list[OrderMatch]:
        """Get order match events for a wallet address.

        Uses the /v1/orders/matches endpoint which returns filled orders
        filtered by signer (wallet address).
        """
        try:
            params = {"signer": signer.lower(), "first": first}
            if after:
                params["after"] = after

            result = await self._request("/v1/orders/matches", params)
            if not result:
                return []

            matches = []
            data = result.get("data", [])

            for item in data:
                market = item.get("market", {})
                outcome = item.get("outcome", {})

                match = OrderMatch(
                    match_id=item.get("id", ""),
                    order_hash=item.get("orderHash", ""),
                    maker=item.get("maker", ""),
                    market_id=market.get("id", ""),
                    market_slug=market.get("slug", ""),
                    market_title=market.get("title", ""),
                    outcome_index=outcome.get("index", 0),
                    outcome_title=outcome.get("title", ""),
                    side=item.get("side", "BUY"),
                    price=float(item.get("price", 0)),
                    shares=float(item.get("size", 0)),
                    amount=float(item.get("value", 0)),
                    fee=float(item.get("fee", 0)),
                    executed_at=item.get("executedAt", ""),
                    tx_hash=item.get("txHash", "")
                )
                matches.append(match)

            print(f"[DEBUG] Found {len(matches)} order matches for {signer[:10]}...")
            return matches
        except Exception as e:
            print(f"Error fetching order matches for {signer}: {e}")
            return []

    async def get_positions(self, address: str, first: int = 50) -> list[Position]:
        """Get positions for a wallet address.

        Note: This endpoint requires authentication with the wallet's JWT token,
        so it may not work for tracking other wallets without their permission.
        We'll try the public market data instead.
        """
        # The /v1/positions endpoint requires JWT auth for the specific wallet
        # So instead we return empty - positions will be inferred from order matches
        print(f"[DEBUG] Positions endpoint requires auth, skipping for {address[:10]}...")
        return []


# Global API instance
predict_api = PredictAPI()
