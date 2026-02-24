from random import choice, random
from typing import TYPE_CHECKING, Optional
from game.entities.base.entity import EngagementType, Entity
from game.entities.base.scheduled import Scheduled, ScheduledAction, ActionType
from game.entities.spirit import SpiritType

from .types import DragonType
from .schedule import DragonMood
from . import finders 

if TYPE_CHECKING:
    from . import Dragon
    
TEND_RADIUS_DRUID = 8    # Druids tend all spirits in this radius

# Encounter radii
DOMAIN_PROTECTION_RADIUS = 3  # Radius around domain for protection
VISION_RADIUS = 10   # How far dragons can see
TERRITORIAL_RADIUS = 12  # Radius for territorial attacks

def _default_action(dragon: Dragon) -> None:
    scheduled_action = dragon.schedule.get(dragon.world.time.current_day, dragon.world.time.current_hour)
    if not scheduled_action or dragon.current_action == scheduled_action:
        start_action(dragon, ScheduledAction(
            day=dragon.world.time.current_day,
            hour=dragon.world.time.current_hour,
            action_type=ActionType.REST))
    else:
        start_action(dragon, scheduled_action)

def on_movement_complete(dragon: Dragon) -> None:
    """Called when movement to target completes."""
    if not dragon.current_action:
        return
    
    action = dragon.current_action
    
    if action.action_type == ActionType.FEED:
        if dragon.is_herbivore:
            dragon.engage(EngagementType.FEEDING, location=dragon.destination)
        else:   # Human targets, can be shared
            if dragon.target_entity and dragon.target_entity.is_alive:
                if dragon.is_anthropophage:
                    dragon.engage(EngagementType.COMBAT, dragon.target_entity)
                else:   # Cattle and fish - not so much
                    if dragon.get_nearby_entities(2, 'Dragon'):
                        start_action(dragon, action)  
                    else:
                        dragon.engage(EngagementType.FEEDING, dragon.target_entity)
            else:	# Retry action if target was lost
                start_action(dragon, action)
    
    elif action.action_type == ActionType.REST:
        dragon.engage(EngagementType.RESTING, location=dragon.destination)
    
    elif action.action_type == ActionType.TEND_HOARD:
        dragon.engage(EngagementType.HOARDING, location=dragon.destination)
    
    elif action.action_type == ActionType.TEND_SPIRIT:
        if dragon.target_entity and dragon.target_entity.is_alive:
            dragon.engage(EngagementType.TENDING, dragon.target_entity)
        else:	# Retry action if target was lost
            start_action(dragon, action)
    
    elif action.action_type == ActionType.PROTECT:
        if dragon.target_entity and dragon.target_entity.is_alive and dragon.target_entity.current_engagement:
            dragon.join_engagement(dragon.target_entity.current_engagement)
        else:   # We're late - go home
            _default_action(dragon)

    elif action.action_type == ActionType.ATTACK:
        if dragon.target_entity and dragon.target_entity.is_alive:
            dragon.engage(EngagementType.COMBAT, dragon.target_entity)
        elif (dragon.mood == DragonMood.HUNGRY and dragon.is_anthropophage) or dragon.mood == DragonMood.COVETOUS:
            start_action(dragon, action)  # Retry finding a target if lost during attack
        else:	# Not hangry - go home
            _default_action(dragon)


def start_action(dragon: Dragon, action: ScheduledAction) -> None:
    """
    Start executing a scheduled action.
    May be called by schedule or to retry an action if target was lost.
    """
    Scheduled.start_action(dragon, action)

    if action.action_type in (ActionType.TEND_HOARD, ActionType.REST):
        target = dragon.domain
    elif action.action_type == ActionType.FEED:
        if dragon.is_carnivore:
            target = finders.find_cattle(dragon)
            if not target:
                spirits = finders.find_spirits(dragon, distance_max=9999, spirit_types=[SpiritType.LAKE])
                target = choice(spirits) if spirits else None
        elif dragon.is_herbivore:
            target = finders.find_grazing_spot(dragon)
        elif dragon.is_anthropophage:
            settlement = finders.find_settlement_target(dragon)
            human = finders.find_human_target(dragon)

            if settlement and human and dragon.get_distance(settlement.coordinates) < dragon.get_distance(human.coordinates):
                target = settlement
            else:
                target = human
            
    elif action.action_type == ActionType.ATTACK and dragon.mood == DragonMood.COVETOUS:
        target = finders.find_settlement_with_blessing(dragon) or finders.find_settlement_target(dragon)
        
    else:
        target = action.target
    
    if not target:
        _default_action(dragon)
        return

    dragon.set_target(target)
    

