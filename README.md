# Predict.fun Wallet Tracker Bot

Telegram bot for tracking orders and positions on [Predict.fun](https://predict.fun) prediction market.

## Features

- Track multiple wallet addresses
- Receive notifications for new orders
- Receive notifications for new positions
- Toggle notifications separately for orders and positions
- Hyperlinks to markets on Predict.fun
- Price per share, shares amount, and total value in notifications

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
6. (Optional) Add Predict.fun API key for higher rate limits

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
| `PREDICT_API_KEY` | Predict.fun API key (optional) | - |
| `POLLING_INTERVAL` | Check interval in seconds | 30 |
