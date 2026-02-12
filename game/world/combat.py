"""Combat and engagement resolution for entity encounters.

Engagement System:
- Entities initiate engagements (combat, robbery, etc.) when they meet
- Engagements persist until hour-end or interruption
- Resolution happens at on_hour_end(), applying damage/effects

Functions are split into:
- initiate_X: Start an engagement between entities
- resolve_X: Apply the outcome of an engagement at hour-end
"""
from typing import TYPE_CHECKING, Optional
from random import choice

if TYPE_CHECKING:
    from game.entities.base.settlement import Settlement
    from game.entities.caravan import Caravan
    from game.entities.bandit import Bandit
    from game.entities.dragon import Dragon
    from game.entities.hero.hero import Hero

from game.entities.base import Engagement, EngagementType


# =============================================================================
# ENGAGEMENT INITIATION
# These functions create engagements. Resolution happens at hour-end.
# =============================================================================

def initiate_robbery(bandit: 'Bandit', target: 'Caravan | Settlement') -> Engagement:
    """
    Bandit initiates robbery on a caravan or settlement.
    Does NOT check for hero protection - that happens during the hour as an interrupt.
    
    Returns:
        The created engagement
    """
    engagement = bandit.engage(target, EngagementType.ROBBERY)
    return engagement


def initiate_combat(attacker: 'Bandit | Hero | Dragon', defender, can_be_interrupted: bool = True) -> Engagement:
    """
    Initiate combat between two entities.
    Actual damage is dealt at resolution (on_hour_end).
    
    Args:
        attacker: Entity starting the combat
        defender: Entity being attacked
        world: The game world
        can_be_interrupted: If False (e.g., blade dragons), heroes cannot protect
    
    Returns:
        The created engagement
    """
    engagement = attacker.engage(defender, EngagementType.COMBAT, can_be_interrupted=can_be_interrupted)
    return engagement


def initiate_protection(protector, protected) -> Optional['Engagement']:
    """
    Hero (or good dragon) initiates protection of a target.
    
    Returns:
        The created engagement, or None if initiation failed
    """
    if not hasattr(protector, 'engage'):
        return None
    
    engagement = protector.engage(protected, EngagementType.PROTECTING)
    
    if hasattr(protector, 'think'):
        protector.think("I shall protect the innocent.")
    
    return engagement


def initiate_pillage(pillager, target) -> Optional['Engagement']:
    """
    Hero or bandit initiates pillaging of ruins, treasury, or unguarded domain.
    
    Returns:
        The created engagement, or None if initiation failed
    """
    if not hasattr(pillager, 'engage'):
        return None
    
    engagement = pillager.engage(target, EngagementType.PILLAGING)
    
    if hasattr(pillager, 'think'):
        target_name = getattr(target, 'name', target.__class__.__name__)
        pillager.think(f"I search through the {target_name} for valuables.")
    
    return engagement


# =============================================================================
# ENGAGEMENT RESOLUTION
# These functions apply outcomes. Called from entity.on_hour_end().
# =============================================================================

def resolve_robbery(engagement: 'Engagement') -> None:
    """
    Resolve a robbery engagement at hour-end.
    Bandit steals blessing from caravan/settlement.
    """
    bandit = engagement.initiator
    target = engagement.target
    target_type = target.__class__.__name__
    
    if not bandit.is_alive:
        return
    
    if target_type == 'Caravan':
        _resolve_caravan_robbery(bandit, target)
    elif target_type in ('Village', 'City'):
        _resolve_settlement_robbery(bandit, target)


def _resolve_caravan_robbery(bandit, caravan) -> None:
    """Resolve bandit robbing caravan - steal blessing if any."""
    if not caravan.is_alive:
        return
    
    if caravan.blessing:
        caravan.blessing = False
        if bandit.blessings < 3:  # MAX_BLESSINGS
            bandit.blessings += 1
            bandit.days_since_robbery = 0
    
    bandit.days_since_robbery = 0


def _resolve_settlement_robbery(bandit, settlement) -> None:
    """Resolve bandit raiding settlement - deal damage, no mourning."""
    if not settlement.is_alive:
        return
    
    settlement.hurt(1, 'bandit raid')
    bandit.days_since_robbery = 0


def resolve_combat(engagement: 'Engagement') -> None:
    """
    Resolve a combat engagement at hour-end.
    Outcome depends on combatant types.
    """
    attacker = engagement.initiator
    defender = engagement.target
    
    if not attacker.is_alive:
        return
    if hasattr(defender, 'is_alive') and not defender.is_alive:
        return
    
    attacker_type = attacker.__class__.__name__
    defender_type = defender.__class__.__name__
    
    if attacker_type == 'Dragon':
        _resolve_dragon_combat(attacker, defender, defender_type)
    elif attacker_type == 'Bandit':
        _resolve_bandit_combat(attacker, defender, defender_type)
    elif attacker_type == 'Hero':
        _resolve_hero_combat(attacker, defender, defender_type)

