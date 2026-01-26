# Predict.fun Wallet Tracker Bot

Telegram bot for tracking wallet activity on [Predict.fun](https://predict.fun) prediction market on BNB Chain.

## Features

- Track multiple wallet addresses
- Receive notifications for new transactions with Predict.fun contracts
- Toggle notifications separately for orders and positions
- Transaction links to BscScan
- Contract method identification

## How it works

The bot monitors wallet transactions on BNB Chain using BscScan API and filters transactions that interact with Predict.fun smart contracts:

- **CTF Exchange** - Order filling and matching
- **NegRisk CTF Exchange** - NegRisk order operations
- **Conditional Tokens** - Position management

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
6. (Optional) Get BscScan API key from [bscscan.com/apis](https://bscscan.com/apis) for higher rate limits

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
| `BSCSCAN_API_KEY` | BscScan API key (optional) | - |
| `POLLING_INTERVAL` | Check interval in seconds | 30 |

## Predict.fun Contracts (BNB Mainnet)

| Contract | Address |
|----------|---------|
| CTF Exchange | `0x8BC070BEdAB741406F4B1Eb65A72bee27894B689` |
| NegRisk CTF Exchange | `0x365fb81bd4A24D6303cd2F19c349dE6894D8d58A` |
| Conditional Tokens | `0x22DA1810B194ca018378464a58f6Ac2B10C9d244` |
