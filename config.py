import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PREDICT_API_KEY = os.getenv("PREDICT_API_KEY", "")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "30"))

PREDICT_API_BASE_URL = "https://api.predict.fun/v1"
PREDICT_WEB_URL = "https://predict.fun"