def _resolve_dragon_combat(dragon, defender, defender_type: str) -> None:
    """Resolve dragon attacking something."""
    from random import random
    
    # Fragile dragons may shed a blessing when fighting
    if dragon.dragon_type == 'fragile' and dragon.blessings > 0:
        if random() < 0.3:  # 30% chance to drop blessing during attack
            from game.entities.blessing import drop_blessing
            dragon.blessings -= 1
            drop_blessing(dragon.world, dragon.coordinates, 1)
            dragon.think("A piece of my hoard scatters!")
    
    if defender_type == 'Caravan':
        dragon.think("The caravan is no more.")
        defender.die("dragon attack")
        
    elif defender_type == 'Bandit':
        dragon.think("Vermin crushed.")
        defender.die("dragon attack")
        
    elif defender_type == 'Hero':
        _resolve_dragon_vs_hero(dragon, defender)
        
    elif defender_type == 'Camp':
        if dragon.dragon_type == 'brute':
            defender.die("dragon")
            dragon.think("The camp is obliterated.")
        else:
            defender.hurt(1, 'dragon attack')
            dragon.think("The workers flee.")
            
    elif defender_type in ('Village', 'City'):
        defender.hurt(1, 'dragon attack')
        defender.days_since_attack = 0  # Trigger mourning
        
        # Brute type reduces settlement to 1 HP
        if dragon.dragon_type == 'brute':
            if defender.life > 1:
                defender.hurt(defender.life - 1, 'dragon crush')
        
        # Covetous dragons steal a blessing
        from game.entities.dragon import DragonMood
        if hasattr(dragon, 'mood') and dragon.mood == DragonMood.COVETOUS:
            if hasattr(defender, 'blessings') and defender.blessings > 0:
                defender.blessings -= 1
                dragon.blessings += 1
                dragon.think("I claim their blessing as my own.")
                return
        
        dragon.think("The settlement burns.")


def _resolve_dragon_vs_hero(dragon, hero) -> None:
    """Resolve dragon fighting a hero."""
    from game.entities.hero.hero import HeroMood
    from random import random
    
    # Fragile dragons may shed a blessing when fighting
    if dragon.dragon_type == 'fragile' and dragon.blessings > 0:
        if random() < 0.5:  # 50% chance to drop blessing
            from game.entities.blessing import drop_blessing
            dragon.blessings -= 1
            drop_blessing(dragon.world, dragon.coordinates, 1)
            dragon.think("A piece of my hoard falls away!")
    
    # Tired heroes outside settlements are killed
    if hero.mood == HeroMood.TIRED:
        # Check if hero is in a settlement
        in_settlement = False
        for entity in hero.world.entities:
            if hasattr(entity, 'occupies') and entity.is_alive:
                if entity.occupies(hero.coordinates):
                    in_settlement = True
                    break
        
        if not in_settlement:
            dragon.think("A weary hero falls.")
            hero.die("dragon attack")
            return
    
    # Fighting makes hero tired for the rest of the day (unless vengeful)
    if hero.mood != HeroMood.VENGEFUL:
        hero.tired_today = True
        hero.think("The battle wears on me...")
    
    dragon.think("A hero challenges me!")


def _resolve_bandit_combat(bandit, defender, defender_type: str) -> None:
    """Resolve bandit fighting something."""
    if defender_type == 'Hero':
        from game.entities.hero.hero import HeroMood
        # Bandit doesn't know hero's mood until now!
        if defender.mood == HeroMood.VENGEFUL:
            bandit.die("hero vengeance")
            defender.think("Justice served.")
            # Non-vengeful hero drives off bandit but doesn't kill
            # Bandit disengages and flees (handled by flee logic elsewhere)


def _resolve_hero_combat(hero, defender, defender_type: str) -> None:
    """Resolve hero fighting something."""
    from game.entities.hero.hero import HeroMood
    
    if defender_type == 'Dragon':
        if hero.party and len(hero.party) >= 4:  # PARTY_SIZE
            _party_attacks_dragon(hero.party, defender)
        else:
            # Solo hero can't kill dragon, just becomes tired for the day
            if hero.mood != HeroMood.VENGEFUL:
                hero.tired_today = True
            hero.think("I cannot face this beast alone...")
            
    elif defender_type == 'Bandit':
        if hero.mood == HeroMood.VENGEFUL:
            defender.die("hero vengeance")
            hero.think("One less scoundrel.")
        else:
            # Non-vengeful hero drives off bandit
            hero.think("Begone, villain!")
            # Bandit flees (handled by flee logic elsewhere)


