"""Hero actions - start_action, on_hour, encounters, engagement resolution."""
from random import random, randint
from typing import TYPE_CHECKING, Optional

from game.entities.base.entity import Entity, EngagementType
from game.entities.base.scheduled import Scheduled, ScheduledAction, ActionType
from game.entities.base.thinking import Memory, MemoryType
from .types import (
    HeroMood, PROTECTION_RANGE, PATROL_RANGE, PARTY_SIZE,
)
from . import finders

if TYPE_CHECKING:
    from . import Hero
    from game.entities.dragon.domain import Domain
    from game.entities.settlement.settlement import Settlement


# ---------------------------------------------------------------------------
# Action dispatch
# ---------------------------------------------------------------------------

def _default_action(hero: 'Hero') -> None:
    """Fall back to the next scheduled action or rest."""
    scheduled = hero.schedule.get(hero.world.time.current_day, hero.world.time.current_hour)
    if not scheduled or hero.current_action is scheduled:
        start_action(hero, ScheduledAction(
            day=hero.world.time.current_day,
            hour=hero.world.time.current_hour,
            action_type=ActionType.REST,
        ))
    else:
        start_action(hero, scheduled)


def start_action(hero: 'Hero', action: ScheduledAction) -> None:
    """Begin executing a scheduled action."""
    Scheduled.start_action(hero, action)

    if action.action_type in (ActionType.WAKE, ActionType.SLEEP):
        return  # Handled by Scheduled

    if action.action_type in (ActionType.MOVE_TO, ActionType.PROTECT, ActionType.PILLAGE):
        if action.target:
            hero.set_target(action.target)
        else:
            hero.complete_current_action()

    elif action.action_type == ActionType.REST:
        hero.engage(EngagementType.RESTING, location=hero.coordinates)

    elif action.action_type == ActionType.PATROL:
        x = hero.coordinates[0] + randint(-PATROL_RANGE, PATROL_RANGE)
        y = hero.coordinates[1] + randint(-PATROL_RANGE, PATROL_RANGE)
        x = max(0, min(hero.world.WIDTH - 1, x))
        y = max(0, min(hero.world.HEIGHT - 1, y))
        hero.set_target((x, y))

    elif action.action_type == ActionType.ESCORT:
        if action.target and isinstance(action.target, Entity):
            hero.set_target(action.target)
        else:
            hero.complete_current_action()

    elif action.action_type == ActionType.ATTACK:
        if action.target:
            hero.set_target(action.target)
        else:
            hero.complete_current_action()

    elif action.action_type == ActionType.RETURN_HOME:
        if hero.home and hero.home.is_alive:
            hero.set_target(hero.home)
        else:
            hero.complete_current_action()


# ---------------------------------------------------------------------------
# Arrival
# ---------------------------------------------------------------------------

def on_movement_complete(hero: 'Hero') -> None:
    """Called when the hero arrives at their destination."""
    if not hero.current_action:
        return

    action = hero.current_action
    target = hero.target_entity

    if action.action_type in (ActionType.MOVE_TO, ActionType.PATROL, ActionType.RETURN_HOME):
        hero.complete_current_action()

    elif action.action_type == ActionType.REST:
        hero.engage(EngagementType.RESTING, location=hero.coordinates)

    elif action.action_type == ActionType.ESCORT:
        # Keep following if target still alive and moving
        if target and target.is_alive:
            hero.set_target(target)
        else:
            hero.complete_current_action()

    elif action.action_type == ActionType.PROTECT:
        if target and target.is_alive:
            if target.current_engagement:
                hero.join_engagement(target.current_engagement)
            else:
                hero.engage(EngagementType.RESTING, location=hero.coordinates)
        else:
            hero.engage(EngagementType.RESTING, location=hero.coordinates)

    elif action.action_type == ActionType.PILLAGE:
        hero.engage(EngagementType.PILLAGING, target, location=target.coordinates)

    elif action.action_type == ActionType.ATTACK:
        if target.is_alive:
            hero.engage(EngagementType.COMBAT, target)
        else:
            hero.complete_current_action()

# ---------------------------------------------------------------------------
# Hourly passive behavior
# ---------------------------------------------------------------------------

