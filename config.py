import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "30"))

PREDICT_WEB_URL = "https://predict.fun"
BSCSCAN_API_URL = "https://api.bscscan.com/api"

# Predict.fun contract addresses on BNB Mainnet
PREDICT_CONTRACTS = {
    "CTF_EXCHANGE": "0x8BC070BEdAB741406F4B1Eb65A72bee27894B689",
    "NEG_RISK_CTF_EXCHANGE": "0x365fb81bd4A24D6303cd2F19c349dE6894D8d58A",
    "CONDITIONAL_TOKENS": "0x22DA1810B194ca018378464a58f6Ac2B10C9d244",
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
}

# All contract addresses to monitor (lowercase for comparison)
MONITORED_CONTRACTS = [addr.lower() for addr in PREDICT_CONTRACTS.values()]
