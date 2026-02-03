"""Settlement daily events mixin."""
from enum import Enum
from random import random, choice
from typing import TYPE_CHECKING, List, Optional, Any

if TYPE_CHECKING:
    from game.world import World
    from game.entities import Caravan, Hero


class SettlementEvent(Enum):
    """Daily settlement events."""
    NONE = "none"           # Normal day - may send caravans, spawn heroes
    MOURNING = "mourning"   # After dragon attack - no caravans
    MARKET_DAY = "market_day"  # Every 5 days - attracts heroes, trading
    REPAIRS = "repairs"     # After market day if damaged - restore HP


# Event timing
MARKET_DAY_INTERVAL = 5  # Market day every 5 days


class SettlementEventsMixin:
    """Mixin providing daily event scheduling for settlements."""
    
    def __init__(self):
        self.current_event = SettlementEvent.NONE
        self.days_since_attack = 999  # Days since last dragon attack
        self.days_since_market = 0    # Days since last market day
        self.blessings = 0            # Accumulated blessings
        self.is_protected = False     # Whether currently protected by hero
    
    def determine_daily_event(self) -> SettlementEvent:
        """Determine today's event based on conditions."""
        self.days_since_market += 1
        
        # Mourning takes priority (if attacked recently and not protected)
        if self.days_since_attack <= 1 and not self.is_protected:
            return SettlementEvent.MOURNING
        
        # Repairs after market day if damaged
        if self.current_event == SettlementEvent.MARKET_DAY:
            if self.life < self.max_life:
                return SettlementEvent.REPAIRS
        
        # Market day every 5 days (unless mourning forced)
        if self.days_since_market >= MARKET_DAY_INTERVAL:
            self.days_since_market = 0
            return SettlementEvent.MARKET_DAY
        
        # Natural mourning (rare)
        if random() < 0.02:  # 2% chance
            return SettlementEvent.MOURNING
        
        return SettlementEvent.NONE
    
    def process_daily_event(self) -> None:
        """Process the day's event. Called at dawn."""
        self.current_event = self.determine_daily_event()
        self.is_protected = False  # Reset protection status
        self.days_since_attack += 1
        
        if self.current_event == SettlementEvent.NONE:
            self._process_none_day()
        elif self.current_event == SettlementEvent.MOURNING:
            self._process_mourning_day()
        elif self.current_event == SettlementEvent.MARKET_DAY:
            self._process_market_day()
        elif self.current_event == SettlementEvent.REPAIRS:
            self._process_repairs_day()
    
    def _process_none_day(self) -> None:
        """Normal day - may send caravans, occasionally spawn heroes/heal."""
        # Try to expand (settler caravans every 2 days)
        # Uses ExpansionMixin.try_expand() if available
        if hasattr(self, 'try_expand'):
            self.try_expand()
        
        # Find nearby settlements to trade with
        if random() < 0.4:  # 40% chance to send trade caravan
            target = self._find_trade_target()
            if target:
                self._send_trade_caravan(target)
        
        # Villages may spawn hero (rare)
        if self.__class__.__name__ == 'Village' and random() < 0.05:
            self._spawn_hero(city_born=False)
        
        # Cities may heal
        if self.__class__.__name__ == 'City' and random() < 0.1:
            self.heal(1)
    
    def _process_mourning_day(self) -> None:
        """Mourning - no outbound activity."""
        # Just mourn, no caravans
        if hasattr(self, 'think'):
            self.think("The settlement mourns its losses...")
    
    def _process_market_day(self) -> None:
        """Market day - busy trading, may spawn heroes."""
        # Neighbors may send caravans to us
        # (They check our event status and send caravans to market days)
        
        # Cities may spawn hero
        if self.__class__.__name__ == 'City' and random() < 0.2:
            self._spawn_hero(city_born=True)
        
        # Villages may spawn hero
        if self.__class__.__name__ == 'Village' and random() < 0.1:
            self._spawn_hero(city_born=False)
        
        if hasattr(self, 'think'):
            self.think("Market day! The square bustles with activity.")
    
    def _process_repairs_day(self) -> None:
        """Repairs - restore health."""
        heal_amount = 1
        
        # Double healing if hero is present
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Hero' and entity.is_alive:
                if self.occupies(entity.coordinates):
                    heal_amount = 2
                    break
        
        self.heal(heal_amount)
        
        if hasattr(self, 'think'):
            self.think("Repairs underway...")
    
    def _find_trade_target(self) -> Optional[Any]:
        """Find a nearby settlement to trade with. Closer = higher probability."""
        from .settlement import Settlement
        
        candidates = []
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.is_alive and entity != self:
                distance = self.get_distance(entity.coordinates)
                if distance <= 50:  # Max trade range
                    # Weight by inverse distance (closer = more likely)
                    weight = 50 - distance
                    candidates.append((weight, entity))
        
        if not candidates:
            return None
        
        # Prioritize market days
        market_targets = [
            (w * 2, e) for w, e in candidates 
            if hasattr(e, 'current_event') and e.current_event == SettlementEvent.MARKET_DAY
        ]
        
        if market_targets:
            candidates = market_targets
        
        # Weighted random selection
        total_weight = sum(w for w, _ in candidates)
        if total_weight <= 0:
            return None
        
        r = random() * total_weight
        cumulative = 0
        for weight, entity in candidates:
            cumulative += weight
            if r <= cumulative:
                return entity
        
        return candidates[-1][1] if candidates else None
    
    def _send_trade_caravan(self, destination) -> None:
        """Send a trade caravan to destination."""
        from game.entities.caravan import Caravan, CaravanMission
        
        caravan = Caravan(
            self.world,
            coordinates=(self.coordinates[0], self.coordinates[1] + 2),
            home=self,
            destination=destination,
            mission=CaravanMission.TRADE
        )
        self.world.add_entity(caravan)
    
    def _send_blessing_caravan(self, destination, retrieving: bool = True) -> None:
        """Send caravan to retrieve or deliver blessing."""
        from game.entities.caravan import Caravan, CaravanMission
        
        mission = CaravanMission.RETRIEVE_BLESSING if retrieving else CaravanMission.DELIVER_BLESSING
        
        caravan = Caravan(
            self.world,
            coordinates=(self.coordinates[0], self.coordinates[1] + 2),
            home=self,
            destination=destination,
            mission=mission
        )
        
        if not retrieving:
            caravan.blessing = True
            self.blessings -= 1
        
        self.world.add_entity(caravan)
    
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
        from game.entities.spire import Spire
        
        # Find location near city
        spire_x = self.coordinates[0] + 3
        spire_y = self.coordinates[1]
        
        spire = Spire(self.world, (spire_x, spire_y), self)
        self.spire = spire
        self.blessings -= 10
        
        self.world.add_entity(spire)
        
        if hasattr(self, 'think'):
            self.think("A golden spire rises to the heavens!")
