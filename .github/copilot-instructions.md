# Here Be Dragons - Copilot Instructions

## Project Overview

A **fantasy world simulation** where dragons, heroes, settlements, and spirits interact in a procedurally-generated world. Flask web app deployable to Vercel with API endpoints and visual world map.

For detailed entity behaviors and planned features, see [todo.txt](../todo.txt).

## Architecture

### Backend (`game/`)
- **`main.py`** - Flask entry point; creates `World`, initializes entities, registers blueprints
- **`game/world/`** - Simulation engine (time, terrain, spawning, combat)
- **`game/entities/`** - All entities with mixin-based composition
- **`web/endpoints/`** - Flask blueprints (`api.py` for JSON, `endpoints.py` for pages)

### Frontend (`web/static/world/`)
Modular ES6 architecture with dual-canvas rendering:
- **`world.js`** - Main loop, orchestrates terrain/entity rendering at 60fps
- **`terrain.js`** - Background canvas (biome colors) + character canvas (animated tiles)
- **`entities.js`** - Entity canvas with rotation, pulse animation, glow effects
- **`config.js`** - Dimensions (200×200 grid, 12px cells), biome colors, display toggles
- **`ui.js`** - Pan/zoom controls, display option toggles

**Render pipeline:** `requestAnimationFrame` for characters/entities, 1-second interval for entity data fetch via `/api/world`.

### Entity System (Mixin Composition)
Entities use **multiple inheritance** from mixins in `game/entities/base/`:

```python
# Example: Dragon inherits from 6 mixins
class Dragon(Mortal, Mobile, Named, Thinking, Scheduled, Aging):
```

**Key mixins:**
- `Entity` - Base class (coordinates, color, character, `serialize()`, `die()`)
- `Mobile` - Movement, A* pathfinding, state machine (`created→moving→arrived`), movement debt
- `Thinking` - Thoughts list, intent, `think()` method for logging entity thoughts
- `Scheduled` - Day planning with `DayScheduler`, hour-based actions via `on_hour()`
- `Mortal` - Auto-cleanup from world when `is_dead=True` (checked in `update()`)
- `Settlement` - Multi-tile structures via `occupies()`, `hurt()`/`heal()`, blessings
- `Aging` - Lifespan tracking via `process_aging()`, `init_aging()`, `get_lifespan()`
- `Named` - Simple name attribute

### Time System
The world uses a **day/night cycle** with event hooks:
- `on_dawn()` - Build schedules, spawn entities, daily events
- `on_hour(hour)` - Execute scheduled actions
- `on_dusk()` - Return to home, end day
- `on_night()` - Sleep, special behaviors

Schedule hours: 7-19 (active), 6 (dawn), 20 (dusk), 21-5 (night)

### World Update Flow
1. `DayNightCycle` advances time based on real seconds
2. Period transitions trigger `_trigger_dawn()`, `_trigger_dusk()`, `_trigger_night()`
3. Hourly updates call entity `on_hour(hour)` for scheduled action execution
4. 10-second movement updates handle entity motion and encounters

## Conventions

### Entity Creation Pattern
```python
class NewEntity(Mobile, Thinking, Scheduled):  # Choose mixins needed
    def __init__(self, world: 'World', coordinates: Coordinates, ...):
        Mobile.__init__(self, world, color, char, coordinates)
        Thinking.__init__(self, intent="...")
        Scheduled.__init__(self)
        # Entity-specific state
```

### Scheduling Actions
Use `DayScheduler` to spread actions across active hours:
```python
def build_schedule(self):
    scheduler = DayScheduler()
    scheduler.add(ActionType.PATROL, target=location)
    scheduler.add(ActionType.REST)
    self.schedule = scheduler.build()  # Returns [(hour, PlannedAction), ...]
```

### Serialization
Entities override `serialize()` returning dicts for the `/api/world` JSON endpoint. Base `Entity.serialize()` returns `color`, `character`, `coordinates`. Subclasses add entity-specific fields (e.g., `mood`, `age_days`, `blessings`). Entity type is inferred by the frontend from the presence of type-specific fields.

### Combat
Combat functions in `game/world/combat.py` follow pattern: `attacker_attacks_defender(attacker, defender, world)`. They check for protections (heroes defending settlements) before applying damage.

## Commands

```bash
uv sync           # Install dependencies
gunicorn main:app # Run locally (auto-deploys on git push)
```

Debug mode (2-minute days): set `debug_speed=True` in `World()` constructor.

## Code Exploration

When discovering signatures or class structures:
1. Check `game/entities/__init__.py` and `game/entities/base/__init__.py` for exported names
2. Use `grep_search` with `includePattern` to find definitions, then `read_file` for 15-20 lines around it
3. Use `list_code_usages` to see how mixins/methods are actually called in practice
4. Avoid reading 100+ line chunks speculatively - be surgical with line ranges

## Key Files for Common Tasks

| Task | Files |
|------|-------|
| Add new entity type | `game/entities/new_entity.py`, update `game/entities/__init__.py` |
| Modify spawning | `game/world/entity_gen.py` |
| Add combat behavior | `game/world/combat.py` |
| Change time/scheduling | `game/world/time_system.py`, `game/entities/base/scheduled.py` |
| Add API endpoint | `web/endpoints/api.py` |
| Add page route | `web/endpoints/endpoints.py`, `web/templates/` |
| Modify frontend rendering | `web/static/world/` (terrain.js, entities.js) |

## Current Development Focus
See [todo.txt](../todo.txt) for active tasks. Priority areas:
- User dragon submission form with spire-gated spawning
- Gossip/news system between entities
- Settlement hit point balancing
