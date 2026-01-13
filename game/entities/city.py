"""City settlement."""
from .base import Coordinates, ExpansionMixin, Settlement, Named
from typing import List, Tuple, TYPE_CHECKING


if TYPE_CHECKING:
    from game.world import World
    from . import Camp, Village, Caravan, Spire


# City constants
STARTING_LIFE = 1000  # City starting HP
STORAGE_CAPACITY = 200  # City storage capacity
SPIRE_TREASURE_THRESHOLD = 200  # Treasure needed to spawn spire
HERO_SPAWN_INTERVAL = 50  # Cycles between hero spawns
HERO_ORE_REQUIREMENT = 40  # Ores needed to spawn hero


class City(Settlement, ExpansionMixin, Named):
    """5x5 city with walls, gates, buildings, and roads."""
    
    def __init__(self, name: str, coordinates: Coordinates):
        super().__init__(coordinates, life=STARTING_LIFE)
        Named.__init__(self, name)
        self.storage_capacity = STORAGE_CAPACITY
        self.village_created_on_promotion = False  # Track if village was created on promotion
        self.village_created_on_excess_wood = False  # Track if village was created with excess wood
        
        # Expansion tracking
        self.last_caravan_cycle = -999  # Last cycle a caravan was sent
        self.subsidiary_camps: List['Camp | Caravan'] = []
        self.subsidiary_villages: List['Village | Caravan'] = []
        
        # Spire and hero tracking
        self.spire: 'Spire' = None
        self.last_hero_spawn_cycle = -999
        
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return all 5x5 tiles for the city.
        Layout (coordinates at city square Ѻ):
        #═══#
        ║ѦЋЋ║
        ║֏ѺЋ║
        ║Ҵ║Ҵ║
        #₸₳₸#
        """
        x, y = self.coordinates  # City square position
        
        if self.is_dead:
            # Depleted city: buildings grey, city square green, walls slightly green
            return [
                # Row 0
                ((x - 2, y - 2), "#", "#90A090"),          # Wall (slightly green)
                ((x - 1, y - 2), "═", "#90A090"),      # Wall
                ((x, y - 2), "═", "#90A090"),      # Wall
                ((x + 1, y - 2), "═", "#90A090"),      # Wall
                ((x + 2, y - 2), "#", "#90A090"),      # Wall
                
                # Row 1
                ((x - 2, y - 1), "║", "#90A090"),      # Wall
                ((x - 1, y - 1), "Ѧ", "#808080"),  # Building (grey)
                ((x, y - 1), "Ћ", "#808080"),  # Building
                ((x + 1, y - 1), "Ћ", "#808080"),  # Building
                ((x + 2, y - 1), "║", "#90A090"),  # Wall
                
                # Row 2
                ((x - 2, y), "║", "#90A090"),      # Wall
                ((x - 1, y), "֏", "#808080"),  # Building
                ((x, y), "Ѻ", "#228B22"),  # City square (green)
                ((x + 1, y), "Ћ", "#808080"),  # Building
                ((x + 2, y), "║", "#90A090"),  # Wall
                
                # Row 3
                ((x - 2, y + 1), "║", "#90A090"),      # Wall
                ((x - 1, y + 1), "Ҵ", "#808080"),  # Building
                ((x, y + 1), "║", "#345F12"),  # Main road (overgrown green)
                ((x + 1, y + 1), "Ҵ", "#808080"),  # Building
                ((x + 2, y + 1), "║", "#90A090"),  # Wall
                
                # Row 4
                ((x - 2, y + 2), "#", "#90A090"),      # Wall
                ((x - 1, y + 2), "₸", "#808080"),  # Gate (grey)
                ((x, y + 2), "₳", "#808080"),  # Gate
                ((x + 1, y + 2), "₸", "#808080"),  # Gate
                ((x + 2, y + 2), "#", "#90A090"),  # Wall
            ]
        else:
            # Normal city
            return [
                # Row 0
                ((x - 2, y - 2), "#", "#808080"),          # Wall (grey)
                ((x - 1, y - 2), "═", "#808080"),      # Wall
                ((x, y - 2), "═", "#808080"),      # Wall
                ((x + 1, y - 2), "═", "#808080"),      # Wall
                ((x + 2, y - 2), "#", "#808080"),      # Wall
                
                # Row 1
                ((x - 2, y - 1), "║", "#808080"),      # Wall
                ((x - 1, y - 1), "Ѧ", "#B22222"),  # Building (brick)
                ((x, y - 1), "Ћ", "#B22222"),  # Building
                ((x + 1, y - 1), "Ћ", "#B22222"),  # Building
                ((x + 2, y - 1), "║", "#808080"),  # Wall
                
                # Row 2
                ((x - 2, y), "║", "#808080"),      # Wall
                ((x - 1, y), "֏", "#B22222"),  # Building
                ((x, y), "Ѻ", "#808080"),  # City square (grey)
                ((x + 1, y), "Ћ", "#B22222"),  # Building
                ((x + 2, y), "║", "#808080"),  # Wall
                
                # Row 3
                ((x - 2, y + 1), "║", "#808080"),      # Wall
                ((x - 1, y + 1), "Ҵ", "#B22222"),  # Building
                ((x, y + 1), "║", "#8B4513"),  # Main road (grey)
                ((x + 1, y + 1), "Ҵ", "#B22222"),  # Building
                ((x + 2, y + 1), "║", "#808080"),  # Wall
                
                # Row 4
                ((x - 2, y + 2), "#", "#808080"),      # Wall
                ((x - 1, y + 2), "₸", "#808080"),  # Gate (grey)
                ((x, y + 2), "₳", "#808080"),  # Gate
                ((x + 1, y + 2), "₸", "#808080"),  # Gate
                ((x + 2, y + 2), "#", "#808080"),  # Wall
            ]
    
    def get_max_camps(self) -> int:
        return 4

    def get_prioritized_resource(self) -> str:
        return 'ore'

    def get_prioritized_resource_count(self) -> int:
        return 2
    
    def generate_resources(self, world):
        if self.is_dead:
            return
        
        treasure_generated = 1  # Base treasure generation

        if self.has_excess('ores'):
            treasure_generated += 2

        self.add_resource('treasure', treasure_generated)

    def consume_resources(self, world: 'World') -> str:
        """Cities consume 3 food, 2 wood, and 1 ore per cycle."""
        if self.is_dead:
            return
        
        # Consume food
        food_needed = 3
        food_consumed = self.remove_resource('food', food_needed)
        
        # Consume wood
        wood_needed = 2
        wood_consumed = self.remove_resource('wood', wood_needed)
        
        # Consume ores
        ores_needed = 1
        ores_consumed = self.remove_resource('ores', ores_needed)
        
        # Track what's missing
        missing_food = food_needed - food_consumed
        missing_wood = wood_needed - wood_consumed
        missing_ores = ores_needed - ores_consumed
        
        if missing_food > 0:
            self.hurt(world, missing_food, 'starvation')
            if self.is_dead:
                return
        
        if missing_wood > 0 or missing_ores > 0:
            self.hurt(world, missing_wood + missing_ores, 'disrepair')
            if self.is_dead:
                return
        
        if missing_food == 0 and missing_wood == 0 and missing_ores == 0:
            self.heal(2)  # Heal 2 life if all needs met
    
    def expand_settlement(self, world: 'World') -> None:
        """Attempt to send caravans to create worker camps or villages."""
        # First priority: Create village on promotion (once, free, immediate)
        if len(self.subsidiary_villages) == 0 and self._attempt_create_village(world):
            return
        
        # Check caravan cooldown (8 cycles)
        if world.update_count - self.last_caravan_cycle < 8:
            return
        
        # Second priority: Create second village when we have excess wood
        if len(self.subsidiary_villages) == 1 and self.has_excess('wood') and self._attempt_create_village(world):
            return
        
        # Third priority: Create worker camps
        super().expand_settlement(world)
        
        # Fourth priority: Spawn heroes when excess ores
        if self.spire and self.has_excess('ores'):
            if world.update_count - self.last_hero_spawn_cycle >= HERO_SPAWN_INTERVAL:
                if self.resources['ores'] >= HERO_ORE_REQUIREMENT:
                    self._spawn_hero(world)
        
        # Fifth priority: Create spire when treasure threshold reached
        if self.spire is None and self.resources['treasure'] >= SPIRE_TREASURE_THRESHOLD:
            self._attempt_create_spire(world)
    
    def _attempt_create_spire(self, world: 'World') -> bool:
        """Attempt to create a spire near the city."""
        from . import Spire
        
        # Find adjacent tile for spire (prefer corners outside walls)
        x, y = self.coordinates
        spire_locations = [
            (x + 3, y - 3),  # Top right corner
            (x - 3, y - 3),  # Top left corner
            (x + 3, y + 3),  # Bottom right corner
            (x - 3, y + 3),  # Bottom left corner
        ]
        
        for loc in spire_locations:
            # Check if location is valid (plains, unoccupied)
            lx, ly = loc
            if lx < 0 or ly < 0 or lx >= world.WIDTH or ly >= world.HEIGHT:
                continue
            
            height = world.height_map[ly][lx]
            if world.get_biome_from_height(height) != 'field':
                continue
            
            if world.get_entities_at(loc):
                continue
            
            # Valid location found
            spire = Spire(loc, self)
            world.add_entity(spire)
            self.spire = spire
            return True
        
        return False
    
    def _spawn_hero(self, world: 'World') -> None:
        """Spawn a hero from the city."""
        from . import Hero
        
        # Spawn at city gate
        hero = Hero((self.coordinates[0], self.coordinates[1] + 3), self)
        world.add_entity(hero)
        
        # Consume ores for hero equipment
        self.remove_resource('ores', 20)
        self.last_hero_spawn_cycle = world.update_count

    
    def _attempt_create_village(self, world: 'World') -> bool:
        """Attempt to create a subsidiary village. Returns True if successful."""
        # Check village limit (2 max)
        if len(self.subsidiary_villages) >= 2:
            return False
        
        # Find a valid location for village (7x7 plains, no settlement distance limit for city villages)
        from game.world import check_village_spawn_area
        
        # Try locations in expanding rings from city
        x, y = self.coordinates
        for distance in range(10, 50):  # Start at 10, close to city
            for dx in range(-distance, distance + 1):
                dy_remaining = distance - abs(dx)
                for dy in [-dy_remaining, dy_remaining] if dy_remaining != 0 else [0]:
                    test_x, test_y = x + dx, y + dy
                    
                    # Check if valid for village (only check spawn area, ignore settlement distance)
                    if check_village_spawn_area(world, test_x, test_y):
                        # Valid location! Create caravan
                        from . import Caravan
                        
                        caravan = Caravan(
                            coordinates=(self.coordinates[0], self.coordinates[1] + 2),
                            home=self,
                            destination=(test_x, test_y),
                            intent=f"settle village"
                        )
                        
                        world.add_entity(caravan)
                        
                        # Track the subsidiary village
                        self.subsidiary_villages.append(caravan)
                        
                        # Update last caravan cycle
                        self.last_caravan_cycle = world.update_count
                        
                        return True
        
        return False
