from bot.ciphers._shared import PASSTHROUGH
from bot.ciphers.caesar import encode as caesar_encode, decode as caesar_decode

__all__ = ["PASSTHROUGH", "encode", "decode"]


def encode(text: str, method: str, **params) -> str:
    if method == "Caesar":
        return caesar_encode(text, params.get("shift", 0))
    return text


def decode(text: str, method: str, **params) -> str:
    if method == "Caesar":
        return caesar_decode(text, params.get("shift", 0))
    return text
