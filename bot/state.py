import firebase_admin
from firebase_admin import credentials, firestore
import secrets

_app_initialized = False


def _init_firebase():
    global _app_initialized
    if _app_initialized:
        return
    from bot.config import FIREBASE_CREDENTIALS

    cred = credentials.Certificate(FIREBASE_CREDENTIALS)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    _app_initialized = True


def _default_state():
    host_string = secrets.token_hex(5)
    return {
        "phase": 0,
        "game_guild_id": None,
        "communications_channel_id": None,
        "discoveries_channel_id": None,
        "host_string": host_string,
        "config": {
            "server": secrets.token_hex(5),
            "communications_channel": None,
            "discovery_channel": secrets.token_hex(5),
            "host": host_string,
            "identity": "prox",
            "directory": "ERROR",
            "method": None,
            "shift": None,
        },
        "discovered_methods": ["Caesar"],
        "discovered_endpoints": [],
    }


class BotState:
    """Persistent bot state backed by Firestore."""

    def __init__(self):
        _init_firebase()
        self.db = firestore.client()
        self.doc_ref = self.db.collection("bot_state").document("proxy")
        self._data = {}

    def load(self):
        doc = self.doc_ref.get()
        if doc.exists:
            self._data = doc.to_dict()
        else:
            self._data = _default_state()
            self._persist()
        return self._data

    def _persist(self):
        self.doc_ref.set(self._data)

    def reset(self):
        self._data = _default_state()
        self._persist()

    # ── Phase ────────────────────────────────────────────

    @property
    def phase(self):
        return self._data.get("phase", 0)

    @phase.setter
    def phase(self, value):
        self._data["phase"] = value
        self._persist()

    # ── Guild & Channels ────────────────────────────────

    @property
    def game_guild_id(self):
        return self._data.get("game_guild_id")

    @game_guild_id.setter
    def game_guild_id(self, value):
        self._data["game_guild_id"] = value
        self._persist()

    @property
    def communications_channel_id(self):
        return self._data.get("communications_channel_id")

    @communications_channel_id.setter
    def communications_channel_id(self, value):
        self._data["communications_channel_id"] = value
        # Keep the display config in sync with the real channel ID
        self._data["config"]["communications_channel"] = str(value)
        self._persist()

    @property
    def discoveries_channel_id(self):
        return self._data.get("discoveries_channel_id")

    @discoveries_channel_id.setter
    def discoveries_channel_id(self, value):
        self._data["discoveries_channel_id"] = value
        self._persist()

    @property
    def host_string(self):
        return self._data.get("host_string", "")

    # ── Config ──────────────────────────────────────────

    @property
    def config(self):
        return self._data.get("config", {})

    def set_config(self, key, value):
        self._data["config"][key] = value
        self._persist()

    # ── Discovered methods / endpoints ──────────────────

    @property
    def discovered_methods(self):
        return self._data.get("discovered_methods", ["Caesar"])

    @property
    def discovered_endpoints(self):
        return self._data.get("discovered_endpoints", [])

    def add_endpoint(self, url):
        endpoints = self._data.get("discovered_endpoints", [])
        if url not in endpoints:
            endpoints.append(url)
            self._data["discovered_endpoints"] = endpoints
            # Also update the directory config display
            directory = self._data["config"].get("directory")
            if isinstance(directory, list):
                directory.append(url)
            else:
                self._data["config"]["directory"] = [url]
            self._persist()
