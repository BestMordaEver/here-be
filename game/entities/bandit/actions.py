"""Bandit actions, encounters, and engagement resolution."""
from random import randint
from typing import TYPE_CHECKING, Optional

from game.entities.base.entity import EngagementType, Entity
from game.entities.base.scheduled import Scheduled, ScheduledAction, ActionType
from game.entities.dragon.types import DragonType
from .types import BanditBehavior, FEAR_RADIUS, MAX_BLESSINGS, ATTACK_RANGE

if TYPE_CHECKING:
    from . import Bandit
    from game.entities.dragon.domain import Domain
    from game.entities.settlement.settlement import Settlement


# ---------------------------------------------------------------------------
# Action dispatch
# ---------------------------------------------------------------------------

def start_action(bandit: 'Bandit', action: ScheduledAction) -> None:
    """Begin executing a scheduled action."""
    Scheduled.start_action(bandit, action)

    if action.action_type == ActionType.MOVE_TO:
        if isinstance(action.target, tuple):
            bandit.set_target(action.target)
        elif isinstance(action.target, Entity):
            bandit.set_target(action.target.coordinates)
        else:
            bandit.complete_current_action()

    elif action.action_type == ActionType.WANDER:
        x = bandit.coordinates[0] + randint(-15, 15)
        y = bandit.coordinates[1] + randint(-15, 15)
        x = max(0, min(bandit.world.WIDTH - 1, x))
        y = max(0, min(bandit.world.HEIGHT - 1, y))
        bandit.set_target((x, y))

    elif action.action_type == ActionType.IDLE:
        bandit.complete_current_action()

    elif action.action_type == ActionType.ATTACK:
        if action.target and isinstance(action.target, Entity):
            bandit.set_target(action.target)
        else:
            bandit.complete_current_action()

    elif action.action_type == ActionType.PILLAGE:
        if action.target and isinstance(action.target, Entity):
            bandit.set_target(action.target.coordinates)
        else:
            bandit.complete_current_action()


# ---------------------------------------------------------------------------
# Arrival
# ---------------------------------------------------------------------------

def on_arrival(bandit: 'Bandit') -> None:
    """Called when arriving at destination."""
    if not bandit.current_action:
        return

    action = bandit.current_action

    if action.action_type == ActionType.ATTACK:
        _execute_attack(bandit)
    elif action.action_type == ActionType.PILLAGE:
        _execute_pillage(bandit)
    else:
        bandit.complete_current_action()


def _execute_attack(bandit: 'Bandit') -> None:
    """Initiate engagement with target.

    Per user specification:
    - ROBBERY for caravans (halt + steal blessing)
    - COMBAT for settlements (deal damage + steal blessings)
    - COMBAT for heroes
    """
    target = bandit.target_entity
    if not target or not target.is_alive:
        bandit.complete_current_action()
        return

    target_type = target.__class__.__name__

    if target_type == 'Caravan':
        bandit.engage(EngagementType.ROBBERY, target)
    elif target_type in ('Village', 'City', 'Camp'):
        bandit.engage(EngagementType.COMBAT, target)
    elif target_type == 'Hero':
        bandit.engage(EngagementType.COMBAT, target)
    else:
        bandit.complete_current_action()


def _execute_pillage(bandit: 'Bandit') -> None:
    """Pillage a treasury or ruins using engagement system."""
    from game.entities.dragon.domain import Domain
    from game.entities.settlement.settlement import Settlement
    target = bandit.target_entity
    if not target:
        bandit.complete_current_action()
        return

    can_pillage = False
    if isinstance(target, Settlement) and target.can_be_pillaged():
        can_pillage = True
    elif isinstance(target, Domain) and target.treasure > 0:
        can_pillage = True

    if can_pillage:
        bandit.engage(EngagementType.PILLAGING, target, location=target.coordinates)
    else:
        bandit.think("Nothing left to take.")
        bandit.complete_current_action()

# ---------------------------------------------------------------------------
# Encounter checks (called during movement ticks)
# ---------------------------------------------------------------------------

