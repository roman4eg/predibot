import asyncio
import logging
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, POLLING_INTERVAL, PREDICT_WEB_URL
from database import (
    init_db,
    add_wallet,
    remove_wallet,
    get_wallets,
    get_all_wallets,
    toggle_orders,
    toggle_positions,
    is_order_seen,
    mark_order_seen,
    is_position_seen,
    mark_position_seen,
    get_wallet_by_address,
    get_last_check_time,
    update_last_check_time,
)
from predict_api import predictscan_api, Order, Position

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WALLET_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Global tracking task reference
_tracking_task: asyncio.Task | None = None


def is_valid_address(address: str) -> bool:
    """Validate Ethereum/BNB wallet address format."""
    return bool(WALLET_ADDRESS_PATTERN.match(address))


def format_order_message(order: Order, wallet_name: str) -> str:
    """Format order notification message."""
    timestamp = datetime.fromtimestamp(order.last_fill_time).strftime("%Y-%m-%d %H:%M:%S") if order.last_fill_time else ""

    # Build market title
    market_display = order.market_title or "Unknown Market"
    if order.parent_event_title:
        market_display = f"{order.parent_event_title} - {order.market_title}"

    # Price display (0-100 format from API, convert to 0-1)
    price_display = order.price
    if price_display > 1:
        price_display = price_display / 100

    return (
        f"**New Order** | {wallet_name}\n\n"
        f"**Market:** {market_display}\n"
        f"**Side:** {order.side}\n"
        f"**Price:** ${price_display:.4f}\n"
        f"**Shares:** {order.shares:.2f}\n"
        f"**Amount:** ${order.amount:.2f}\n"
        f"**Fee:** ${order.fee:.4f}\n"
        f"**Time:** {timestamp}\n\n"
        f"[View Order]({order.url})"
    )


