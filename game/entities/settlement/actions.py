from random import choice, random
from typing import TYPE_CHECKING, Optional
from game.entities.base.entity import EngagementType, Engagement, Entity
from game.entities.base.scheduled import Scheduled, ScheduledAction, ActionType
from game.entities.spirit import SpiritType
from game.entities.caravan import CaravanMission
from game.entities.dragon.types import DragonType
from .types import SettlementEvent
from . import finders 

if TYPE_CHECKING:
    from .settlement import Settlement


def start_action(settlement: 'Settlement', action: ScheduledAction) -> None:
    """
    Start executing a scheduled action.
    """
    Scheduled.start_action(settlement, action)

    if action == ActionType.EXPAND:
        settlement.try_expand(settlement)
    elif action == ActionType.TRADE:
        target = finders.find_trade_target(settlement)
        if target:
            settlement.send_caravan(target, CaravanMission.TRADE)
    elif action == ActionType.REPAIR:
        settlement.heal(1)
    elif action == ActionType.SPAWN_HERO:
        if not getattr(settlement, "has_village_hero", False):
            from game.entities.hero import Hero
            from .city import City
            
            hero = Hero(
                settlement.world,
                coordinates=settlement.get_spawn_point(),
                home=settlement,
                city_born=isinstance(settlement, City)
            )
            settlement.world.add_entity(hero)

            if settlement.current_event == SettlementEvent.MOURNING:
                settlement.has_village_hero = True


def resolve_engagement(settlement: 'Settlement') -> None:
    """Resolve an engagement at hour-end.
    
    Settlements are typically the *target* in engagements initiated by
    dragons or bandits.
    """
    engagement = Entity.resolve_engagement(settlement)
    if not engagement:
        return

    if engagement.engagement_type == EngagementType.COMBAT:
        others = engagement.get_others(settlement)

        has_protector = False    # Hero or good dragon joined the engagement
        attacked_by_bandit = False
        attacked_by_dragon = False
        attacked_by_blade = False  # Protector is irrelevant
        attacked_by_brute = False  # Heavy damage

        for entity in others:
            if entity.__class__.__name__ == 'Hero' or (
                entity.__class__.__name__ == 'Dragon' and entity.is_good
            ):
                has_protector = True
            elif entity.__class__.__name__ == 'Dragon':
                attacked_by_dragon = True
                if entity.dragon_type == DragonType.BLADE:
                    attacked_by_blade = True
                elif entity.dragon_type == DragonType.BRUTE:
                    attacked_by_brute = True
            elif entity.__class__.__name__ == 'Bandit':
                attacked_by_bandit = True

        if not has_protector or attacked_by_blade:
            if attacked_by_dragon:
                settlement.days_since_attack = 0
                if attacked_by_brute:
                    if settlement.__class__.__name__ == 'Camp':
                        settlement.die("destroyed by brute dragon")
                    else:
                        damage = max(0, settlement.life - 1)
                        if damage > 0:
                            settlement.hurt(damage, "brute dragon attack")
                        else:
                            settlement.hurt(1, "dragon attack")
                else:
                    settlement.hurt(1, "dragon attack")

            elif attacked_by_bandit:
                settlement.hurt(1, "bandit raid")

    settlement.complete_current_action()
