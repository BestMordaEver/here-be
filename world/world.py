import random
import threading
import time
from typing import List
from world import HeightMapGenerator
from world.entity_gen import generate_spirits

class World:

    WIDTH = 200
    HEIGHT = 200
    
    THRESHOLDS = {
        'water': 0.23,
        'field': 0.68,
        'forest': 0.80,
    }

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randint(0, 1000000)
        self.seed = seed
        self.height_map = HeightMapGenerator(seed).generate_height_map(self.WIDTH, self.HEIGHT)
        
        # Entity management
        self.entities: List = []
        self.update_interval = 1  # seconds
        self.last_update_time = time.time()
        self.update_count = 0
        
        # Generate spirits after heightmap is ready
        generate_spirits(self)

    @staticmethod
    def get_biome_from_height(height):
        if height < World.THRESHOLDS['water']:
            return 'water'
        if height < World.THRESHOLDS['field']:
            return 'field'
        if height < World.THRESHOLDS['forest']:
            return 'forest'
        return 'mountain'

    

    def add_entity(self, entity) -> None:
        """Add an entity to the world."""
        self.entities.append(entity)
    
    def remove_entity(self, entity) -> None:
        """Remove an entity from the world."""
        if entity in self.entities:
            self.entities.remove(entity)
    
    def get_entities_at(self, coordinates):
        """Get all entities at a specific coordinate."""
        return [e for e in self.entities if e.coordinates == coordinates]
    
    def should_update(self) -> bool:
        """Check if enough time has passed for an update."""
        current_time = time.time()
        return current_time - self.last_update_time >= self.update_interval
    
    def update(self) -> None:
        """Update all entities and advance game state."""
        if not self.should_update():
            return
        
        self.last_update_time = time.time()
        self.update_count += 1
        
        for entity in self.entities:
            entity.update(self)
            # Check for dead camps
            if hasattr(entity, 'settlement_type') and entity.settlement_type == 'worker_camp':
                if entity.is_dead:
                    self.remove_entity(entity)
    
    def get_next_update_time(self) -> float:
        """Get seconds until next update."""
        current_time = time.time()
        time_since_last = current_time - self.last_update_time
        return max(0, self.update_interval - time_since_last)

    # Background world update thread
    def update_loop(self) -> None:
        """Continuously update the world in the background."""
        while True:
            try:
                self.update()
                # Sleep for a short time to avoid busy-waiting
                time.sleep(0.5)  # Check for updates twice per second
            except Exception as e:
                print(f"Error in world update loop: {e}")
                time.sleep(1)

    def start_update_thread(self) -> None:
        # Start background thread
        update_thread = threading.Thread(target=self.update_loop, daemon=True)
        update_thread.start()