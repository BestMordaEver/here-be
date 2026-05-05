from bot.ciphers._shared import PASSTHROUGH


def encode(text: str, shift: int) -> str:
    """Shift ASCII letters by the given offset.
    Passthrough symbols (.,!?-:()) are kept as-is.
    Any character outside the dictionary is dropped.
    """
    result = []
    for ch in text:
        if "A" <= ch <= "Z" or "a" <= ch <= "z":
            result.append(chr(ord(ch) + shift))
        elif ch in PASSTHROUGH:
            result.append(ch)
        # else: drop
    return "".join(result)


def decode(text: str, shift: int) -> str:
    """Reverse a Caesar shift.
    Characters whose codepoint falls in the shifted letter ranges are decoded.
    Passthrough symbols are kept as-is. Everything else is dropped.
    """
    upper_lo = ord("A") + shift
    upper_hi = ord("Z") + shift
    lower_lo = ord("a") + shift
    lower_hi = ord("z") + shift
    result = []
    for ch in text:
        c = ord(ch)
        if upper_lo <= c <= upper_hi or lower_lo <= c <= lower_hi:
            result.append(chr(c - shift))
        elif ch in PASSTHROUGH:
            result.append(ch)
        # else: drop
    return "".join(result)
