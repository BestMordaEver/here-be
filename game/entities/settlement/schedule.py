from typing import TYPE_CHECKING
from random import random
from enum import Enum
from game.entities.base.scheduled import ActionType
from .types import SettlementEvent
from . import finders

if TYPE_CHECKING:
    from game.entities.base import Settlement



# Event timing
MARKET_DAY_INTERVAL = 5  # Market day every 5 days
CELEBRATION_COOLDOWN = 5  # Days before celebration can happen again

# Hero spawn probabilities
VILLAGE_HERO_CHANCE_NONE = 0.05      # Village hero spawn on normal day
VILLAGE_HERO_CHANCE_MOURNING = 0.5   # Village hero spawn on mourning day
CITY_HERO_CHANCE_MARKET = 0.2        # City hero spawn on market day

CITY_HEAL_CHANCE = 0.1               # City chance to heal on normal day
TRADE_CHANCE = 0.4                   # Chance to send a trade caravan


def build_schedule(settlement: "Settlement") -> None:
    """Build the day's schedule based on the settlement event."""

    is_village = getattr(settlement, 'is_village', False)
    is_city = getattr(settlement, 'is_city', False)

    settlement.days_since_attack += 1
    settlement.days_since_market += 1
    settlement.days_since_celebration += 1
    
    if settlement.got_blessing_yesterday and settlement.days_since_celebration >= CELEBRATION_COOLDOWN:
        settlement.got_blessing_yesterday = False
        settlement.days_since_celebration = 0
        event = SettlementEvent.CELEBRATION
    
    elif settlement.days_since_attack <= 1 or random() < 0.02:
        event = SettlementEvent.MOURNING
    
    elif settlement.current_event == SettlementEvent.MARKET_DAY and settlement.life < settlement.max_life:
        event = SettlementEvent.REPAIRS
    
    elif settlement.days_since_market >= MARKET_DAY_INTERVAL:
        settlement.days_since_market = 0
        event = SettlementEvent.MARKET_DAY
    
    else:
        event = SettlementEvent.NONE
    
    settlement.current_event = event

    planner = settlement.plan_day()

    if event == SettlementEvent.MOURNING:
        if is_village and settlement.has_village_hero and random() < VILLAGE_HERO_CHANCE_MOURNING:
            planner.add(ActionType.SPAWN_HERO)
    else:
        planner.add(ActionType.EXPAND)

        if event == SettlementEvent.NONE:

            if random() < TRADE_CHANCE:
                target = finders.find_trade_target(settlement)
                if target:
                    planner.add(ActionType.TRADE, target)

            if is_village and random() < VILLAGE_HERO_CHANCE_NONE:
                planner.add(ActionType.SPAWN_HERO)

            if is_city and random() < CITY_HEAL_CHANCE:
                planner.add(ActionType.REPAIR)

        elif event in (SettlementEvent.MARKET_DAY, SettlementEvent.CELEBRATION):
            
            target = finders.find_trade_target(settlement)
            if target:
                planner.add(ActionType.TRADE, target)

            if is_city and (event == SettlementEvent.CELEBRATION or random() < CITY_HERO_CHANCE_MARKET):
                planner.add(ActionType.SPAWN_HERO)

        elif event == SettlementEvent.REPAIRS:
            planner.add(ActionType.REPAIR)
    
    planner.commit(randomize=True)