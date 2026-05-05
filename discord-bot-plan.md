# Discord Bot Plan - "Proxy"

## Overview

A Discord bot that acts as a character in the ARG — a broken proxy system that players repair, configure, and eventually communicate through. The bot progresses through phases, starting as a malfunctioning program and evolving into a real-time communication channel with cipher-encoded messages.

Two servers are involved:
- **Sister server** — pre-existing, has a dedicated channel. Operator-facing (the person behind Proxy).
- **Game server** — created by the bot on startup. Player-facing.

---

## Phase 0: Genesis

**Trigger:** Bot starts up.

**Actions:**
1. Bot creates a new guild (the game server) with two text channels:
   - `#communications`
   - `#discoveries`
2. Bot generates a permanent invite link to the game server.
3. Bot posts the invite link in the sister server's dedicated channel.
4. Bot registers a single slash command: `/ping`
5. `/ping` is available in the game server only.

**Transition:** A player uses `/ping` in the game server → Phase 1 begins.

**Implementation notes:**
- Bot needs `guilds` and `manage_guild` intents, plus guild creation permissions.
- Store the game server ID, channel IDs, and phase state in a persistent store (SQLite or JSON file).
- The `/ping` response can be something minimal and ominous — a single `PONG` or a timestamp, then the bot immediately transitions.

---

## Phase 1: Boot Sequence

**Trigger:** `/ping` is used.

**Actions:**
1. Bot posts 8 messages of garbage text in `#communications` — random hex dumps, malformed logs, unicode noise, partial stack traces. Spaced out over a few seconds each for dramatic effect.
2. After the garbage, bot posts a clean error message:
   ```
   /home/a8f3c1d9e7/Proxy: multiple configuration errors - SERVER_ID_MISMATCH, DISCOVERIES_ID_MISMATCH, IDENTITY_MISMATCH
   ```
   (The path string `a8f3c1d9e7` is a random hex string, generated once and stored.)
3. A new slash command becomes available: `/configure`
   - Optional arg: `parameter_name` (string)
   - Optional arg: `parameter_value` (string)

**`/configure` behavior:**

Without arguments, prints current configuration:
```
Server — a8f3c1d9e7
Communications channel — <actual communications channel ID>
Discovery channel — b4e2f7a901
Host — a8f3c1d9e7
Identity — prox
Directory — ERROR
```

- `Communications channel` is already correct (real ID) — a red herring / anchor point.
- `Server`, `Discovery channel`, and `Identity` are the three broken values.
- All other parameter names (including `Communications channel`, `Host`, `Directory`) respond with: `ERROR — this action will disturb homeostasis`

**Resolution:**
| Parameter | Correct Value | How Players Find It |
|-----------|--------------|-------------------|
| `Server` | Current guild ID | Copy server ID from Discord |
| `Discovery channel` | `#discoveries` channel ID | Copy channel ID from Discord |
| `Identity` | `Proxy` | The error says "prox" — close but wrong. The error path says "Proxy". |

Each correct `/configure` updates the stored value and prints a confirmation like:
```
Server — 1234567890 ✓ UPDATED
```

Wrong values get:
```
Server — <attempted value> ✗ REJECTED
```

**Transition:** All three values are corrected → Phase 2 begins. Bot posts:
```
/home/a8f3c1d9e7/Proxy: configuration resolved. Establishing connection...
```

**Implementation notes:**
- `/configure` should have autocomplete on `parameter_name` listing only the visible config keys.
- Persist configuration state so it survives restarts.
- The garbage messages should look like a boot sequence — mix of recognizable-but-broken output. Examples:
  - `0x4E 0x55 0x4C 0x4C 0x00 0x00 0x00 0x00 0x00...`
  - `[WARN] fd:7 unexpected EOF in handshake`
  - `▒▒▓░▒▓▒░▓▒▒░░▓▒▒▓░▒`
  - Partial Python tracebacks, corrupted config YAML fragments, etc.

---

## Phase 2: Connection Established

**Trigger:** Phase 1 configuration is resolved.

**Immediate changes:**
- `Host` in `/configure` output changes from `a8f3c1d9e7` to `here-be`
- Two new config entries appear:
  ```
  Method — Caesar
  Shift — <N>
  ```
  where N is chosen so that the letter `I` shifted by N maps to 🐉 (U+1F409). See cipher discussion below.
- `Directory` resolves to an initially empty list — this is the live index of discovered endpoints on the site. As players find pages, they are announced in `#discoveries` and added here.

**Shift 0 = Factory Reset:**
If a player sets `Shift` to `0` via `/configure`, the bot resets to Phase 0. Full wipe — guild gets recreated, state cleared. This is the self-destruct button. Since the Caesar shift puts letters deep into emoji-land, players might learn to "speak emoji" and communicate with Proxy in ciphertext. Setting shift to 0 is the one thing they must NOT do.

**The `/talk` command (sister server only):**
- Registered only in the sister server.
- Accepts a `message` string argument.
- The operator types a message; the bot relays it to `#communications` in the game server.

