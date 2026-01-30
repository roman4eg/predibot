# Predict.fun Wallet Tracker Bot

Telegram bot for tracking wallet activity on [Predict.fun](https://predict.fun) prediction market on BNB Chain.

## Features

- Track multiple wallet addresses
- Receive notifications for new orders and positions
- Toggle notifications separately for orders and positions
- Links to order details and markets
- Price, shares quantity, and USD value in notifications

## How it works

The bot monitors wallet activity using the [Predictscan API](https://predictdotfun.predictscan.dev/dataapi) which provides:

- **Orders** - Filled orders with price, shares, and amounts
- **Positions** - Current positions with average price and value

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
4. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)
5. Add token to `.env` file

## Usage

Start the bot:
```bash
python bot.py
```

## Bot Commands

- `/start` - Welcome message and help
- `/add <address> <name>` - Add wallet to track
- `/remove <address>` - Remove wallet from tracking
- `/list` - List all tracked wallets
- `/settings` - Manage notification settings
- `/help` - Show help message

## Example

```
/add 0x1234567890abcdef1234567890abcdef12345678 MyWallet
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (required) | - |
| `POLLING_INTERVAL` | Check interval in seconds | 30 |
