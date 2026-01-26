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
            CREATE TABLE IF NOT EXISTS seen_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wallet_address, tx_hash)
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


async def is_tx_seen(wallet_address: str, tx_hash: str) -> bool:
    """Check if a transaction has been seen before."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM seen_transactions WHERE wallet_address = ? AND tx_hash = ?",
            (wallet_address.lower(), tx_hash.lower())
        )
        return await cursor.fetchone() is not None


async def mark_tx_seen(wallet_address: str, tx_hash: str):
    """Mark a transaction as seen."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        try:
            await db.execute(
                "INSERT INTO seen_transactions (wallet_address, tx_hash) VALUES (?, ?)",
                (wallet_address.lower(), tx_hash.lower())
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