**Typing effect:**
1. Bot sends an initial short segment of the message (first ~10-20 chars).
2. Rapidly edits the message to append further chunks (every 100-300ms), simulating real-time typing.
3. Final edit contains the complete message.

**Message queue:**
- If `/talk` is used while a message is still being "typed out", the new message is buffered.
- After the current message finishes, the next one begins after a short pause (~1-2 seconds).
- Queue is FIFO. Multiple messages play out in sequence.

**Implementation notes:**
- Use `discord.Message.edit()` for the typing effect.
- Chunk sizes can vary slightly for realism (not perfectly uniform).
- Rate limits: Discord allows ~5 edits per 5 seconds per message. Chunk timing must respect this.
- Consider adding a `/queue` command on the sister server to view pending messages.
- Consider a `/clear` command to flush the queue.

**Two-way communication:**
- Player messages in `#communications` are relayed to the sister server's dedicated channel so the operator can read them.
- The operator responds via `/talk`. From the players' perspective, Proxy is a live entity that reads and responds.
- Bot should relay player messages with attribution (username + content), possibly with a distinct embed style to separate from bot chatter.

**`#discoveries` channel:**
- When a player finds a new endpoint on the here-be site, the bot announces it in `#discoveries`.
- The `Directory` config value maintains the running list of discovered links.
- Discovery mechanism TBD — could be players submitting URLs via a `/discover` command, or automated detection from the site's access logs.

**Method is player-configurable:**
- `Method` is a valid `/configure` parameter — players can change the active cipher.
- However, only methods the players have *discovered* are accepted. Unknown methods get `ERROR — method not recognized`.
- How and where players discover new methods is TBD — could be hidden in the world simulation, on website pages, or in encoded messages themselves.

---

## Cipher System: Method & Shift

The `/configure` output exposes cipher parameters as an in-world hint. Players are meant to realize that some messages (or parts of the world) are encoded, and the config tells them how to decode.

### Caesar (Phase 2 default)

Standard alphabetic shift cipher. The twist: the emoji 🐉 replaces the letter `I` in ciphertext. The shift value N is chosen such that this substitution is internally consistent — specifically, the ciphertext letter that `I` would normally map to is instead represented by 🐉.

Example with shift 7: `I` → `P`, but instead of `P`, the ciphertext uses 🐉. So when players see 🐉 in a message, they know it decodes to `I`. This gives them a known plaintext anchor for cracking the cipher, and ties the dragon theme into the mechanics.

**Open question:** Do ALL messages use the cipher, or only specific "encoded" ones? Suggestion: Proxy speaks plainly most of the time, but certain critical messages (coordinates, names, hints for other puzzles) appear encoded. The config is the players' Rosetta Stone.

### Suggested Additional Methods

These can be introduced as the narrative progresses — the config's `Method` and parameters update to reflect the current cipher in use. Each escalation can be a narrative beat (Proxy "upgrading" its encryption, or the connection degrading and requiring new decoding).

#### 1. Substitution (`Method — Substitution`)

Arbitrary monoalphabetic substitution. Config could expose a partial mapping table:
```
Method — Substitution
Table — A:🐉 E:⚔ I:🏰 O:🔥 U:💀 ...
```
Only vowels are shown — players must frequency-analyze to crack the consonants. Good mid-difficulty step up from Caesar.

#### 2. Vigenère (`Method — Vigenère`)

Polyalphabetic cipher with a keyword. The keyword is something discoverable in the world simulation — a dragon's name, a settlement, a spirit's location.
```
Method — Vigenère
Key — ????????
```
The key is hidden. Players must figure out what it is from cross-referencing the world. This directly ties the simulation puzzle to the bot puzzle.

#### 3. Null Cipher (`Method — Null`)

Messages look like normal English text, but a hidden message is embedded. Config hints at the extraction rule:
```
Method — Null
Extract — first
Delimiter — sentence
```
Meaning: take the first letter of each sentence. Or `first` + `word` = first letter of each word. This is great because players might not even realize the message is encoded at first.

#### 4. Book Cipher (`Method — Book`)

References to the here-be website pages. Messages contain coordinates like `thoughts:3:7` meaning "page `thoughts`, paragraph 3, word 7." This forces players to explore the website and ties all the puzzles together.
```
Method — Book
Source — /thoughts
Format — paragraph:word
```

#### 5. Coordinates (`Method — Cartography`)

Uses the world map grid as a lookup table. Messages contain coordinate pairs, and the letter/entity/terrain at that position on the map spells out the message. Players must have the world map open and cross-reference.
```
Method — Cartography
Grid — /world
Read — terrain
```
This one is powerful because the world is alive — if terrain changes, previously decoded messages might become ambiguous. Time-sensitive puzzles.

#### 6. Binary / Hex (`Method — Binary`)

Fits the "broken computer" aesthetic. Messages are raw hex or binary. Simple to decode but tedious without tooling, and it feels very in-character for a malfunctioning proxy.
```
Method — Binary
Encoding — hex
```

