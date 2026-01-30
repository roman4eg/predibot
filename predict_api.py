import aiohttp
from typing import Optional
from dataclasses import dataclass
from config import PREDICTSCAN_API_URL, PREDICT_WEB_URL


@dataclass
class Order:
    order_hash: str
    maker: str
    asset_id: str
    amount: float  # USDT amount
    shares: float  # Token quantity
    fee: float
    side: str  # BUY or SELL
    price: float
    fill_count: int
    first_fill_time: int
    last_fill_time: int
    tx_hashes: list[str]
    market_title: str = ""
    parent_event_title: str = ""

    @property
    def url(self) -> str:
        return f"https://predictdotfun.predictscan.dev/order?orderHash={self.order_hash}"

    @property
    def tx_url(self) -> str:
        if self.tx_hashes:
            return f"https://bscscan.com/tx/{self.tx_hashes[-1]}"
        return ""


@dataclass
class Position:
    maker: str
    asset_id: str
    shares: float
    avg_price: float
    snapshot_time: int
    market_title: str = ""
    condition_id: str = ""

    @property
    def url(self) -> str:
        return f"{PREDICT_WEB_URL}"


class PredictscanAPI:
    def __init__(self):
        self.api_url = PREDICTSCAN_API_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._markets_cache: dict = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: dict = None) -> dict:
        session = await self._get_session()
        url = f"{self.api_url}{endpoint}"
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        return data
                    else:
                        print(f"[DEBUG API] Error: {data.get('error', {}).get('message', 'Unknown error')}")
                        return {}
                else:
                    text = await response.text()
                    print(f"[DEBUG API] Request failed: {response.status} - {text[:200]}")
                    return {}
        except Exception as e:
            print(f"[DEBUG API] Exception: {e}")
            return {}

    async def get_market_by_asset(self, asset_id: str) -> dict:
        """Get market info by asset ID."""
        if asset_id in self._markets_cache:
            return self._markets_cache[asset_id]

        result = await self._request(f"/api/markets/by-asset/{asset_id}")
        if result.get("success"):
            market = result.get("data", {})
            self._markets_cache[asset_id] = market
            return market
        return {}

    async def get_orders_by_maker(self, maker_address: str, after_time: int = 0) -> list[Order]:
        """Get orders by maker address."""
        try:
            params = {"limit": 100}
            if after_time > 0:
                params["afterTime"] = after_time

            result = await self._request(f"/api/orders/by-maker/{maker_address}", params)
            if not result.get("success"):
                return []

            orders = []
            for item in result.get("data", []):
                # Get market info for title
                asset_id = item.get("assetId", "")
                market = await self.get_market_by_asset(asset_id) if asset_id else {}

                order = Order(
                    order_hash=item.get("orderHash", ""),
                    maker=item.get("maker", ""),
                    asset_id=asset_id,
                    amount=float(item.get("amount", 0)),
                    shares=float(item.get("shares", 0)),
                    fee=float(item.get("fee", 0)),
                    side=item.get("sideStr", item.get("side", "BUY")),
                    price=float(item.get("price", 0)),
                    fill_count=int(item.get("fillCount", 0)),
                    first_fill_time=int(item.get("firstFillTime", 0)),
                    last_fill_time=int(item.get("lastFillTime", 0)),
                    tx_hashes=item.get("txHashes", []),
                    market_title=market.get("marketTitle", item.get("marketTitle", "")),
                    parent_event_title=market.get("parentEvent", {}).get("title", item.get("parentEventTitle", ""))
                )
                orders.append(order)

            print(f"[DEBUG] Found {len(orders)} orders for {maker_address[:10]}...")
            return orders
        except Exception as e:
            print(f"Error fetching orders for {maker_address}: {e}")
            return []

    async def get_positions_by_address(self, address: str) -> list[Position]:
        """Get positions by address."""
        try:
            params = {"limit": 100, "includeConditionId": "true"}
            result = await self._request(f"/api/user/positions/{address}", params)
            if not result.get("success"):
                return []

            data = result.get("data", {})
            positions_data = data.get("data", []) if isinstance(data, dict) else data

            positions = []
            for item in positions_data:
                asset_id = item.get("assetId", "")
                market = await self.get_market_by_asset(asset_id) if asset_id else {}

                position = Position(
                    maker=item.get("maker", ""),
                    asset_id=asset_id,
                    shares=float(item.get("shares", 0)),
                    avg_price=float(item.get("avgPrice", 0)),
                    snapshot_time=int(item.get("snapshotTime", 0)),
                    market_title=market.get("marketTitle", ""),
                    condition_id=item.get("conditionId", "")
                )
                positions.append(position)

            print(f"[DEBUG] Found {len(positions)} positions for {address[:10]}...")
            return positions
        except Exception as e:
            print(f"Error fetching positions for {address}: {e}")
            return []


# Global API instance
predictscan_api = PredictscanAPI()