def check_for_encounters(dragon: Dragon) -> Optional[ScheduledAction]:
    """Check for entities that trigger encounters during other actions."""
    if dragon.current_action and (dragon.current_action.action_type in (ActionType.ATTACK, ActionType.PROTECT)):
        return
    
    nearby = dragon.get_nearby_entities(VISION_RADIUS, 'Hero', 'Caravan', 'Bandit', 'Camp', 'Village', 'City')

    # All dragons attack humans that are too close to their domain
    for e in dragon.domain.get_nearby_entities(	# What counts as "too close" varies
        TERRITORIAL_RADIUS if dragon.is_territorial else DOMAIN_PROTECTION_RADIUS, 
        'Hero', 'Caravan', 'Bandit', 'Camp', 'Village', 'City'):
        if e in nearby:
            dragon.interrupt_current(ScheduledAction(
                day=dragon.world.time.current_day,
                hour=dragon.world.time.current_hour,
                action_type=ActionType.ATTACK,
                target=e,
            ))
            return
    
    if dragon.current_action and (
        (	# Evil dragons attack humans near spirits they are tending
            dragon.is_evil and
            dragon.current_action.action_type == ActionType.TEND_SPIRIT
        ) or (	# Dreary dragons attack humans when tending the hoard, unless good
            not dragon.is_good and
            dragon.mood == DragonMood.DREARY and
            dragon.current_action.action_type == ActionType.TEND_HOARD
        )
    ):
        dragon.interrupt_current(ScheduledAction(
            day=dragon.world.time.current_day,
            hour=dragon.world.time.current_hour,
            action_type=ActionType.ATTACK,
            target=choice(nearby),  # Attack a random nearby human
        ))
        return
    
    # Good dragons protect humans from threats
    if dragon.is_good:
        for entity in nearby:
            if entity.__class__.__name__ != 'Bandit' and entity.current_engagement:
                # Check if they're being threatened (engaged by attacker)
                engagement = entity.current_engagement
                if engagement.engagement_type in (EngagementType.ROBBERY, EngagementType.COMBAT):
                    if engagement.started_by.is_alive:
                        dragon.interrupt_current(ScheduledAction(
                            day=dragon.world.time.current_day,
                            hour=dragon.world.time.current_hour,
                            action_type=ActionType.PROTECT,
                            target=engagement.started_by,
                        ))


def resolve_engagement(dragon: Dragon) -> None:
    """Resolve an engagement at hour-end."""
    engagement = Entity.resolve_engagement(dragon)
    if not engagement:
        return

    if engagement.engagement_type in (
        EngagementType.FEEDING, # Hunger handled by schedule
        EngagementType.RESTING, # Just passing time
        EngagementType.TENDING, # Resolved by the spirit
        EngagementType.HOARDING # Resolved by the domain
    ):
        pass
    
    elif engagement.engagement_type == EngagementType.COMBAT:
        # Hungry anthropophage attempts to feed on human target
        if dragon.is_anthropophage and dragon.mood in (DragonMood.HUNGRY, DragonMood.PENSIVE):
            from game.entities.hero import HeroMood

            settlement_or_bandit = False
            tired_hero_alone = False
            has_caravan = False
            has_protector = False
            for e in engagement.participants:
                if e.__class__.__name__ in ('Camp', 'Village', 'City', 'Bandit'):
                    settlement_or_bandit = True
                    break
                elif (
                    e.__class__.__name__ == 'Hero' and
                    e.mood == HeroMood.TIRED and
                    not e.get_nearby_entities(2, 'Camp', 'Village', 'City')
                ):
                    tired_hero_alone = True
                    break
                elif e.__class__.__name__ == 'Caravan':
                    has_caravan = True
                    if dragon.dragon_type == DragonType.BLADE:
                        break
                elif e.__class__.__name__ == 'Hero':
                    has_protector = True
                elif e.__class__.__name__ == 'Dragon' and e != dragon and e.is_good:
                    has_protector = True

            if (
                settlement_or_bandit or 
                tired_hero_alone or 
                (has_caravan and (dragon.dragon_type == DragonType.BLADE or not has_protector))
            ):

                feed_action = dragon.schedule.find_future_action(
                    ActionType.FEED,
                    dragon.world.time.current_day,
                    dragon.world.time.current_hour
                )
                if feed_action:
                    dragon.schedule.remove(feed_action.day, feed_action.hour)
            
            else:
                dragon.schedule.push_action(
                    dragon.current_action.day,
                    dragon.current_action.hour,
                )
            

        # Fragile dragons may shed a blessing when fighting
        if dragon.dragon_type == DragonType.FRAGILE:
            if random() < 0.3:  # 30% chance to drop blessing during attack
                from game.entities.blessing import drop_blessing
                drop_blessing(dragon.world, dragon.coordinates, 1)
    
    dragon.complete_current_action()