import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "10"))

PREDICT_WEB_URL = "https://predict.fun"
PREDICTSCAN_API_URL = "http://predictdotfun.api.predictscan.dev:10004"
PREDICTSCAN_WS_URL = "ws://predictdotfun.api.predictscan.dev:10004/ws"
