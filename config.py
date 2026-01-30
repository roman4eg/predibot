import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "10"))

PREDICT_WEB_URL = "https://predict.fun"
# Try HTTPS version of Predictscan API
PREDICTSCAN_API_URL = os.getenv("PREDICTSCAN_API_URL", "https://predictdotfun.predictscan.dev")
PREDICTSCAN_WS_URL = "wss://predictdotfun.predictscan.dev/ws"
