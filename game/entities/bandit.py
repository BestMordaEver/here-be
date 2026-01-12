from .base import Coordinates, Mobile, Thinking, Mortal, Settlement
import random


# Bandit constants
FOOD_CONSUMPTION = 1
ATTACK_RANGE = 8
HUNGER_THRESHOLD = 10  # Below this food level, attack villages
ATTACK_COOLDOWN = 20
CARAVAN_DAMAGE = 10
VILLAGE_DAMAGE = 5
STARTING_FOOD = 20
STARTING_LIFE = 50
LOITER_TIME = 2
FOREST_SEARCH_RADIUS = 20
AMBUSH_CHANCE = 0.3  # 30% chance to attack caravan
STEAL_AMOUNT = 5  # Resources stolen per attack
RAID_FOOD_STEAL = 10  # Food stolen from villages
MELEE_RANGE = 2  # Range to trigger attack
VILLAGE_MELEE_RANGE = 3
STARVATION_DAMAGE = 1


class Bandit(Mortal, Mobile, Thinking):

    def __init__(
        self,
        coordinates: Coordinates,
    ):
        Mobile.__init__(self, "#960000", 'Ω', coordinates, STARTING_LIFE)
        Thinking.__init__(self, intent="lurking")
        self.loiter = LOITER_TIME
        self.food = STARTING_FOOD
        self.last_attack_cycle = -999
        self.path: list[Coordinates] = []
        self.hiding_spot: Coordinates = None  # Forest tile to return to
    
    def is_passable(self, coordinates: Coordinates, world) -> bool:
        """Bandits can move through fields and forests."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(world.height_map[0]) or y >= len(world.height_map):
            return False
        
        height = world.height_map[y][x]
        biome = world.get_biome_from_height(height)
        
        # Can move through fields and forests
        if biome not in ('field', 'forest'):
            return False
        
        # Can't move through settlements
        for entity in world.entities:
            if isinstance(entity, Settlement) and entity.occupies(coordinates):
                return False
        
        return True
    
    def is_in_forest(self, world) -> bool:
        """Check if bandit is currently in a forest tile."""
        x, y = self.coordinates
        height = world.height_map[y][x]
        return world.get_biome_from_height(height) == 'forest'
    
    def find_nearby_forest(self, world) -> Coordinates:
        """Find nearest forest tile to hide in."""
        best_distance = float('inf')
        best_coord = None
        
        # Search in expanding rings
        for radius in range(1, FOREST_SEARCH_RADIUS):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue  # Only check the ring edge
                    
                    x, y = self.coordinates[0] + dx, self.coordinates[1] + dy
                    if x < 0 or y < 0 or x >= world.WIDTH or y >= world.HEIGHT:
                        continue
                    
                    height = world.height_map[y][x]
                    if world.get_biome_from_height(height) == 'forest':
                        dist = (dx**2 + dy**2)**0.5
                        if dist < best_distance:
                            best_distance = dist
                            best_coord = (x, y)
            
            if best_coord:
                break
        
        return best_coord
    
    def find_nearby_target(self, world, target_type: str):
        """Find nearest entity of given type within attack range."""
        best_distance = float('inf')
        best_target = None
        
        for entity in world.entities:
            if entity.__class__.__name__ == target_type and entity.is_alive:
                dist = self.get_distance(entity.coordinates)
                if dist <= ATTACK_RANGE and dist < best_distance:
                    best_distance = dist
                    best_target = entity
        
        return best_target
    
    def choose_target(self, world) -> None:
        """Choose what to do based on current state."""
        # If hungry, look for villages to raid
        if self.food < HUNGER_THRESHOLD:
            village = self.find_nearby_target(world, 'Village')
            if village:
                self.destination = village.coordinates
                self.intent = "raiding"
                self.path = self.find_path(village.coordinates, world)
                self.state = "moving"
                return
        
        # Otherwise, look for caravans to ambush
        caravan = self.find_nearby_target(world, 'Caravan')
        if caravan and random.random() < AMBUSH_CHANCE:
            self.destination = caravan.coordinates
            self.intent = "ambushing"
            self.state = "moving"
            return
        
        # Default: hide in forest
        if not self.is_in_forest(world):
            forest = self.find_nearby_forest(world)
            if forest:
                self.destination = forest
                self.hiding_spot = forest
                self.intent = "hiding"
                self.path = self.find_path(forest, world)
                self.state = "moving"
                return
        
        # Already in forest, stay put
        self.intent = "lurking"
        self.state = "arrived"
    
    def approach_target(self, world) -> None:
        """Move towards current destination."""
        if not self.path and self.destination:
            self.path = self.find_path(self.destination, world)
        
        if self.path:
            next_step = self.path.pop(0)
            self.move_to(next_step)
    
    def attack_caravan(self, caravan, world) -> None:
        """Attack a caravan."""
        caravan.hurt(world, CARAVAN_DAMAGE, "bandit attack")
        self.think("A successful ambush!")
        # Steal some cargo
        for resource, amount in list(caravan.cargo.items()):
            if amount > 0:
                stolen = min(amount, STEAL_AMOUNT)
                caravan.cargo[resource] -= stolen
                if resource == 'food':
                    self.food += stolen
    
    def attack_village(self, village, world) -> None:
        """Attack a village for food."""
        village.hurt(world, VILLAGE_DAMAGE, "bandit raid")
        # Steal food
        stolen = village.remove_resource('food', RAID_FOOD_STEAL)
        self.food += stolen
        self.think(f"Raided the village for {stolen} food!")
    
    def update(self, world) -> None:
        # Consume food
        self.food -= FOOD_CONSUMPTION
        if self.food <= 0:
            self.hurt(world, STARVATION_DAMAGE, "starvation")
        
        # Generate thoughts
        self.generate_thought(world)
        
        super().update(world)
        
        # Check for attack opportunities
        if world.update_count - self.last_attack_cycle >= ATTACK_COOLDOWN:
            # Check for adjacent caravans
            for entity in world.entities:
                if entity.__class__.__name__ == 'Caravan' and entity.is_alive:
                    if self.get_distance(entity.coordinates) <= MELEE_RANGE:
                        self.attack_caravan(entity, world)
                        self.last_attack_cycle = world.update_count
                        break
            
            # If hungry, check for adjacent villages
            if self.food < HUNGER_THRESHOLD:
                for entity in world.entities:
                    if entity.__class__.__name__ == 'Village' and entity.is_alive:
                        if self.get_distance(entity.coordinates) <= VILLAGE_MELEE_RANGE:
                            self.attack_village(entity, world)
                            self.last_attack_cycle = world.update_count
                            break
        
        # Choose new target if needed
        if self.state in ("created", "arrived"):
            self.choose_target(world)