def check_for_encounters(bandit: 'Bandit') -> None:
    """Check for dragons — flee if nearby.

    Bandits do NOT flee from heroes preemptively; they don't know the
    hero's mood until combat resolves.
    """
    if bandit.current_action and bandit.current_action.action_type == ActionType.FLEE:
        return
    
    if bandit.is_sleeping():
        return

    # Lurking bandits ambush passing caravans
    if bandit.behavior == BanditBehavior.LURKING and bandit.is_in_forest():
        caravans = bandit.get_nearby_entities(ATTACK_RANGE, 'Caravan')
        caravan = caravans[0] if caravans else None
        if caravan:
            bandit.interrupt_current(ScheduledAction(
                day=bandit.world.time.current_day,
                hour=bandit.world.time.current_hour,
                action_type=ActionType.ATTACK,
                target=caravan,
            ))
            bandit.set_target(caravan)

    nearby = bandit.get_nearby_entities(FEAR_RADIUS)

    for entity in nearby:
        if entity.__class__.__name__ == 'Dragon' and entity.is_alive:
            # Disengage from any current engagement first
            if bandit.is_engaged():
                bandit.disengage()

            bandit.fleeing_from = entity
            bandit.flee_from(entity)

            bandit.interrupt_current(ScheduledAction(
                day=bandit.world.time.current_day,
                hour=bandit.world.time.current_hour,
                action_type=ActionType.FLEE,
            ))
            return


# ---------------------------------------------------------------------------
# Engagement resolution (called at hour-end)
# ---------------------------------------------------------------------------

def resolve_engagement(bandit: 'Bandit') -> None:
    """Resolve the bandit's current engagement at hour-end."""
    if bandit.is_dead:
        bandit.current_engagement = None
        return

    engagement = Entity.resolve_engagement(bandit)
    if not engagement:
        return

    if engagement.engagement_type == EngagementType.ROBBERY:
        for other in engagement.get_others(bandit):
            if other.__class__.__name__ == 'Caravan' and other.is_alive:
                if other.blessing and bandit.blessings < MAX_BLESSINGS:
                    other.blessing = False
                    bandit.blessings += 1
                    bandit.think("A fine haul from a caravan!")
                elif other.blessing:
                    other.blessing = False
                    bandit.think("More trinkets than I can carry.")
                bandit.days_since_robbery = 0
                break
        else:
            bandit.think("The prey escaped.")

    elif engagement.engagement_type == EngagementType.COMBAT:
        others = engagement.get_others(bandit)

        protectors = 0
        bandits = 0
        attacking_dragons = 0

        for entity in others:
            if entity.__class__.__name__ == 'Hero' or (
                entity.__class__.__name__ == 'Dragon' and entity.is_good
            ):
                protectors += 1
            elif entity.__class__.__name__ == 'Dragon':
                attacking_dragons += 1
                if entity.dragon_type == DragonType.BRUTE:
                    attacking_dragons += 1
            elif entity.__class__.__name__ == 'Bandit':
                bandits += 1

        if bandits > 0 and bandits + attacking_dragons > protectors:
            for entity in others:
                if entity.__class__.__name__ == 'Bandit':
                    entity.transfer_from(settlement, entity.max_blessings)

    elif engagement.engagement_type == EngagementType.PILLAGING:
        from game.entities.dragon.domain import Domain
        from game.entities.settlement.settlement import Settlement
        can_take = MAX_BLESSINGS - bandit.blessings
        if can_take > 0:
            for other in engagement.participants:
                if other is bandit:
                    continue
                if isinstance(other, Settlement) and other.can_be_pillaged():
                    taken = other.pillage_ruins(can_take)
                    bandit.blessings += taken
                    bandit.days_since_robbery = 0
                    bandit.think(f"Looted {taken} blessing{'s' if taken > 1 else ''} from the ruins.")
                    break
                if isinstance(other, Domain) and other.treasure > 0:
                    taken = min(can_take, other.treasure)
                    other.treasure -= taken
                    bandit.blessings += taken
                    bandit.days_since_robbery = 0
                    bandit.think(f"Looted {taken} blessing{'s' if taken > 1 else ''} from the hoard.")
                    break

    bandit.complete_current_action()
