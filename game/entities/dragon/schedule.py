from typing import TYPE_CHECKING
from random import choice, random
from game.entities.base.scheduled import ActionType

from . import finders
from .types import DragonMood

if TYPE_CHECKING:
    from . import Dragon


def build_schedule(dragon: Dragon) -> None:
    """Build the day's schedule based on mood."""
    dragon.current_action = None
    
    dragon.mood = _determine_mood(dragon)
    dragon.days_since_hungry += 1
    planner = dragon.plan_day()
    
    if dragon.mood == DragonMood.DREARY:
        # Dreary: tend hoard, attack if not good.
        planner.add(ActionType.TEND_HOARD)
        if dragon.is_evil:
            settlement = finders.find_settlement_target(dragon)
            if settlement:
                planner.add(ActionType.ATTACK, settlement)

    elif dragon.mood == DragonMood.INSPIRED:
        # Inspired: tend hoard, visit distant spirits.
        spirits = finders.find_spirits(dragon, distance_max=9999, distance_min=20, count=2, has_blessing=False)
        
        if spirits:
            planner.add(ActionType.TEND_SPIRIT, spirits[0])
        
        planner.add(ActionType.TEND_HOARD)
        
        if len(spirits) > 1:
            planner.add(ActionType.TEND_SPIRIT, spirits[1])

    elif dragon.mood == DragonMood.PENSIVE:
        # Pensive: feed once, tend nearby spirit.
        planner.add(ActionType.FEED)
        spirits = finders.find_spirits(dragon, has_blessing=False)
        if spirits:
            planner.add(ActionType.TEND_SPIRIT, spirits[0])

    elif dragon.mood == DragonMood.HUNGRY:
        # Hungry: feed, rest, feed again.
        planner.add(ActionType.FEED)
        
        if dragon.is_evil:
            target = choice([finders.find_human_target(dragon), finders.find_settlement_target(dragon)])
            planner.add(ActionType.ATTACK, target) if target else None
        
        planner.add(ActionType.REST)
        
        if not dragon.is_anthropophage:
            planner.add(ActionType.FEED)
        
            if dragon.is_evil:
                target = choice([finders.find_human_target(dragon), finders.find_settlement_target(dragon)])
                planner.add(ActionType.ATTACK, target) if target else None

    elif dragon.mood == DragonMood.COVETOUS:
        planner.add(ActionType.ATTACK)
    
    planner.commit()

def _determine_mood(dragon: Dragon) -> DragonMood:
    """Determine today's mood based on conditions."""
    # Hungry every 3 days (unless greed)
    if dragon.days_since_hungry >= 3:
        dragon.days_since_hungry = 0
        if dragon.is_greed:
            return DragonMood.COVETOUS
        return DragonMood.HUNGRY
    
    # Covetous occasionally
    if not dragon.is_good and random() < 0.2:
        return DragonMood.COVETOUS
    
    # Random between dreary, inspired, pensive
    roll = random()
    if roll < 0.3:
        return DragonMood.DREARY
    elif roll < 0.6:
        return DragonMood.INSPIRED
    else:
        return DragonMood.PENSIVE