def on_hour(hero: 'Hero', hour: int) -> None:
    """Hourly tick: dispatch scheduled actions, then run passive behavior."""
    Scheduled.on_hour(hero, hour)

    if hero.is_sleeping():
        return

    # Sell blessings if in a city
    if hero.has_blessings:
        settlement = finders.find_settlement_at(hero)
        if settlement and settlement.__class__.__name__ == 'City':
            hero.transfer_to(settlement, hero.blessings)
            hero.think("Sold my treasures in the city.")

    # Adventurous heroes remember dragon lairs and try to form parties
    if hero.mood == HeroMood.ADVENTUROUS and not hero.party:
        for entity in hero.get_nearby_entities(PATROL_RANGE, 'Dragon', 'Domain'):
            if entity.coordinates not in hero.known_domains:
                hero.known_domains.add(entity.coordinates)
                hero.days_domain_known[entity.coordinates] = 0
                hero.think("I've spotted a dragon lair!")
                hero.add_memory(Memory(
                    type=MemoryType.SAW_DOMAIN,
                    subject=entity,
                    location=entity.coordinates,
                    day=hero.world.time.current_day,
                    source=hero,
                ))

        if hero.known_domains and not hero.party:
            # Try to form a dragon-hunting party with nearby heroes sharing domain knowledge
            nearby = [h for h in hero.get_nearby_entities(PATROL_RANGE, 'Hero') if not h.party]
            if len(nearby) >= PARTY_SIZE - 1:
                potential = [
                    h for h in nearby
                    if hero.known_domains & h.known_domains
                ]
                if len(potential) >= PARTY_SIZE - 1:
                    party = [hero] + potential[:PARTY_SIZE - 1]
                    hero.party = party
                    hero.party_leader = hero
                    for h in party[1:]:
                        h.party = party
                        h.party_leader = hero
                        h.mood = HeroMood.SUBSERVIENT
                        hero.acquaintances.add(h)
                        h.acquaintances.add(hero)
                    hero.think("Fellow heroes, let us band together!")

    # Active moods spot pillage opportunities
    if hero.mood in (HeroMood.ADVENTUROUS, HeroMood.MERCENARY, HeroMood.VENGEFUL):
        from game.entities.dragon.domain import Domain
        from game.entities.settlement.settlement import Settlement
        for entity in hero.world.get_entities_nearby(
            hero.coordinates, PATROL_RANGE, 'Village', 'City', 'Domain', alive_only=False
        ):
            if isinstance(entity, Settlement):
                if entity.can_be_pillaged():
                    hero.opportunistic_target = entity
                    hero.think("I see ruins that hold treasure!")
                    break
            elif isinstance(entity, Domain):
                if entity.is_treasury and entity.has_blessings:
                    hero.opportunistic_target = entity
                    hero.think("A dragon's hoard lies unguarded!")
                    break

    # Become acquaintances with heroes in the same settlement
    if hero.mood in (HeroMood.ADVENTUROUS, HeroMood.MERCENARY):
        settlement = finders.find_settlement_at(hero)
        if settlement:
            for other in hero.get_nearby_entities(10, 'Hero'):
                if settlement.occupies(other.coordinates):
                    hero.acquaintances.add(other)
                    other.acquaintances.add(hero)


# ---------------------------------------------------------------------------
# Encounter checks (called during movement ticks)
# ---------------------------------------------------------------------------

def check_for_encounters(hero: 'Hero') -> None:
    """Check for threats to respond to. May interrupt current action."""
    if hero.current_action and hero.current_action.action_type in (ActionType.ATTACK, ActionType.PROTECT):
        return  # Already in combat posture

    if hero.is_sleeping():
        return

    # Exchange events with nearby talkers
    for entity in hero.get_nearby_entities(PROTECTION_RANGE):
        if hasattr(entity, 'is_talker') and entity.is_talker:
            hero.exchange_memories(entity)

    nearby = hero.get_nearby_entities(
        PROTECTION_RANGE,
        'Bandit', 'Caravan', 'Village', 'City', 'Camp',
    )

    # Attack bandits (always if vengeful, 70% otherwise)
    for entity in nearby:
        if entity.__class__.__name__ == 'Bandit' and entity.is_alive:
            hero.add_memory(Memory(
                type=MemoryType.SAW_BANDIT,
                subject=entity,
                location=entity.coordinates,
                day=hero.world.time.current_day,
                source=hero,
            ))
            if hero.mood == HeroMood.VENGEFUL or random() < 0.7:
                hero.interrupt_current(ScheduledAction(
                    day=hero.world.time.current_day,
                    hour=hero.world.time.current_hour,
                    action_type=ActionType.ATTACK,
                    target=entity,
                ))
                hero.think("I shall protect the innocent!")
                return

    # Protect entities being victimized
    for entity in nearby:
        if entity.__class__.__name__ not in ('Caravan', 'Village', 'City', 'Camp'):
            continue
        if not entity.current_engagement:
            continue

        engagement = entity.current_engagement
        if engagement.engagement_type not in (EngagementType.ROBBERY, EngagementType.COMBAT):
            continue

        attacker = engagement.started_by
        if not attacker.is_alive or attacker is hero:
            continue

        # Blade dragons cannot be defended against
        if attacker.__class__.__name__ == 'Dragon':
            hero.add_memory(Memory(
                type=MemoryType.SAW_DRAGON,
                subject=attacker,
                location=attacker.coordinates,
                day=hero.world.time.current_day,
                source=hero,
            ))
            from game.entities.dragon.types import DragonType
            if attacker.dragon_type == DragonType.BLADE:
                continue

        # Mercenaries prioritize the caravan they're escorting
        if hero.mood == HeroMood.MERCENARY and entity.__class__.__name__ == 'Caravan':
            if hero.target_entity is not entity:
                continue

        hero.interrupt_current(ScheduledAction(
            day=hero.world.time.current_day,
            hour=hero.world.time.current_hour,
            action_type=ActionType.ATTACK,
            target=attacker,
        ))
        hero.think("I shall protect the innocent!")
        return


