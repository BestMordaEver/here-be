# Here Be Dragons - Copilot Instructions

## Project Overview

This project is a multipart puzzle challenge site where users discover pages by name and reveal hidden elements using various tools. We're tracking endpoint access to see which pages users find. The primary part is a **fantasy world simulation** where dragons, heroes, settlements, and spirits interact in a procedurally-generated world. Flask web app deployable to Vercel with API endpoints and visual world map.

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
class Dragon(Mobile, Visible, Named, Thinking, Scheduled, Aging):
```

**Key mixins:**
- `Entity` - Base class (coordinates, engagement system, `serialize()`, `die()`)
- `Mobile` - Movement, A* pathfinding, movement debt, `set_target()`, `on_arrival()`
- `Visible` - Visual states via `create_small()`/`create_large()`, multi-state rendering
- `Thinking` - Thoughts list, `think()` method for logging entity thoughts, placeholder system
- `Scheduled` - Rolling schedule with `DayPlanner`, `on_hour()`/`on_hour_end()`, sleep/wake cycle
- `Settlement` - Multi-tile structures via `occupies()`, `hurt()`/`heal()`, blessings
- `Aging` - Lifespan tracking via `process_aging()`, `get_lifespan()`, `on_old_age_death()`
- `Named` - Simple name attribute

**Deprecated:** `Mortal` mixin has been removed; entity cleanup is handled by `Entity.die()`.

### Time System
The world uses a **day/night cycle** managed by `DayNightCycle` in `time_system.py`:
- `on_dawn()` - Age entities, build schedules, spawn entities, daily events
- `on_hour(hour)` - Dispatch scheduled actions, passive behavior
- `on_hour_end(hour)` - Resolve engagements (combat damage, blessing theft, etc.)
- Sleep/wake cycle is entity-controlled via `Scheduled` mixin (not world-triggered)

Schedule hours: 7-19 (active), 6 (dawn), 20 (dusk), 21-5 (night)

### World Update Flow
1. `DayNightCycle` advances time based on real seconds
2. `_process_hour()` calls `_trigger_hour_end()` for the previous hour, then `_trigger_hour()` for current
3. Hourly updates call entity `on_hour(hour)` for scheduled action execution
4. 10-second movement updates handle entity motion and encounter checks

## Conventions

### Entity Creation Pattern
```python
class NewEntity(Mobile, Visible, Thinking, Scheduled, Aging):  # Choose mixins needed
    def __init__(self, world: 'World', coordinates: Coordinates, ...):
        Mobile.__init__(self, world, coordinates, loiter=1)
        Visible.__init__(self)
        Thinking.__init__(self)
        Scheduled.__init__(self)
        Aging.__init__(self)
        self.create_small("default", color, char)
        self.visual_state = "default"
```

### Scheduling Actions
Use `DayPlanner` to spread actions across active hours (anchored at dusk):
```python
def build_schedule(self):
    planner = self.plan_day()
    planner.add(ActionType.PATROL, target=location)
    planner.add(ActionType.REST)
    planner.commit()  # Writes to schedule + auto-schedules sleep/wake
```

### Serialization
Entities override `serialize()` returning dicts for the `/api/world` JSON endpoint. Subclasses build their own dict (e.g., `mood`, `age_days`, `blessings`, `coordinates`). Entity type is inferred by the frontend from the presence of type-specific fields.

### Entity Module Pattern
Complex entities (Dragon, Hero) are split into submodules and monkey-patched onto the class:
```python
# In entity/__init__.py:
from .schedule import build_schedule
Entity.build_schedule = build_schedule

from .actions import start_action, check_for_encounters, resolve_engagement
Entity.start_action = start_action
# etc.
```
Submodule files: `types.py` (enums/constants), `finders.py` (target search), `schedule.py` (mood + day planning), `actions.py` (action dispatch + engagement resolution), `movement.py` (movement overrides).

## Key Files for Common Tasks

| Task | Files |
|------|-------|
| Add new entity type | `game/entities/new_entity.py`, update `game/entities/__init__.py` |
| Modify spawning | `game/world/entity_gen.py` |
| Change time/scheduling | `game/world/time_system.py`, `game/entities/base/scheduled.py` |
| Add API endpoint | `web/endpoints/api.py` |
| Add page route | `web/endpoints/endpoints.py`, `web/templates/` |
| Modify frontend rendering | `web/static/world/` (terrain.js, entities.js) |

## Current Development Focus
See [todo.txt](../todo.txt) for active tasks. Priority areas:
- User dragon submission form with spire-gated spawning
- Gossip/news system between entities
- Wiring up the world update loop to call `on_dawn()` / engagement resolution
