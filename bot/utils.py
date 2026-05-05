import random
import asyncio

GARBAGE_MESSAGES = [
    "0x4E 0x55 0x4C 0x4C 0x00 0x00 0x00 0x00 0x00 0x00 0xFF 0xFE 0x00 0x00 0x00 0x00",
    (
        "[WARN] fd:7 unexpected EOF in handshake\n"
        "[WARN] fd:7 retry 1/3... connection reset\n"
        "[ERR] fd:7 handshake failed: ECONN_REFUSED"
    ),
    "\u2592\u2592\u2593\u2591\u2592\u2593\u2592\u2591\u2593\u2592\u2592\u2591\u2591\u2593\u2592\u2592\u2593\u2591\u2592\u2593\u2592\u2591\u2592\u2592\u2593\u2591\u2591\u2593\u2592\u2592\u2591\u2593\u2592",
    (
        "Traceback (most recent call last):\n"
        '  File "/usr/lib/python3.11/asyncio/ta\u2588\u2588\u2588\n'
        '  Fil\u2588 "/home/\u2588\u2588\u2588\u2588/\u2588\u2588\u2588.py", line \u2588\u2588\n'
        "    \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588"
    ),
    (
        "config:\n"
        "  host: !!binary |\n"
        "    R0lGODlhAQABAIAAAAAAAP///\n"
        "  port: null\n"
        "  upstream: [CORRUPTED]\n"
        "  retry: \u00ff\u00ff\u00ff\u00ff"
    ),
    (
        "\u2591" * 32 + "\n"
        "segfault at 0x0000000000000000 rip 0x00007f3a2c1b4e00\n"
        "rsp 0x00007fff5a8c9d08 error 4"
    ),
    (
        "IDENTITY=????\n"
        "SERVER=????\n"
        "DISC\u2588\u2588\u2588\u2588\u2588=????\n"
        "[FATAL] cannot resolve self\n"
        "[FATAL] cannot resolve self\n"
        "[FATAL] cannot resolve self"
    ),
    (
        "connecting......\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\n"
        "timeout\n"
        "retrying......\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\n"
        "timeout\n"
        "retrying......\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\n"
        "failed"
    ),
]


def get_garbage_messages():
    """Return the 8 garbage messages in a shuffled order."""
    msgs = GARBAGE_MESSAGES.copy()
    random.shuffle(msgs)
    return msgs


async def type_out_message(channel, text):
    """Send a message with a simulated typing effect via sequential edits."""
    if not text:
        return None

    chunks = []
    pos = 0
    # First chunk: short initial burst
    first_size = min(random.randint(8, 18), len(text))
    chunks.append(text[:first_size])
    pos = first_size

    # Subsequent chunks: variable sizes
    while pos < len(text):
        size = random.randint(4, 14)
        end = min(pos + size, len(text))
        chunks.append(text[pos:end])
        pos = end

    # Send initial chunk
    current_text = chunks[0]
    msg = await channel.send(current_text)

    # Edit in subsequent chunks — stay within rate limits (~5 edits / 5s)
    for chunk in chunks[1:]:
        await asyncio.sleep(random.uniform(0.8, 1.4))
        current_text += chunk
        await msg.edit(content=current_text)

    return msg