def _party_attacks_dragon(party: list, dragon) -> None:
    """Full party kills dragon, but one hero must die (two for blade type)."""
    # Determine casualties - blade type kills two heroes
    deaths_required = 2 if dragon.dragon_type == 'blade' else 1
    
    casualties = []
    for _ in range(min(deaths_required, len(party))):
        victim = choice([h for h in party if h not in casualties and h.is_alive])
        casualties.append(victim)
    
    # Kill dragon
    dragon.die("hero party")
    
    # Kill casualties
    for victim in casualties:
        victim.think("For the realm...")
        victim.die("dragon fight")
        # Don't trigger vengeance for party members
        for hero in party:
            if hero.is_alive and victim in hero.acquaintances:
                hero.acquaintances.discard(victim)
    
    # Survivors become tired for the day and disband
    from game.entities.hero.hero import HeroMood
    for hero in party:
        if hero.is_alive:
            hero.tired_today = True
            hero.mood = HeroMood.TIRED
            hero.party = None
            hero.party_leader = None
            hero.think("The beast is slain... but at what cost.")


# =============================================================================
# ENGAGEMENT RESOLUTION DISPATCHER
# Called from entity.on_hour_end() to resolve the current engagement.
# =============================================================================

def resolve_engagement(engagement: 'Engagement') -> None:
    """
    Resolve an engagement based on its type.
    Called at hour-end for any active engagement.
    """
    if engagement.engagement_type == EngagementType.COMBAT:
        resolve_combat(engagement)
    elif engagement.engagement_type == EngagementType.ROBBERY:
        resolve_robbery(engagement)
    elif engagement.engagement_type == EngagementType.FEEDING:
        resolve_feeding(engagement)
    elif engagement.engagement_type == EngagementType.TENDING:
        resolve_tending(engagement)
    elif engagement.engagement_type == EngagementType.PILLAGING:
        resolve_pillage(engagement)

def resolve_feeding(engagement: 'Engagement') -> None:
    """
    Resolve a feeding engagement at hour-end.
    Dragon consumes its prey.
    """
    predator = engagement.initiator
    prey = engagement.target
    
    if not predator.is_alive:
        return
    if hasattr(prey, 'is_alive') and not prey.is_alive:
        # Prey already dead (maybe killed by something else)
        if hasattr(predator, 'think'):
            predator.think("My prey was already slain.")
        return
    
    # Kill the prey
    prey_name = getattr(prey, 'name', prey.__class__.__name__)
    prey.die(f"eaten by {getattr(predator, 'name', 'predator')}")
    
    if hasattr(predator, 'think'):
        predator.think("My hunger is sated.")


def resolve_tending(engagement: 'Engagement') -> None:
    """
    Resolve a tending engagement at hour-end.
    Dragon bestows blessing on a spirit.
    """
    tender = engagement.initiator
    spirit = engagement.target
    
    if not tender.is_alive:
        return
    if hasattr(spirit, 'is_alive') and not spirit.is_alive:
        return
    
    # Bestow blessing
    if not getattr(spirit, 'has_blessing', False):
        spirit.has_blessing = True
        if hasattr(tender, 'think'):
            tender.think("I bestow my blessing upon this spirit.")
    else:
        if hasattr(tender, 'think'):
            tender.think("This spirit already flourishes.")


def resolve_pillage(engagement: 'Engagement') -> None:
    """
    Resolve a pillaging engagement at hour-end.
    Pillager takes blessings from ruins, treasury, or domain.
    """
    pillager = engagement.initiator
    target = engagement.target
    
    if not pillager.is_alive:
        return
    
    # Determine max blessings pillager can carry
    max_carry = 3  # Default for heroes and bandits
    if hasattr(pillager, 'MAX_BLESSINGS'):
        max_carry = pillager.MAX_BLESSINGS
    
    current_blessings = getattr(pillager, 'blessings', 0)
    can_take = max_carry - current_blessings
    
    if can_take <= 0:
        if hasattr(pillager, 'think'):
            pillager.think("I cannot carry more blessings.")
        return
    
    taken = 0
    
    # Try to pillage from ruins (settlement ruins)
    if hasattr(target, 'pillage_ruins'):
        taken = target.pillage_ruins(can_take)
    # Try to pillage from domain/treasury
    elif hasattr(target, 'treasure') and target.treasure > 0:
        taken = min(can_take, target.treasure)
        target.treasure -= taken
    # Try to get blessings directly
    elif hasattr(target, 'blessings') and target.blessings > 0:
        taken = min(can_take, target.blessings)
        target.blessings -= taken
    
    if taken > 0:
        pillager.blessings = current_blessings + taken
        if hasattr(pillager, 'think'):
            pillager.think(f"I claimed {taken} blessing{'s' if taken > 1 else ''}!")
        
        # Track robbery for bandits
        if hasattr(pillager, 'days_since_robbery'):
            pillager.days_since_robbery = 0
    else:
        if hasattr(pillager, 'think'):
            pillager.think("Nothing of value remained.")