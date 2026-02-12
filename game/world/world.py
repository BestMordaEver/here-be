import random
import threading
import time
import traceback
from typing import List, TYPE_CHECKING

from . import HeightMapGenerator, attempt_spawn_settlement, attempt_spawn_cattle, generate_spirits
from .time_system import DayNightCycle, GameTime, TimeOfDay, DAWN_HOUR, DUSK_HOUR, NIGHT_HOUR

if TYPE_CHECKING:
    from game.entities.base import Scheduled
    from game.entities.base.entity import Entity


# World timing constants
DEFAULT_REAL_SECONDS_PER_DAY = 86400.0  # Real-time (1 day = 1 day)
DEBUG_REAL_SECONDS_PER_DAY = 120.0      # Debug mode (1 day = 2 minutes)
MOVEMENT_UPDATE_INTERVAL = 10.0          # Seconds between movement updates

# City starting blessings
CITY_STARTING_BLESSINGS = 10  # Enough to spawn spire immediately


class World:

    WIDTH = 200
    HEIGHT = 200
    
    THRESHOLDS = {
        'water': 0.23,
        'field': 0.68,
        'forest': 0.80,
    }

    def __init__(self, seed=None, debug_speed: bool = False):
        if seed is None:
            seed = random.randint(0, 1000000)
        self.seed = seed
        self.height_map = HeightMapGenerator(seed).generate_height_map(self.WIDTH, self.HEIGHT)
        
        # Entity management
        self.entities: List['Entity'] = []
        
        # Time system
        speed = DEBUG_REAL_SECONDS_PER_DAY if debug_speed else DEFAULT_REAL_SECONDS_PER_DAY
        self.time = DayNightCycle(real_seconds_per_game_day=speed)
        
        # Movement update tracking (for the 10-second entity movement updates)
        self.last_movement_update = time.time()
        
        # Generate spirits after heightmap is ready
        generate_spirits(self)
        
        # Spawn initial city (first settlement)
        city = attempt_spawn_settlement(self, 'city')
        city.blessings = CITY_STARTING_BLESSINGS
        if not city._attempt_create_spire():
            raise RuntimeError("Failed to create starting city spire.")
        
        # Generate initial villages
        for _ in range(5):
            attempt_spawn_settlement(self, 'village')
        
        # Trigger initial dawn to build schedules
        self._trigger_dawn()

    @staticmethod
    def get_biome_from_height(height):
        if height < World.THRESHOLDS['water']:
            return 'water'
        if height < World.THRESHOLDS['field']:
            return 'field'
        if height < World.THRESHOLDS['forest']:
            return 'forest'
        return 'mountain'
    
    def add_entity(self, entity: 'Entity') -> None:
        """Add an entity to the world."""
        self.entities.append(entity)
        
        # If it's daytime and entity is Scheduled, build its schedule
        if hasattr(entity, 'build_schedule') and self.time.is_active_hours():
            entity.build_schedule()
    
    def remove_entity(self, entity: 'Entity') -> None:
        """Remove an entity from the world."""
        if entity in self.entities:
            self.entities.remove(entity)
    
    def get_entities_at(self, coordinates):
        """Get all entities at a specific coordinate."""
        result = []
        for e in self.entities:
            if hasattr(e, 'occupies'):
                if e.occupies(coordinates):
                    result.append(e)
            elif e.coordinates == coordinates:
                result.append(e)
        return result
    
    def get_entities_in_radius(self, coordinates, radius: float) -> List:
        """Get all entities within a radius of coordinates."""
        result = []
        cx, cy = coordinates
        for e in self.entities:
            ex, ey = e.coordinates
            distance = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
            if distance <= radius:
                result.append(e)
        return result
    
    def _trigger_hour(self, hour: int) -> None:
        """Trigger hourly event for all scheduled entities."""
        for entity in list(self.entities):
            if hasattr(entity, 'on_hour'):
                entity.on_hour(hour)
    
    def _trigger_hour_end(self, hour: int) -> None:
        """Trigger hour-end event for all scheduled entities. Resolves engagements."""
        for entity in list(self.entities):
            if hasattr(entity, 'on_hour_end'):
                entity.on_hour_end(hour)
            entity.resolve_engagement()
    
    def _process_hour(self, game_time: GameTime) -> None:
        """Process a single hour of game time."""
        hour = game_time.hour
        period = game_time.get_period()
        
        # Resolve previous hour's engagements before starting new hour
        self._trigger_hour_end((hour - 1) % 24)
        
        if period == TimeOfDay.DAWN:
            self._daily_spawns(game_time.day)
        
        # Trigger hourly updates for active hours
        self._trigger_hour(hour)
    
    def _daily_spawns(self, day: int) -> None:
        """Handle spawning that occurs at dawn."""
        # Spawn cities every 15 days
        if day > 1 and day % 15 == 0:
            attempt_spawn_settlement(self, 'city')
        
        # Spawn villages every 10 days (2 villages)
        if day > 1 and day % 10 == 0:
            for _ in range(2):
                attempt_spawn_settlement(self, 'village')
        
        # Spawn cattle once per day, with world cap of 20
        cattle_count = sum(1 for e in self.entities if e.__class__.__name__ == 'Cattle' and e.is_alive)
        if cattle_count < 20:
            attempt_spawn_cattle(self)
    
    def update(self) -> None:
        """
        Main update loop. Processes:
        1. Time advancement and hourly events
        2. Entity movement (every 10 seconds)
        3. Encounter checks
        """
        # Update time and get any hours that passed
        hours_passed = self.time.update()
        
        # Process each hour that passed
        for game_time in hours_passed:
            self._process_hour(game_time)
        
        # Check if it's time for movement update (every 10 seconds)
        current_time = time.time()
        if current_time - self.last_movement_update >= MOVEMENT_UPDATE_INTERVAL:
            self.last_movement_update = current_time
            
            # Iterate over a copy since entities may be removed during update
            for entity in list(self.entities):
                if hasattr(entity, 'update_movement'):
                    entity.update_movement()

             # Get all scheduled entities that are currently moving
            moving_entities: List[Entity] = [
                e for e in self.entities 
                if hasattr(e, 'check_for_encounters') and hasattr(e, 'current_action')
                and e.current_action is not None
            ]
            
            for entity in moving_entities:
                entity.check_for_encounters()
    
    def update_loop(self) -> None:
        """Continuously update the world in the background."""
        while True:
            try:
                self.update()
                # Sleep briefly to avoid busy-waiting
                time.sleep(1.0)
            except Exception as e:
                print(f"Error in world update loop: {e}")
                traceback.print_exc()
                time.sleep(1)

    def start_update_thread(self) -> None:
        """Start background update thread."""
        update_thread = threading.Thread(target=self.update_loop, daemon=True)
        update_thread.start()
    
    def set_time_speed(self, real_seconds_per_day: float) -> None:
        """Change the game speed."""
        self.time.set_speed(real_seconds_per_day)
    
    def skip_hours(self, count: int) -> None:
        """Debug: Skip a number of hours."""
        for _ in range(count):
            hours = self.time.skip_to_hour((self.time.current_hour + 1) % 24)
            for gt in hours:
                self._process_hour(gt)