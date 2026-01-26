import aiohttp
from typing import Optional
from dataclasses import dataclass
from config import PREDICT_API_BASE_URL, PREDICT_API_KEY, PREDICT_WEB_URL


@dataclass
class Order:
    order_hash: str
    maker: str
    token_id: str
    market_slug: str
    market_title: str
    outcome: str
    side: str  # BUY or SELL
    price_per_share: float
    shares_amount: float
    total_value: float
    status: str
    created_at: str

    @property
    def url(self) -> str:
        return f"{PREDICT_WEB_URL}/market/{self.market_slug}"


@dataclass
class Position:
    position_id: str
    maker: str
    market_slug: str
    market_title: str
    outcome: str
    shares_amount: float
    avg_price: float
    total_value: float
    current_price: float
    pnl: float
    created_at: str

    @property
    def url(self) -> str:
        return f"{PREDICT_WEB_URL}/market/{self.market_slug}"


class PredictAPI:
    def __init__(self):
        self.base_url = PREDICT_API_BASE_URL
        self.api_key = PREDICT_API_KEY
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, endpoint: str, params: dict = None) -> dict:
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        async with session.request(method, url, params=params) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return {"data": []}
            else:
                text = await response.text()
                raise Exception(f"API request failed: {response.status} - {text}")

    async def get_orders_by_maker(self, maker_address: str) -> list[Order]:
        """Get all orders for a specific maker address."""
        try:
            data = await self._request("GET", "/orders", params={"maker": maker_address})
            orders = []
            for item in data.get("data", data.get("orders", [])):
                order = self._parse_order(item, maker_address)
                if order:
                    orders.append(order)
            return orders
        except Exception as e:
            print(f"Error fetching orders for {maker_address}: {e}")
            return []

    async def get_positions_by_maker(self, maker_address: str) -> list[Position]:
        """Get all positions for a specific maker address."""
        try:
            data = await self._request("GET", "/positions", params={"maker": maker_address})
            positions = []
            for item in data.get("data", data.get("positions", [])):
                position = self._parse_position(item, maker_address)
                if position:
                    positions.append(position)
            return positions
        except Exception as e:
            print(f"Error fetching positions for {maker_address}: {e}")
            return []

    async def get_market_activity(self, maker_address: str) -> list[dict]:
        """Get market activity for a specific maker address."""
        try:
            data = await self._request("GET", "/activity", params={"maker": maker_address})
            return data.get("data", data.get("activity", []))
        except Exception as e:
            print(f"Error fetching activity for {maker_address}: {e}")
            return []

    def _parse_order(self, item: dict, maker_address: str) -> Optional[Order]:
        """Parse order data from API response."""
        try:
            maker_amount = float(item.get("makerAmount", 0)) / 1e6  # USDT has 6 decimals
            taker_amount = float(item.get("takerAmount", 0)) / 1e6
            price_per_share = float(item.get("pricePerShare", item.get("price", 0)))

            if maker_amount > 0:
                shares = maker_amount / price_per_share if price_per_share > 0 else 0
            else:
                shares = taker_amount / (1 - price_per_share) if price_per_share < 1 else 0

            market = item.get("market", {})
            outcome_token = item.get("outcomeToken", {})

            return Order(
                order_hash=item.get("hash", item.get("id", "")),
                maker=item.get("maker", maker_address),
                token_id=item.get("tokenId", ""),
                market_slug=market.get("slug", item.get("marketSlug", "")),
                market_title=market.get("title", item.get("marketTitle", "Unknown Market")),
                outcome=outcome_token.get("name", item.get("outcome", "Unknown")),
                side=item.get("side", "BUY"),
                price_per_share=price_per_share,
                shares_amount=shares,
                total_value=maker_amount if maker_amount > 0 else taker_amount,
                status=item.get("status", "OPEN"),
                created_at=item.get("createdAt", item.get("timestamp", ""))
            )
        except Exception as e:
            print(f"Error parsing order: {e}")
            return None

    def _parse_position(self, item: dict, maker_address: str) -> Optional[Position]:
        """Parse position data from API response."""
        try:
            market = item.get("market", {})
            outcome_token = item.get("outcomeToken", {})

            shares = float(item.get("shares", item.get("amount", 0))) / 1e6
            avg_price = float(item.get("avgPrice", item.get("averagePrice", 0)))
            current_price = float(item.get("currentPrice", item.get("price", avg_price)))
            total_value = shares * avg_price
            pnl = shares * (current_price - avg_price)

            position_id = item.get("id", f"{item.get('marketId', '')}-{item.get('tokenId', '')}")

            return Position(
                position_id=position_id,
                maker=item.get("maker", maker_address),
                market_slug=market.get("slug", item.get("marketSlug", "")),
                market_title=market.get("title", item.get("marketTitle", "Unknown Market")),
                outcome=outcome_token.get("name", item.get("outcome", "Unknown")),
                shares_amount=shares,
                avg_price=avg_price,
                total_value=total_value,
                current_price=current_price,
                pnl=pnl,
                created_at=item.get("createdAt", item.get("timestamp", ""))
            )
        except Exception as e:
            print(f"Error parsing position: {e}")
            return None


# Global API instance
predict_api = PredictAPI()
