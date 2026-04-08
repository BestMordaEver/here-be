"""Hero scheduling - mood determination and daily schedule building."""
from typing import TYPE_CHECKING
from random import random

from game.entities.base.scheduled import ActionType
from .types import (
    HeroMood, TIRED_AFTER_DAYS, TIRED_THRESHOLD, PARTY_SIZE,
)
from . import finders

if TYPE_CHECKING:
    from . import Hero


def determine_mood(hero: 'Hero') -> HeroMood:
    """Determine today's mood based on hero state and conditions."""
    # Tired for the rest of the day from combat
    if hero.tired_today:
        return HeroMood.TIRED

    # Permanently tired after 48 days
    if hero.is_permanently_tired or hero.age_days >= TIRED_AFTER_DAYS:
        hero.is_permanently_tired = True
        return HeroMood.TIRED

    # Following a party leader
    if hero.party_leader and hero.party_leader is not hero:
        return HeroMood.SUBSERVIENT

    # Leading a full party
    if hero.party and len(hero.party) >= PARTY_SIZE:
        return HeroMood.FOREBODING

    # Vengeful if a friend died recently
    if hero.dead_friend:
        hero.dead_friend = None  # Clear after one day of vengeance
        return HeroMood.VENGEFUL

    # Opportunistic if we spotted ruins/treasury, or domain known for 10+ days
    if hero.opportunistic_target and hero.opportunistic_target.is_alive:
        hero.opportunistic_target = None
        return HeroMood.OPPORTUNISTIC

    if hero.days_domain_known:
        for domain, days in hero.days_domain_known.items():
            if days >= 10:
                return HeroMood.OPPORTUNISTIC

    # Tired after consecutive active days
    if hero.consecutive_active_days >= TIRED_THRESHOLD:
        hero.consecutive_active_days = 0
        return HeroMood.TIRED

    # Random between mercenary and adventurous
    if random() < 0.3:
        return HeroMood.MERCENARY
    return HeroMood.ADVENTUROUS


def build_schedule(hero: 'Hero') -> None:
    """Build the day's schedule based on mood."""
    hero.current_action = None
    hero.tired_today = False  # Reset daily combat tiredness

    hero.mood = determine_mood(hero)

    # Increment domain knowledge age
    for domain in list(hero.days_domain_known.keys()):
        hero.days_domain_known[domain] += 1

    # Track consecutive active days
    if hero.mood != HeroMood.TIRED:
        hero.consecutive_active_days += 1

    planner = hero.plan_day()

    if hero.mood == HeroMood.MERCENARY:
        caravans = hero.get_nearby_entities(30, 'Caravan')
        caravan = caravans[0] if caravans else None
        if caravan:
            planner.add(ActionType.ESCORT, caravan)
        else:
            _schedule_adventurous(hero, planner)

    elif hero.mood == HeroMood.TIRED:
        settlement = finders.find_settlement_at(hero)
        if settlement:
            planner.add(ActionType.PROTECT, settlement)
            planner.add(ActionType.REST)
            planner.add(ActionType.PROTECT, settlement)
            hero.think(f"I shall guard {settlement.name}.")
        else:
            # Tired heroes are attracted to markets
            from game.entities.settlement.settlement import Settlement
            closest_market = None
            closest_dist = float('inf')
            for entity in hero.world.entities:
                if isinstance(entity, Settlement) and entity.is_alive:
                    if entity.__class__.__name__ in ('Village', 'City'):
                        if entity.current_event is not None and entity.current_event.value == 'market_day':
                            dist = hero.get_distance(entity.coordinates)
                            if dist < closest_dist:
                                closest_market = entity
                                closest_dist = dist
            if closest_market:
                planner.add(ActionType.MOVE_TO, closest_market)
                planner.add(ActionType.REST)
                hero.think("I hear there's a market today...")
            elif hero.home and hero.home.is_alive:
                planner.add(ActionType.MOVE_TO, hero.home)
                planner.add(ActionType.REST)
            else:
                planner.add(ActionType.REST)

    elif hero.mood == HeroMood.ADVENTUROUS:
        _schedule_adventurous(hero, planner)

    elif hero.mood == HeroMood.OPPORTUNISTIC:
        target = finders.find_pillage_target(hero)
        if target:
            planner.add(ActionType.MOVE_TO, target)
            planner.add(ActionType.PILLAGE, target)
        else:
            from game.entities.dragon.domain import Domain
            unguarded = None
            for entity in hero.world.entities:
                if isinstance(entity, Domain) and entity.is_alive:
                    if entity.owner:
                        dragon = entity.owner
                        if dragon.is_alive and dragon.get_distance(entity.coordinates) > 15:
                            unguarded = entity
                            break
            if unguarded:
                planner.add(ActionType.MOVE_TO, unguarded)
                planner.add(ActionType.PILLAGE, unguarded)
            else:
                _schedule_adventurous(hero, planner)

    elif hero.mood == HeroMood.VENGEFUL:
        settlements = finders.find_remote_settlements(hero, count=2)
        if settlements:
            planner.add(ActionType.PATROL)
            planner.add(ActionType.MOVE_TO, settlements[0])
            planner.add(ActionType.PATROL)
            if len(settlements) > 1:
                planner.add(ActionType.MOVE_TO, settlements[1])
        else:
            planner.add(ActionType.PATROL)
            planner.add(ActionType.PATROL)
            planner.add(ActionType.PATROL)
        hero.think("I shall avenge the fallen.")

    elif hero.mood == HeroMood.FOREBODING:
        if not hero.party:
            _schedule_adventurous(hero, planner)
        else:
            known_domain = None
            for domain_coords in hero.known_domains:
                for entity in hero.world.entities:
                    if entity.__class__.__name__ == 'Domain' and entity.is_alive:
                        if entity.coordinates == domain_coords:
                            known_domain = entity
                            break
                if known_domain:
                    break
            if known_domain:
                planner.add(ActionType.MOVE_TO, known_domain)
                planner.add(ActionType.ATTACK, known_domain)
            else:
                _schedule_adventurous(hero, planner)

    elif hero.mood == HeroMood.SUBSERVIENT:
        if hero.party_leader:
            planner.add(ActionType.ESCORT, hero.party_leader)
        else:
            hero.party = None
            _schedule_adventurous(hero, planner)

    planner.commit()

    hero.think(f"Today I feel {hero.mood.value}.")


# ---------------------------------------------------------------------------
# Per-mood schedule helpers
# ---------------------------------------------------------------------------

def _schedule_adventurous(hero: 'Hero', planner) -> None:
    """Travel to remote settlements, occasionally patrol."""
    settlements = finders.find_remote_settlements(hero, count=2)

    if settlements:
        planner.add(ActionType.MOVE_TO, settlements[0])
        if random() < 0.5:
            planner.add(ActionType.PATROL)
        if len(settlements) > 1:
            planner.add(ActionType.MOVE_TO, settlements[1])
    else:
        planner.add(ActionType.PATROL)
        planner.add(ActionType.PATROL)