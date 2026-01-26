import aiosqlite
from typing import Optional
from dataclasses import dataclass

DATABASE_FILE = "predibot.db"


@dataclass
class WalletSettings:
    wallet_address: str
    name: str
    chat_id: int
    orders_enabled: bool = True
    positions_enabled: bool = True


async def init_db():
    """Initialize the database and create tables."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                name TEXT NOT NULL,
                orders_enabled INTEGER DEFAULT 1,
                positions_enabled INTEGER DEFAULT 1,
                UNIQUE(chat_id, wallet_address)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                order_hash TEXT NOT NULL,
                UNIQUE(wallet_address, order_hash)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                position_id TEXT NOT NULL,
                UNIQUE(wallet_address, position_id)
            )
        """)
        await db.commit()


async def add_wallet(chat_id: int, wallet_address: str, name: str) -> bool:
    """Add a wallet to track. Returns True if added, False if already exists."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        try:
            await db.execute(
                "INSERT INTO wallets (chat_id, wallet_address, name) VALUES (?, ?, ?)",
                (chat_id, wallet_address.lower(), name)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_wallet(chat_id: int, wallet_address: str) -> bool:
    """Remove a wallet from tracking. Returns True if removed."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "DELETE FROM wallets WHERE chat_id = ? AND wallet_address = ?",
            (chat_id, wallet_address.lower())
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_wallets(chat_id: int) -> list[WalletSettings]:
    """Get all wallets for a chat."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM wallets WHERE chat_id = ?",
            (chat_id,)
        )
        rows = await cursor.fetchall()
        return [
            WalletSettings(
                wallet_address=row["wallet_address"],
                name=row["name"],
                chat_id=row["chat_id"],
                orders_enabled=bool(row["orders_enabled"]),
                positions_enabled=bool(row["positions_enabled"])
            )
            for row in rows
        ]


async def get_all_wallets() -> list[WalletSettings]:
    """Get all wallets from all chats."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM wallets")
        rows = await cursor.fetchall()
        return [
            WalletSettings(
                wallet_address=row["wallet_address"],
                name=row["name"],
                chat_id=row["chat_id"],
                orders_enabled=bool(row["orders_enabled"]),
                positions_enabled=bool(row["positions_enabled"])
            )
            for row in rows
        ]


async def toggle_orders(chat_id: int, wallet_address: str, enabled: bool) -> bool:
    """Toggle orders notifications for a wallet."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "UPDATE wallets SET orders_enabled = ? WHERE chat_id = ? AND wallet_address = ?",
            (1 if enabled else 0, chat_id, wallet_address.lower())
        )
        await db.commit()
        return cursor.rowcount > 0


async def toggle_positions(chat_id: int, wallet_address: str, enabled: bool) -> bool:
    """Toggle positions notifications for a wallet."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "UPDATE wallets SET positions_enabled = ? WHERE chat_id = ? AND wallet_address = ?",
            (1 if enabled else 0, chat_id, wallet_address.lower())
        )
        await db.commit()
        return cursor.rowcount > 0


async def is_order_seen(wallet_address: str, order_hash: str) -> bool:
    """Check if an order has been seen before."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM seen_orders WHERE wallet_address = ? AND order_hash = ?",
            (wallet_address.lower(), order_hash)
        )
        return await cursor.fetchone() is not None


async def mark_order_seen(wallet_address: str, order_hash: str):
    """Mark an order as seen."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        try:
            await db.execute(
                "INSERT INTO seen_orders (wallet_address, order_hash) VALUES (?, ?)",
                (wallet_address.lower(), order_hash)
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            pass


async def is_position_seen(wallet_address: str, position_id: str) -> bool:
    """Check if a position has been seen before."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM seen_positions WHERE wallet_address = ? AND position_id = ?",
            (wallet_address.lower(), position_id)
        )
        return await cursor.fetchone() is not None


async def mark_position_seen(wallet_address: str, position_id: str):
    """Mark a position as seen."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        try:
            await db.execute(
                "INSERT INTO seen_positions (wallet_address, position_id) VALUES (?, ?)",
                (wallet_address.lower(), position_id)
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            pass


async def get_wallet_by_address(chat_id: int, wallet_address: str) -> Optional[WalletSettings]:
    """Get a specific wallet for a chat."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM wallets WHERE chat_id = ? AND wallet_address = ?",
            (chat_id, wallet_address.lower())
        )
        row = await cursor.fetchone()
        if row:
            return WalletSettings(
                wallet_address=row["wallet_address"],
                name=row["name"],
                chat_id=row["chat_id"],
                orders_enabled=bool(row["orders_enabled"]),
                positions_enabled=bool(row["positions_enabled"])
            )
        return None
