"""Settlement daily events mixin."""
from enum import Enum
from random import random, choice
from typing import TYPE_CHECKING, List, Optional, Any
from .types import SettlementEvent

if TYPE_CHECKING:
    from game.world import World
    from game.entities import Caravan, Hero


class SettlementEventsMixin:
    """Mixin providing daily event scheduling for settlements."""
    
    def __init__(self):
        self.current_event = SettlementEvent.NONE
        self.days_since_attack = 999  # Days since last dragon attack
        self.days_since_market = 0    # Days since last market day
        self.days_since_celebration = CELEBRATION_COOLDOWN  # Days since last celebration
        self.got_blessing_yesterday = False  # Whether a blessing was received yesterday
        self.blessings = 0            # Accumulated blessings
        self.is_protected = False     # Whether currently protected by hero
    
    def _send_blessing_caravan(self, destination, retrieving: bool = True) -> None:
        """Send caravan to retrieve or deliver blessing."""
        from game.entities.caravan import CaravanMission
        
        mission = CaravanMission.RETRIEVE_BLESSING if retrieving else CaravanMission.DELIVER_BLESSING
        
        caravan = self.send_caravan(destination, mission)
        
        if not retrieving:
            caravan.blessing = True
            self.blessings -= 1
    
    def _spawn_hero(self, city_born: bool = True) -> None:
        """Spawn a hero at this settlement."""
        from game.entities.hero import Hero
        
        hero = Hero(
            self.world,
            coordinates=self.coordinates,
            home=self,
            city_born=city_born
        )
        self.world.add_entity(hero)
        
        if hasattr(self, 'think'):
            self.think("A hero emerges from our midst!")
    
    def on_attacked_by_dragon(self) -> None:
        """Called when attacked by a dragon."""
        self.days_since_attack = 0
    
    def receive_blessing(self, count: int = 1) -> None:
        """Receive blessings into the settlement. Sets celebration trigger."""
        self.blessings += count
        self.got_blessing_yesterday = True
    
    def check_spire_creation(self) -> bool:
        """Check if city should create a spire. Returns True if created."""
        if self.__class__.__name__ != 'City':
            return False
        
        # Need 10 blessings and previous day was market day
        if self.blessings >= 10 and self.current_event == SettlementEvent.MARKET_DAY:
            self._create_spire()
            return True
        
        return False
    
    def _create_spire(self) -> None:
        """Create a spire near this city."""
        from game.entities.settlement.spire import Spire
        
        # Find location near city
        spire_x = self.coordinates[0] + 3
        spire_y = self.coordinates[1]
        
        spire = Spire(self.world, (spire_x, spire_y), self)
        self.spire = spire
        self.blessings -= 10
        
        self.world.add_entity(spire)
        
        if hasattr(self, 'think'):
            self.think("A golden spire rises to the heavens!")