def format_position_message(position: Position, wallet_name: str) -> str:
    """Format position notification message."""
    timestamp = datetime.fromtimestamp(position.snapshot_time).strftime("%Y-%m-%d %H:%M:%S") if position.snapshot_time else ""

    market_display = position.market_title or "Unknown Market"

    # Price display
    price_display = position.avg_price
    if price_display > 1:
        price_display = price_display / 100

    total_value = position.shares * price_display

    return (
        f"**New Position** | {wallet_name}\n\n"
        f"**Market:** {market_display}\n"
        f"**Shares:** {position.shares:.2f}\n"
        f"**Avg Price:** ${price_display:.4f}\n"
        f"**Value:** ${total_value:.2f}\n"
        f"**Time:** {timestamp}\n\n"
        f"[View on Predict.fun]({PREDICT_WEB_URL})"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "Welcome to Predict.fun Wallet Tracker Bot!\n\n"
        "Track wallet activity on Predict.fun prediction market.\n\n"
        "**Commands:**\n"
        "/add <address> <name> - Add wallet to track\n"
        "/remove <address> - Remove wallet from tracking\n"
        "/list - List all tracked wallets\n"
        "/settings - Manage notification settings\n"
        "/help - Show this help message\n\n"
        "Example:\n"
        "`/add 0x1234...abcd MyWallet`",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start(update, context)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command to add a wallet for tracking."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /add <wallet_address> <name>\n"
            "Example: `/add 0x1234...abcd MyWallet`",
            parse_mode="Markdown"
        )
        return

    address = context.args[0]
    name = " ".join(context.args[1:])

    if not is_valid_address(address):
        await update.message.reply_text(
            "Invalid wallet address format. Please provide a valid address starting with 0x."
        )
        return

    chat_id = update.effective_chat.id
    success = await add_wallet(chat_id, address, name)

    if success:
        await update.message.reply_text(
            f"Wallet **{name}** (`{address[:8]}...{address[-6:]}`) added successfully!\n\n"
            f"You will receive notifications for new orders and positions.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "This wallet is already being tracked."
        )


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remove command to remove a wallet from tracking."""
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /remove <wallet_address>\n"
            "Example: `/remove 0x1234...abcd`",
            parse_mode="Markdown"
        )
        return

    address = context.args[0]
    chat_id = update.effective_chat.id
    success = await remove_wallet(chat_id, address)

    if success:
        await update.message.reply_text(
            f"Wallet `{address[:8]}...{address[-6:]}` removed from tracking.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "Wallet not found in your tracking list."
        )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command to show all tracked wallets."""
    chat_id = update.effective_chat.id
    wallets = await get_wallets(chat_id)

    if not wallets:
        await update.message.reply_text(
            "You are not tracking any wallets.\n"
            "Use /add <address> <name> to add one."
        )
        return

    message = "**Tracked Wallets:**\n\n"
    for w in wallets:
        orders_status = "ON" if w.orders_enabled else "OFF"
        positions_status = "ON" if w.positions_enabled else "OFF"
        message += (
            f"**{w.name}**\n"
            f"`{w.wallet_address[:8]}...{w.wallet_address[-6:]}`\n"
            f"Orders: {orders_status} | Positions: {positions_status}\n\n"
        )

    await update.message.reply_text(message, parse_mode="Markdown")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command to manage notification settings."""
    chat_id = update.effective_chat.id

    if len(context.args) < 1:
        wallets = await get_wallets(chat_id)
        if not wallets:
            await update.message.reply_text(
                "You are not tracking any wallets.\n"
                "Use /add <address> <name> to add one."
            )
            return

        message = "**Select wallet to configure:**\n\n"
        keyboard = []
        for w in wallets:
            keyboard.append([
                InlineKeyboardButton(
                    f"{w.name} ({w.wallet_address[:8]}...)",
                    callback_data=f"settings:{w.wallet_address}"
                )
            ])

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    address = context.args[0]
    wallet = await get_wallet_by_address(chat_id, address)

    if not wallet:
        await update.message.reply_text("Wallet not found in your tracking list.")
        return

    await send_settings_menu(update.message, wallet)


async def send_settings_menu(message, wallet):
    """Send settings menu for a wallet."""
    orders_text = "ON" if wallet.orders_enabled else "OFF"
    positions_text = "ON" if wallet.positions_enabled else "OFF"

    keyboard = [
        [
            InlineKeyboardButton(
                f"Orders: {orders_text}",
                callback_data=f"toggle_orders:{wallet.wallet_address}"
            )
        ],
        [
            InlineKeyboardButton(
                f"Positions: {positions_text}",
                callback_data=f"toggle_positions:{wallet.wallet_address}"
            )
        ],
    ]

    await message.reply_text(
        f"**Settings for {wallet.name}**\n"
        f"`{wallet.wallet_address[:8]}...{wallet.wallet_address[-6:]}`\n\n"
        f"Tap buttons below to toggle notifications:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboard."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    data = query.data

    if data.startswith("settings:"):
        address = data.split(":")[1]
        wallet = await get_wallet_by_address(chat_id, address)
        if wallet:
            await send_settings_menu(query.message, wallet)
        return

    if data.startswith("toggle_orders:"):
        address = data.split(":")[1]
        wallet = await get_wallet_by_address(chat_id, address)
        if wallet:
            new_state = not wallet.orders_enabled
            await toggle_orders(chat_id, address, new_state)
            wallet = await get_wallet_by_address(chat_id, address)

            orders_text = "ON" if wallet.orders_enabled else "OFF"
            positions_text = "ON" if wallet.positions_enabled else "OFF"

            keyboard = [
                [
                    InlineKeyboardButton(
                        f"Orders: {orders_text}",
                        callback_data=f"toggle_orders:{wallet.wallet_address}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"Positions: {positions_text}",
                        callback_data=f"toggle_positions:{wallet.wallet_address}"
                    )
                ],
            ]

            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    if data.startswith("toggle_positions:"):
        address = data.split(":")[1]
        wallet = await get_wallet_by_address(chat_id, address)
        if wallet:
            new_state = not wallet.positions_enabled
            await toggle_positions(chat_id, address, new_state)
            wallet = await get_wallet_by_address(chat_id, address)

            orders_text = "ON" if wallet.orders_enabled else "OFF"
            positions_text = "ON" if wallet.positions_enabled else "OFF"

            keyboard = [
                [
                    InlineKeyboardButton(
                        f"Orders: {orders_text}",
                        callback_data=f"toggle_orders:{wallet.wallet_address}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"Positions: {positions_text}",
                        callback_data=f"toggle_positions:{wallet.wallet_address}"
                    )
                ],
            ]

            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return


async def check_wallet_updates(app: Application, wallet):
    """Check for new orders and positions for a wallet."""
    try:
        # Get last check time for this wallet
        last_check = await get_last_check_time(wallet.wallet_address)

        # Check orders
        if wallet.orders_enabled:
            orders = await predictscan_api.get_orders_by_maker(wallet.wallet_address, after_time=last_check)
            logger.info(f"Found {len(orders)} orders for {wallet.name}")

            for order in orders:
                if not order.order_hash:
                    continue

                if await is_order_seen(wallet.wallet_address, order.order_hash):
                    continue

                await mark_order_seen(wallet.wallet_address, order.order_hash)

                logger.info(f"Sending order notification: {order.order_hash[:16]}...")
                message = format_order_message(order, wallet.name)
                try:
                    await app.bot.send_message(
                        chat_id=wallet.chat_id,
                        text=message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send order notification: {e}")

        # Check positions
        if wallet.positions_enabled:
            positions = await predictscan_api.get_positions_by_address(wallet.wallet_address)
            logger.info(f"Found {len(positions)} positions for {wallet.name}")

            for position in positions:
                position_id = f"{position.asset_id}:{position.snapshot_time}"

                if await is_position_seen(wallet.wallet_address, position_id):
                    continue

                await mark_position_seen(wallet.wallet_address, position_id)

                logger.info(f"Sending position notification: {position.asset_id[:16]}...")
                message = format_position_message(position, wallet.name)
                try:
                    await app.bot.send_message(
                        chat_id=wallet.chat_id,
                        text=message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send position notification: {e}")

        # Update last check time
        await update_last_check_time(wallet.wallet_address)

    except Exception as e:
        logger.error(f"Error checking updates for {wallet.wallet_address}: {e}")


async def tracking_loop(app: Application):
    """Main tracking loop that checks for updates periodically."""
    logger.info("Starting tracking loop...")
    try:
        while True:
            try:
                wallets = await get_all_wallets()
                logger.info(f"Checking {len(wallets)} wallets...")
                for wallet in wallets:
                    logger.info(f"Checking wallet: {wallet.name} ({wallet.wallet_address[:10]}...)")
                    await check_wallet_updates(app, wallet)
                    await asyncio.sleep(1)  # Small delay between wallets
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in tracking loop: {e}")

            await asyncio.sleep(POLLING_INTERVAL)
    except asyncio.CancelledError:
        logger.info("Tracking loop cancelled")
        raise


async def post_init(app: Application):
    """Initialize database and start tracking loop after bot starts."""
    global _tracking_task
    await init_db()
    _tracking_task = asyncio.create_task(tracking_loop(app))


async def post_shutdown(app: Application):
    """Cleanup on bot shutdown."""
    global _tracking_task
    if _tracking_task and not _tracking_task.done():
        _tracking_task.cancel()
        try:
            await _tracking_task
        except asyncio.CancelledError:
            pass
    await predictscan_api.close()
    logger.info("Bot shutdown complete")


def main():
    """Main function to start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in environment variables")
        print("Please create a .env file based on .env.example")
        return

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("remove", remove_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
