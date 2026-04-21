from random import random
from typing import TYPE_CHECKING, Optional, Any
from .types import SettlementEvent

if TYPE_CHECKING:
    from .settlement import Settlement


def find_trade_target(settlement : 'Settlement') -> Optional[Any]:
    """Find a nearby settlement to trade with. Closer = higher probability."""
    from .settlement import Settlement
    
    candidates = []
    for entity in list(settlement.world.entities):
        if isinstance(entity, Settlement) and entity.is_alive and entity != settlement:
            distance = settlement.get_distance(entity.coordinates)
            if distance <= 50:  # Max trade range
                # Weight by inverse distance (closer = more likely)
                weight = 50 - distance
                candidates.append((weight, entity))
    
    if not candidates:
        return None
    
    # Prioritize market days
    market_targets = [
        (w * 2, e) for w, e in candidates 
        if e.current_event == SettlementEvent.MARKET_DAY
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