#### 7. Semaphore / Emoji Flag (`Method — Signal`)

Messages use sequences of flag emojis or directional arrows that correspond to semaphore positions → letters. Visually distinctive, not immediately obvious as a cipher.
```
Method — Signal
System — semaphore
```

#### 8. Runic (`Method — Runic`)

Messages use Unicode runic characters (ᚠᚢᚦᚨᚱᚲ etc.) as a 1:1 substitution for Latin letters. Fits the fantasy theme perfectly. Players need to look up the Elder Futhark or similar mapping.
```
Method — Runic
Alphabet — elder_futhark
```

### Recommended Progression

| Order | Method | Difficulty | Cross-reference needed? |
|-------|--------|-----------|------------------------|
| 1 | Caesar | Easy | No — config gives shift |
| 2 | Null | Easy-Medium | No — but easy to miss |
| 3 | Substitution | Medium | No — partial table given |
| 4 | Runic | Medium | External (alphabet lookup) |
| 5 | Vigenère | Hard | World simulation (key) |
| 6 | Book | Hard | Website pages |
| 7 | Cartography | Hard | Live world map |

Binary and Signal are good wildcards to drop in for one-off messages rather than sustained phases.

---

## Data Model

```
bot_state:
  phase: 0 | 1 | 2
  game_guild_id: snowflake
  sister_guild_id: snowflake (pre-configured)
  sister_channel_id: snowflake (pre-configured)
  communications_channel_id: snowflake
  discoveries_channel_id: snowflake
  host_string: random hex (generated once)
  config:
    server: string (starts random, target = game_guild_id)
    communications_channel: string (starts correct)
    discovery_channel: string (starts random, target = discoveries_channel_id)
    host: string (starts = host_string, becomes "here-be" in phase 2)
    identity: string (starts "prox", target = "Proxy")
    directory: list of strings (starts "ERROR", becomes [] in phase 2, accumulates discovered URLs)
    method: string (null until phase 2, then "Caesar"; player-changeable to discovered methods)
    shift: int (null until phase 2; setting to 0 triggers full reset to phase 0)
  message_queue: list of pending /talk messages
  discovered_methods: list of strings (starts ["Caesar"], grows as players find more)
  discovered_endpoints: list of URLs announced in #discoveries
```

---

## Technical Stack

- **discord.py** (Python, consistent with the Flask project)
- **Persistence:** Database (shared with the main app). Single server — guild ID and all state stored in DB so the bot can resume after restarts.
- **Hosting:** Separate from the Vercel Flask app. Needs a persistent process (not serverless). A small VPS, or Railway/Fly.io, or just a local machine.
- **Slash commands:** Use `discord.app_commands` for guild-specific slash commands
- **Guild-specific commands:** `/ping` and `/configure` registered only in the game server. `/talk` registered only in the sister server.

---

## File Structure (proposed)

```
bot/
  main.py          — bot startup, event handlers, phase orchestration
  config.py        — bot token, sister server/channel IDs, constants
  state.py         — persistence layer (load/save bot_state)
  phases/
    phase0.py      — guild creation, invite, /ping registration
    phase1.py      — garbage messages, /configure command logic
    phase2.py      — /talk relay, typing effect, message queue
  ciphers/
    __init__.py    — cipher registry, encode/decode dispatch
    caesar.py
    substitution.py
    vigenere.py
    null_cipher.py
    book.py
    cartography.py
    runic.py
    binary.py
    signal.py
  utils.py         — garbage text generators, typing effect helpers
```

---

## Resolved Questions

1. **Cipher application scope:** The Caesar shift goes all the way into emoji-land, making all shifted text emoji sequences. Players may learn to communicate in emoji-cipher. Scope of encoding (all messages vs. selective) still being considered.
2. **Discovery channel purpose:** `#discoveries` announces new endpoints players find on the here-be site. The `Directory` config maintains the running list of discovered links.
3. **Phase 2+ narrative transitions:** `Method` is a player-configurable parameter via `/configure`. Players can only set it to methods they've discovered. How/where methods are discovered — TBD.
4. **Server persistence:** Single server. Guild ID stored in database. Bot resumes state on restart.
5. **Player interaction model:** Two-way. Player messages in `#communications` are relayed to the sister server. Operator reads them and responds via `/talk`.
6. **Rate limiting:** None.
7. **Shift 0 = reset:** Setting Shift to 0 resets the bot to Phase 0. This is the self-destruct mechanism.

## Open Questions

1. **Cipher scope detail:** Do Proxy's conversational messages also get ciphered, or only specific encoded payloads (coordinates, hints, puzzle answers)?
2. **Discovery submission:** How do players report found endpoints? `/discover` command? Automated via access logs? Manual operator trigger?
3. **Method discovery:** Where and how do players find new cipher methods? Hidden in the world sim? On website pages? In encoded messages?
4. **Reset consequences:** When Shift 0 triggers a reset, is it a complete wipe (new guild) or a soft reset (same guild, state cleared)? What happens to `#discoveries` history?
