import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
SISTER_GUILD_ID = int(os.getenv("SISTER_GUILD_ID", "0"))
SISTER_CHANNEL_ID = int(os.getenv("SISTER_CHANNEL_ID", "0"))

# Firebase credentials assembled from individual env vars
FIREBASE_CREDENTIALS = {
    "type": os.getenv("FIREBASE_TYPE", "service_account"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN", "googleapis.com"),
}

# Caesar shift: maps I -> 🐉 (U+1F409)
# This puts A-Z into 🐁-🐚 and a-z into 🐡-🐺
DEFAULT_CAESAR_SHIFT = ord("\U0001F409") - ord("I")  # 127936
