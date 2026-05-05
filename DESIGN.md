# Here Be Dragons — Design Document

## Overview

*Here Be Dragons* is a top-down world simulator running on a 200×200 tile grid. Entities act autonomously on a day/night schedule, pursuing goals around a circular economy of **blessings** — a resource produced by nature spirits, hoarded by dragons, traded between settlements, and fought over by everyone.

---

## Table of Contents

1. [World Generation](#world-generation)
2. [Time System](#time-system)
3. [Entity Architecture](#entity-architecture)
4. [Base Mixins](#base-mixins)
5. [Entities](#entities)
   - [Spirits](#spirits)
   - [Blessings](#blessings)
   - [Cattle](#cattle)
   - [Bandits](#bandits)
   - [Caravans](#caravans)
   - [Heroes](#heroes)
   - [Dragons](#dragons)
   - [Settlements](#settlements)
6. [The Blessing Economy](#the-blessing-economy)
7. [Scheduling System](#scheduling-system)
8. [Engagement System](#engagement-system)
9. [Memory System](#memory-system)
10. [Territory & Domain](#territory--domain)

---

## World Generation

The world is a **200×200 tile grid** generated with Perlin noise.

### Heightmap

- 4 octaves of layered Perlin noise
- 5 smoothing iterations
- Normalized to `[0.0, 1.0]`

### Biomes

| Height Range | Biome |
|---|---|
| `< 0.23` | Water |
| `< 0.68` | Field |
| `< 0.80` | Forest |
| `≥ 0.80` | Mountain |

### Spirit Placement

A flood-fill pass identifies connected biome regions. Valid regions (≥ 5 tiles for water/mountain, ≥ 10 for forest) each receive a spirit at their most central tile (minimizing total Manhattan distance). Oversized forests are split into clusters using k-means (max 25-tile intra-cluster spread).

### Initial State

- 1 starting city
- 5 starting villages
- Spirits spawned on every qualifying biome region

### Ongoing Spawning

| Entity | Interval |
|---|---|
| City | Every 15 days |
| Villages (×2) | Every 10 days |
| Cattle | Once per day (cap: 20) |

---

## Time System

### Game Time

`GameTime` is an immutable `(day, hour)` pair with comparison operators.

### Day/Night Cycle

`DayNightCycle` maps real seconds to game time. Two presets:

| Mode | Real seconds per game day |
|---|---|
| Real-time | 86,400 s |
| Debug | 120 s |

### Time Periods

| Period | Hours |
|---|---|
| Dawn | 6:00 |
| Day | 7:00 – 19:00 |
| Dusk | 20:00 |
| Night | 21:00 – 5:00 |

Entity schedules are executed on every hour transition. Schedules are built at dawn each day.

---

## Entity Architecture

All entities are built from a **mixin-based composition** pattern. Every entity extends `Entity` and adds mixins for the capabilities it needs.

```
Entity (base)
  ├── Mobile          — grid movement and pathfinding
  ├── Named           — name and pronouns
  ├── Visible         — map representation
  ├── Aging           — lifespan and old-age death
  ├── Scheduled       — daily planning and hourly execution
  ├── Thinking        — memory and thought logging
  ├── Pockets         — blessing storage
  └── Engaging        — participation in engagements
```

---

## Base Mixins

### Entity

The root class. Provides:

- Grid position
- `get_distance(other)` — Chebyshev or Euclidean distance
- `get_adjacent_tiles()` — 8-directional neighbours
- `get_nearby_entities(radius)` — filtered entity lookup
- `die()` — removal from world

### Mobile

For entities that move on the grid.

- **A\* pathfinding** with terrain cost
- **Diagonal debt** — diagonal moves accumulate fractional cost; movement is skipped when debt ≥ 1.0 (BLADE dragons are exempt)
- **Loiter** — configurable tick delay between moves
- **Terrain restriction** — per-entity passable tile sets

### Named

Stores a name and gendered pronouns (he/she/they/it/ze/ae).

### Visible

Stores the visual representation used by the web renderer: a character + color per tile. Supports multi-tile entities.

### Aging

- Tracks `age_days`
- Calls `die()` when lifespan is reached (old-age deaths do not drop blessings)

### Scheduled

Schedule-based daily planning.

- Schedule stored as `(day, hour) → action` dictionary
- `push_action()` cascades conflicts forward if a slot is taken
- Free-slot search: backward from preferred hour to anchor (dusk), then forward

See [Scheduling System](#scheduling-system) for detail.

### Thinking

Priority-bounded memory and thought log.

- Thoughts are stored with a priority tier and a staleness timer
- Lowest-priority memory is evicted when capacity is full

See [Memory System](#memory-system) for detail.

### Pockets

Blessing storage.

| Capacity value | Meaning |
|---|---|
| `0` | Cannot carry blessings |
| `-1` | Unlimited |
| `N` | Fixed capacity |

`wasteful=True` — entity accepts blessings when full but immediately discards them (used by bandits to make robbery feel punishing).

### Engaging

Participation in structured interactions.

- An entity's `current_engagement` is resolved at the end of each hour
- Entities can `join_engagement()` to enter an existing engagement
- Supports solo (RESTING) and multi-participant (COMBAT) engagements

See [Engagement System](#engagement-system) for detail.

---

## Entities

### Spirits

Stationary anchors placed on biome clusters at world-gen.

| Type | Source biome |
|---|---|
| `FOREST` | Forest cluster |
| `LAKE` | Water region |
| `MOUNTAIN` | Mountain region |

- Capacity: 1 blessing
- Dragons **tend** spirits (create a blessing if none is present)
- Settlements **extract** from nearby spirits (lake spirits in particular)
- Building a camp on a spirit marks it **occupied**, blocking extraction conflicts

---

### Blessings

The world's currency. A pile entity with a numeric count.

- Dropped when a non-old-age death occurs
- Multiple piles at the same tile automatically merge
- Removed from the world when count reaches zero

**Who can pick them up:**

| Entity | Capacity |
|---|---|
| Hero | 3 |
| Bandit | 3 (wasteful) |
| Caravan | 1 |

---

### Cattle

Slow-moving grazers.

- **Loiter:** 10 (very slow)
- Wander fields near villages
- Flee from dragons within `FEAR_RADIUS = 12` tiles
- Capped at 20 simultaneously alive
- Rendered in 4 shades of brown

---

### Bandits

Short-lived opportunists.

- **Loiter:** 1 | **Lifespan:** 50 days
- Move through fields and forests
- Capacity: 3 blessings (`wasteful=True`)

**Behaviour alternates daily:**

| Mood | Behaviour |
|---|---|
| LURKING | Hide in forest, ambush caravans (ROBBERY). If 3+ days without a robbery, attack a nearby village |
| SEEKING | Travel to ruins or treasuries and pillage them (PILLAGING) |

**Engagement resolution:**

- *ROBBERY*: Steal caravan's blessing, reset `days_since_robbery`
- *COMBAT*: Win → steal from settlement; die if a VENGEFUL hero is in the engagement
- *PILLAGING*: Claim blessings from ruins/treasury

Bandits spawn in ruins 2 days after a settlement dies.

---

### Caravans

Mobile traders dispatched by settlements.

- **Loiter:** 4 | Field-only movement
- Capacity: 1 blessing, 1 memory slot

**Mission types:**

| Mission | Description |
|---|---|
| `TRADE` | Exchange memories at a settlement, return home |
| `SETTLE_CAMP` | Travel to a spirit and found a worker camp |
| `RETRIEVE_BLESSING` | Buy blessing from a village, return home |
| `DELIVER_BLESSING` | One-way delivery |

Caravans exchange memories with every talker they pass. If their destination dies, they flee to the nearest safe settlement. BLADE dragons destroy a caravan outright; an ANTHROPOPHAGE dragon destroys an unprotected caravan.

---

### Heroes

Wandering adventurers with a party system.

- **Loiter:** 1 | **Lifespan:** 50 days
- Capacity: 3 blessings, 5 memory slots

**Daily moods (with rough probability):**

| Mood | Condition / Weight | Behaviour |
|---|---|---|
| MERCENARY | 30% | Escort a caravan |
| ADVENTUROUS | 70% | Travel to a remote settlement |
| TIRED | After 3 active days, or age ≥ 48 | Rest in a settlement |
| OPPORTUNISTIC | Knows a domain for 10+ days | Pillage ruins or treasury |
| VENGEFUL | An acquaintance was killed | Hunt bandits |
| FOREBODING | Leading a full 4-hero party | March on a dragon lair |
| SUBSERVIENT | In a party, not the leader | Follow party leader |

**Party system:**

- Up to 4 heroes form a party when FOREBODING
- A full party can kill a dragon (BLADE types cause 1–2 hero casualties; casualties are determined by party position, not randomly)
- Solo hero vs. dragon: hero becomes TIRED unless VENGEFUL; a TIRED hero dies if not in a settlement, or immediately against a BLADE dragon

**Other mechanics:**

- Track known dragon domains
- Build acquaintances with heroes in the same settlement
- Sell blessings in cities
- On death: drop blessings, broadcast `SAW_HERO_DIE` to nearby talkers

---

### Dragons

The primary antagonists (or protectors, depending on alignment).

- **Loiter:** 0 (fastest) | No terrain restrictions
- **Lifespan:** 20 base days + 5 per active spire in the world

#### Types

| Type | Special trait |
|---|---|
| SERPENT | Figure-8 circling pattern; confuses nearby entities while travelling — they wander randomly until the next hour. Heroes on ESCORT/PROTECT/ATTACK missions are partially exempt and only become briefly erratic (4 erratic steps) instead of fully disoriented. Engaged entities are unaffected. |
| BLADE | Ignores diagonal debt (faster); defenders cannot prevent its attacks |
| DRUID | Tends all spirits within 8 tiles per TENDING session |
| MIDAS | Generates 2 blessings per HOARDING session; domain cap is 20 |
| FRAGILE | 30% chance to shed a blessing on the ground during combat |
| BRUTE | Extra damage in combat |

#### Alignments

| Alignment | Behaviour |
|---|---|
| GOOD | Actively protects humans |
| EVIL | Attacks humans on sight |
| TERRITORIAL | Wide protection radius (12 tiles) |
| NEUTRAL | Neither protects nor seeks out |

#### Diets

| Diet | Target |
|---|---|
| CARNIVORE | Hunt cattle and fish |
| HERBIVORE | Graze fields |
| GREED | Raid settlements for blessings |
| ANTHROPOPHAGE | Target humans via COMBAT (not FEEDING), so protectors can intervene |

#### Domain types

| Domain | Spawn biome | Special |
|---|---|---|
| AQUATIC | Water | — |
| MOUNTAIN | Mountain | — |
| VERDANT | Field / Forest | — |
| SCORCHED | Anywhere | Burns a 10-tile radius (cracked water, ash fields, charred forest) |

#### Daily moods

| Mood | Behaviour |
|---|---|
| DREARY | Tend hoard; attack if EVIL alignment |
| INSPIRED | Tend hoard; visit a distant spirit (20+ tiles away) |
| PENSIVE | Feed once; tend a nearby spirit |
| HUNGRY | Feed twice (every 3 days), rest between meals |
| COVETOUS | Attack a settlement, target blessings only |

#### Circling mechanic

During combat, dragons orbit their target:

- Standard: 8-step octagon at 6-tile radius
- SERPENT: Figure-8 pattern
- Rotation state is tracked for visual accuracy in the renderer

#### Domain entity

Each dragon has an associated `Domain` entity that stores its treasure hoard. The hoard has a cap: **10 blessings** for standard domains, **20** for MIDAS. If the dragon dies, the domain becomes an accessible **treasury** that heroes and bandits can pillage.

---

### Settlements

Settlements share a base class and add specialisation through mixins.

**Base features:**

- Health (`life` / `max_life`)
- Unlimited blessing storage
- Daily event roll
- Memory / thinking
- Caravan dispatch via `send_caravan()`

**Daily events:**

| Event | Trigger |
|---|---|
| NONE | 65% chance |
| MOURNING | After a dragon attack |
| MARKET_DAY | Every 5 days |
| REPAIRS | If damaged after market day |
| CELEBRATION | After receiving a blessing |

**Mixins used by settlements:**

- **Expansion** — sends settler caravans every 2 days to found camps; respects camp limits and distance rules
- **Extractor** — passively collects from nearby spirits; range depends on spirit type (forest: 6, mountain/lake: 10)
- **Ruins** — dead settlements persist as ruins for 50 days; bandits spawn in them; heroes/bandits can pillage stored blessings

---

#### Village

- **Size:** 3×3 | **Life:** 3 HP
- Requires a clear 7×7 plain to spawn
- Up to 4 camps (prioritises 1 forest spirit)
- Extracts from lake spirits
- Hero spawn: 50% on MOURNING, 5% otherwise

#### City

- **Size:** 5×5 | **Life:** 5 HP
- Requires a clear 11×11 plain to spawn
- Up to 6 camps (prioritises 2 mountain spirits)
- Can build **Spires** (cost: 10 blessings each); each active spire extends every dragon's lifespan by 5 days
- Cities with spires trade the surplus to cities without spires via caravan
- Hero spawn: 20% on MARKET_DAY, 0% otherwise

#### Camp

- **Size:** 2×2 | **Life:** 2 HP
- Spawned by a settler caravan on a spirit tile
- Marks its target spirit as occupied
- Extracts from the target spirit daily
- Dispatches a blessing-delivery caravan to its parent settlement daily
- Reassigns to the nearest settlement if the parent dies

#### Spire

- **Size:** 1×1 | **Lifespan:** 100 days
- Belongs to a city; dies with the city
- Becomes ruins (50-day duration) if damaged

---

## The Blessing Economy

```
Nature Spirits
    │  tended by Dragons (create blessing)
    ▼
Dragon Hoard (Domain)
    │  dragon death
    ▼
Treasury / Dropped Pile
    │  pillaged by Heroes, Bandits
    │  extracted by Settlements
    ▼
Settlement Treasury
    │  traded by Caravan     sold to Heroes (in cities)
    ▼                               ▼
  Camp  ──► delivers to parent   Hero Inventory
                                    │  blessing drop on death
                                    ▼
                              Dropped Pile  ──► picked up again
```

Key pressure points:

- Dragons *create* blessings by tending spirits — they are the primary source
- Cities *consume* blessings to build spires
- Bandits *destroy* blessings by accepting them wastefully
- Hero deaths *redistribute* blessings to whoever kills them

---

## Scheduling System

### DayPlanner

Each `Scheduled` entity builds a plan at dawn using `DayPlanner`:

1. Actions are added without explicit time slots
2. `SLEEP` is anchored at dusk (20:00)
3. `WAKE` is placed 8 hours after sleep
4. `commit()` assigns times working backwards from dusk

### Schedule Storage

`(day, hour) → action` dictionary for O(1) lookup.

`push_action()` cascades conflicts forward to the next free slot.

### Action Types

| Category | Actions |
|---|---|
| Lifecycle | `WAKE`, `SLEEP` |
| Movement | `MOVE_TO`, `RETURN_HOME`, `WANDER`, `FLEE` |
| Combat | `ATTACK`, `PROTECT`, `ESCORT` |
| Economy | `FEED`, `TEND`, `HOARD`, `TRADE`, `DELIVER` |
| Settlement | `REPAIR`, `SPAWN_HERO`, `EXPAND`, `SETTLE` |
| Misc | `PATROL`, `REST`, `PILLAGE`, `IDLE` |

---

## Engagement System

Engagements represent structured multi-entity interactions resolved at the end of each game hour.

### Types

| Type | Participants |
|---|---|
| COMBAT | Attacker + defenders |
| ROBBERY | Bandit + caravan |
| TENDING | Dragon + spirit |
| TRADING | Caravan + settlement |
| FEEDING | Dragon + cattle/fish (non-anthropophage diets only) |
| PILLAGING | Hero/Bandit + ruins/treasury |
| RESTING | Solo entity |
| HOARDING | Dragon solo — stores blessings in its domain |

### Lifecycle

1. Entity calls `engage(target, type)` — creates or joins an engagement
2. Others may `join_engagement()` during the same tick
3. At hour-end, `resolve_engagement()` is called on each participant
4. Results: blessing transfer, HP loss, death, memory creation, or no effect

### Resolution rules (selected)

**Resolution contract:** Each participant's `resolve_engagement()` only modifies its own state. The sole exceptions are ROBBERY and PILLAGING, which are explicit blessing-transfer mechanics.

**HOARDING:**
Dragon stores 1 blessing in its domain (2 for MIDAS). Domain silently caps at 10 (20 for MIDAS).

**TENDING:**
Spirit generates a blessing if it holds none. DRUID dragons tend every spirit within 8 tiles, not just the engaged target.

**ANTHROPOPHAGE feeding:**
Anthropophage dragons use COMBAT (not FEEDING), so protectors can intervene. Dragon is sated if it fights: a settlement; a bandit; an unprotected caravan; or a TIRED hero outside a settlement with no protectors. If none of these are present, the attack action is retried.

**BLADE dragon attacks:**
Defenders join the engagement as normal but the attack resolves as if they are absent: caravans are destroyed, settlements take damage, tired heroes die regardless of location.

**Dragon vs. party of 4+ heroes:**
Dragon dies. BLADE types cause 2 hero casualties; others cause 1. Casualties are the first N heroes by object id.

**Dragon vs. solo hero:**
Hero becomes TIRED (unless VENGEFUL). TIRED hero dies if not in a settlement, or always against a BLADE dragon.

**Cattle FEEDING:**
Cattle die when devoured by a dragon during a FEEDING engagement.

**Bandit robbery:**
Caravan loses its blessing. `days_since_robbery` resets.

**Bandit COMBAT:**
Bandit dies if a VENGEFUL hero is in the engagement. If bandits outnumber protectors, the bandit takes blessings from any settlement in the fight.

**Settlement under attack:**
Takes 1 HP damage. BRUTE deals extra (reduces to 1 HP or kills outright for camps). BRUTE one-shots a camp.
A GOOD dragon or hero PROTECTING the settlement blocks all damage — unless the attacker is a BLADE dragon.

---

## Memory System

### Memory Types & Priority

| Memory | Priority | Staleness |
|---|---|---|
| SAW_DRAGON | 1 (lowest) | 3 days |
| ATTACKED_BY_DRAGON | 6 | 5 days |
| SAW_HERO_DIE | 7 (highest) | Never |

### Capacity by Entity

| Entity | Slots |
|---|---|
| Hero | 3 |
| City | 5 |
| Village | 3 |
| Camp | 2 |
| Caravan | 1 |
| Non-talker | 0 |

### Rules

- When capacity is full, the **lowest-priority** memory is evicted
- Stale memories are automatically pruned each tick
- Talker entities **bidirectionally swap** memories when they meet
- Caravans propagate memories across the map, acting as a gossip network

---

## Territory & Domain

### Dragon Domain

- Each dragon owns a `Domain` entity centred on its lair
- **Protection radius:** 3 tiles standard, 12 tiles for TERRITORIAL alignment
- EVIL dragons attack anything within radius
- GOOD dragons defend humans within radius (interrupting their current action)
- On dragon death, the domain entity becomes an accessible treasury

### Scorched Earth

SCORCHED-domain dragons apply a permanent 10-tile radius overlay to terrain:

| Original | Scorched |
|---|---|
| Water | Cracked / ashen water |
| Field | Ash field |
| Forest | Charred forest |

### Settlement Expansion

- Settlements search for unoccupied spirits within 15 tiles
- Candidate sites must be on fields, ≥ 10 tiles from any existing settlement
- Sent via settler caravan (SETTLE_CAMP mission)
- Built camp marks spirit as occupied, preventing double-claiming
