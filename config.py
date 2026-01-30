import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "10"))

PREDICT_WEB_URL = "https://predict.fun"
# Official Predict.fun API
PREDICT_API_URL = os.getenv("PREDICT_API_URL", "https://api.predict.fun")
PREDICT_API_KEY = os.getenv("PREDICT_API_KEY", "")