# ---------------------------------------------------------------------------
# Engagement resolution (called at hour-end)
# ---------------------------------------------------------------------------

def resolve_engagement(hero: 'Hero') -> None:
    """Resolve the hero's current engagement at hour-end."""
    if hero.is_dead:
        hero.current_engagement = None
        return

    engagement = Entity.resolve_engagement(hero)
    if not engagement:
        return

    if engagement.engagement_type == EngagementType.RESTING:
        pass  # Nothing to resolve

    elif engagement.engagement_type == EngagementType.PILLAGING:
        can_take = hero.available_space()
        if can_take > 0:
            for other in engagement.participants:
                if other is hero:
                    continue
                if isinstance(other, Settlement) and other.can_be_pillaged():
                    taken = other.transfer_to(hero, can_take)
                    hero.think(f"Claimed {taken} blessing{'s' if taken > 1 else ''} from the ruins.")
                    break
                if isinstance(other, Domain) and other.has_blessings:
                    taken = other.transfer_to(hero, can_take)
                    if not other.has_blessings:
                        other.die("pillaged")
                    if taken > 0:
                        hero.think(f"Claimed {taken} blessing{'s' if taken > 1 else ''} from the hoard.")
                    break
            else:
                # Pillageable location (from engagement.location)
                loc = engagement.location
                if loc and loc is not hero:
                    if isinstance(loc, Settlement) and loc.can_be_pillaged():
                        taken = loc.transfer_to(hero, can_take)
                        hero.think(f"Claimed {taken} blessing{'s' if taken > 1 else ''} from the ruins.")
                    elif isinstance(loc, Domain) and loc.has_blessings:
                        taken = loc.transfer_to(hero, can_take)
                        if not loc.has_blessings:
                            loc.die("pillaged")
                        if taken > 0:
                            hero.think(f"Claimed {taken} blessing{'s' if taken > 1 else ''} from the hoard.")

    elif engagement.engagement_type == EngagementType.COMBAT:
        from game.entities.dragon.types import DragonType

        dragon_opponent = next(
            (e for e in engagement.participants if e.__class__.__name__ == 'Dragon'), None
        )

        if dragon_opponent:
            if hero.party and len(hero.party) >= PARTY_SIZE:
                # Party fight: dragon handles its own death in dragon's resolver.
                # Each hero determines its own fate deterministically by party position.
                sacrifices = 2 if dragon_opponent.dragon_type == DragonType.BLADE else 1
                sorted_party = sorted(hero.party, key=id)
                am_casualty = hero in sorted_party[:sacrifices]

                hero.party = None
                hero.party_leader = None
                hero.mood = HeroMood.TIRED
                hero.consecutive_active_days = 0

                if am_casualty:
                    hero.die("slain by dragon")
                    return
                else:
                    hero.think("The beast is slain, but at great cost.")
            elif dragon_opponent.is_alive:
                # Solo fight against a living dragon
                if hero.mood != HeroMood.VENGEFUL:
                    hero.tired_today = True

                is_blade = dragon_opponent.dragon_type == DragonType.BLADE
                if hero.tired_today and (is_blade or not finders.find_settlement_at(hero)):
                    hero.die("slain by dragon")
                    return
                else:
                    hero.think("I barely survived the encounter.")

        # Bandit in engagement: bandit handles its own death in bandit's resolver.
        if any(e.__class__.__name__ == 'Bandit' for e in engagement.participants):
            if hero.mood == HeroMood.VENGEFUL:
                hero.think("Justice is served.")

    hero.complete_current_action()
