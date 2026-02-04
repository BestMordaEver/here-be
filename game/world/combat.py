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
    from game.world import World
    from game.entities.base import Mobile, Engagement

from game.entities.base import EngagementType


# =============================================================================
# ENGAGEMENT INITIATION
# These functions create engagements. Resolution happens at hour-end.
# =============================================================================

def initiate_robbery(bandit, target, world: 'World') -> Optional['Engagement']:
    """
    Bandit initiates robbery on a caravan or settlement.
    Does NOT check for hero protection - that happens during the hour as an interrupt.
    
    Returns:
        The created engagement, or None if initiation failed
    """
    if not hasattr(bandit, 'engage'):
        return None
    
    engagement = bandit.engage(target, EngagementType.ROBBERY)
    
    if hasattr(bandit, 'think'):
        target_name = getattr(target, 'name', target.__class__.__name__)
        bandit.think(f"This {target_name} will make me rich.")
    
    return engagement


def initiate_combat(attacker, defender, world: 'World') -> Optional['Engagement']:
    """
    Initiate combat between two entities.
    Actual damage is dealt at resolution (on_hour_end).
    
    Returns:
        The created engagement, or None if initiation failed
    """
    if not hasattr(attacker, 'engage'):
        return None
    
    engagement = attacker.engage(defender, EngagementType.COMBAT)
    
    # Log the initiation
    attacker_type = attacker.__class__.__name__
    defender_type = defender.__class__.__name__
    
    if hasattr(attacker, 'think'):
        if attacker_type == 'Dragon':
            attacker.think("I descend upon my prey.")
        elif attacker_type == 'Hero':
            attacker.think("Steel yourself!")
        elif attacker_type == 'Bandit':
            attacker.think("Time to fight!")
    
    if hasattr(defender, 'think'):
        if defender_type == 'Hero':
            defender.think("An enemy approaches!")
        elif defender_type == 'Bandit':
            defender.think("I must defend myself!")
    
    return engagement


def initiate_protection(protector, protected, world: 'World') -> Optional['Engagement']:
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


def initiate_pillage(pillager, target, world: 'World') -> Optional['Engagement']:
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

def resolve_robbery(engagement: 'Engagement', world: 'World') -> None:
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
        _resolve_caravan_robbery(bandit, target, world)
    elif target_type in ('Village', 'City'):
        _resolve_settlement_robbery(bandit, target, world)


def _resolve_caravan_robbery(bandit, caravan, world: 'World') -> None:
    """Resolve bandit robbing caravan - steal blessing if any."""
    if not caravan.is_alive:
        return
    
    if caravan.blessing:
        if bandit.blessings < 3:  # MAX_BLESSINGS
            caravan.blessing = False
            bandit.blessings += 1
            bandit.days_since_robbery = 0
            if hasattr(bandit, 'think'):
                bandit.think("The blessing is mine!")
        else:
            # Blessing is lost - bandit can't carry more
            caravan.blessing = False
            if hasattr(bandit, 'think'):
                bandit.think("I cannot carry more, but they shan't have it.")
    else:
        if hasattr(bandit, 'think'):
            bandit.think("Nothing of value... a waste of time.")
    
    bandit.days_since_robbery = 0


def _resolve_settlement_robbery(bandit, settlement, world: 'World') -> None:
    """Resolve bandit raiding settlement - deal damage, no mourning."""
    if not settlement.is_alive:
        return
    
    settlement.hurt(1, 'bandit raid')
    bandit.days_since_robbery = 0
    
    if hasattr(bandit, 'think'):
        bandit.think("Easy pickings.")


def resolve_combat(engagement: 'Engagement', world: 'World') -> None:
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
        _resolve_dragon_combat(attacker, defender, defender_type, world)
    elif attacker_type == 'Bandit':
        _resolve_bandit_combat(attacker, defender, defender_type, world)
    elif attacker_type == 'Hero':
        _resolve_hero_combat(attacker, defender, defender_type, world)


def _resolve_dragon_combat(dragon, defender, defender_type: str, world: 'World') -> None:
    """Resolve dragon attacking something."""
    if defender_type == 'Caravan':
        dragon.think("The caravan is no more.")
        defender.die("dragon attack")
        
    elif defender_type == 'Bandit':
        dragon.think("Vermin crushed.")
        defender.die("dragon attack")
        
    elif defender_type == 'Hero':
        _resolve_dragon_vs_hero(dragon, defender, world)
        
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


def _resolve_dragon_vs_hero(dragon, hero, world: 'World') -> None:
    """Resolve dragon fighting a hero."""
    from game.entities.hero import HeroMood
    
    # Tired heroes outside settlements are killed
    if hero.mood == HeroMood.TIRED:
        # Check if hero is in a settlement
        in_settlement = False
        for entity in world.entities:
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


def _resolve_bandit_combat(bandit, defender, defender_type: str, world: 'World') -> None:
    """Resolve bandit fighting something."""
    if defender_type == 'Hero':
        from game.entities.hero import HeroMood
        # Bandit doesn't know hero's mood until now!
        if defender.mood == HeroMood.VENGEFUL:
            bandit.die("hero vengeance")
            defender.think("Justice served.")
        else:
            # Non-vengeful hero drives off bandit but doesn't kill
            if hasattr(bandit, 'think'):
                bandit.think("This one fights back! I retreat.")
            # Bandit disengages and flees (handled by flee logic elsewhere)


def _resolve_hero_combat(hero, defender, defender_type: str, world: 'World') -> None:
    """Resolve hero fighting something."""
    from game.entities.hero import HeroMood
    
    if defender_type == 'Dragon':
        if hero.party and len(hero.party) >= 4:  # PARTY_SIZE
            _party_attacks_dragon(hero.party, defender, world)
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


def _party_attacks_dragon(party: list, dragon, world: 'World') -> None:
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
    from game.entities.hero import HeroMood
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

def resolve_engagement(engagement: 'Engagement', world: 'World') -> None:
    """
    Resolve an engagement based on its type.
    Called at hour-end for any active engagement.
    """
    if engagement.engagement_type == EngagementType.COMBAT:
        resolve_combat(engagement, world)
    elif engagement.engagement_type == EngagementType.ROBBERY:
        resolve_robbery(engagement, world)
    elif engagement.engagement_type == EngagementType.FEEDING:
        resolve_feeding(engagement, world)
    elif engagement.engagement_type == EngagementType.TENDING:
        resolve_tending(engagement, world)
    elif engagement.engagement_type == EngagementType.PILLAGING:
        resolve_pillage(engagement, world)


def resolve_feeding(engagement: 'Engagement', world: 'World') -> None:
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


def resolve_tending(engagement: 'Engagement', world: 'World') -> None:
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


def resolve_pillage(engagement: 'Engagement', world: 'World') -> None:
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


# =============================================================================
# LEGACY COMPATIBILITY (will be removed once all entities use engagements)
# =============================================================================

def dragon_attacks_caravan(dragon, caravan, world: 'World') -> None:
    """Dragon destroys an unprotected caravan."""
    # Check if caravan is protected by a hero
    for entity in world.entities:
        if entity.__class__.__name__ == 'Hero' and entity.is_alive:
            if entity.get_distance(caravan.coordinates) <= 3:
                # Hero defends - combat shifts to hero
                dragon_attacks_hero(dragon, entity, world)
                return
    
    # Unprotected - caravan destroyed
    dragon.think("The caravan is no more.")
    caravan.die("dragon attack")


def dragon_attacks_bandit(dragon, bandit, world: 'World') -> None:
    """Dragon kills a bandit."""
    dragon.think("Vermin crushed.")
    bandit.die("dragon attack")


def dragon_attacks_settlement(dragon, settlement, world: 'World') -> None:
    """Dragon deals 1 damage to a settlement."""
    # Check for hero protection
    for entity in world.entities:
        if entity.__class__.__name__ == 'Hero' and entity.is_alive:
            if entity.get_distance(settlement.coordinates) <= 3:
                # Hero defends
                dragon_attacks_hero(dragon, entity, world)
                return
    
    # Unprotected - deal damage
    settlement.hurt(1, 'dragon attack')
    settlement.days_since_attack = 0  # Trigger mourning
    
    # Brute type reduces settlement to 1 HP
    if dragon.dragon_type == 'brute':
        if settlement.life > 1:
            settlement.hurt(settlement.life - 1, 'dragon crush')
    
    # Covetous dragons steal a blessing
    from game.entities.dragon import DragonMood
    if hasattr(dragon, 'mood') and dragon.mood == DragonMood.COVETOUS:
        if hasattr(settlement, 'blessings') and settlement.blessings > 0:
            settlement.blessings -= 1
            dragon.blessings += 1
            dragon.think("I claim their blessing as my own.")
            return
    
    dragon.think("The settlement burns.")


def dragon_attacks_hero(dragon, hero, world: 'World') -> None:
    """Dragon fights a hero."""
    _resolve_dragon_vs_hero(dragon, hero, world)


def dragon_attacks_camp(dragon, camp, world: 'World') -> None:
    """Dragon destroys a camp. Brute type destroys camps instantly."""
    if dragon.dragon_type == 'brute':
        camp.die("dragon")
        dragon.think("The camp is obliterated.")
    else:
        camp.hurt(1, 'dragon attack')
        dragon.think("The workers flee.")


def bandit_attacks_settlement(bandit, settlement, world: 'World') -> None:
    """Bandit deals 1 damage but doesn't trigger mourning."""
    # Check for hero protection
    for entity in world.entities:
        if entity.__class__.__name__ == 'Hero' and entity.is_alive:
            if entity.get_distance(settlement.coordinates) <= 3:
                # Vengeful hero kills bandit
                from game.entities.hero import HeroMood
                if entity.mood == HeroMood.VENGEFUL:
                    bandit.die("hero vengeance")
                    entity.think("Justice served.")
                    return
                # Other heroes drive off bandit
                return
    
    # Unprotected - deal damage but no mourning
    settlement.hurt(1, 'bandit raid')
    bandit.days_since_robbery = 0


def bandit_attacks_caravan(bandit, caravan, world: 'World') -> None:
    """Bandit ambushes caravan - steals blessing if any."""
    # Check for hero escort
    for entity in world.entities:
        if entity.__class__.__name__ == 'Hero' and entity.is_alive:
            if entity.get_distance(caravan.coordinates) <= 3:
                from game.entities.hero import HeroMood
                if entity.mood == HeroMood.VENGEFUL:
                    bandit.die("hero vengeance")
                    entity.think("This one won't prey on travelers again.")
                    return
                return
    
    # Steal blessing if caravan has one
    if caravan.blessing:
        if bandit.blessings < 3:  # MAX_BLESSINGS
            caravan.blessing = False
            bandit.blessings += 1
            bandit.days_since_robbery = 0
        else:
            # Blessing is lost
            caravan.blessing = False


def hero_attacks_dragon(hero, dragon, world: 'World') -> None:
    """Hero party attacks dragon."""
    if hero.party and len(hero.party) >= 4:  # PARTY_SIZE
        _party_attacks_dragon(hero.party, dragon, world)
    else:
        # Solo hero can't kill dragon, just becomes tired for the day
        from game.entities.hero import HeroMood
        if hero.mood != HeroMood.VENGEFUL:
            hero.tired_today = True
        hero.think("I cannot face this beast alone...")


def resolve_attack(attacker, defender, world: 'World') -> None:
    """
    LEGACY: Resolve an attack based on entity types.
    
    This function provides instant resolution for backwards compatibility.
    New code should use initiate_combat() + resolve at on_hour_end().
    """
    attacker_type = attacker.__class__.__name__
    defender_type = defender.__class__.__name__
    
    if attacker_type == 'Dragon':
        if defender_type == 'Caravan':
            dragon_attacks_caravan(attacker, defender, world)
        elif defender_type == 'Bandit':
            dragon_attacks_bandit(attacker, defender, world)
        elif defender_type == 'Hero':
            dragon_attacks_hero(attacker, defender, world)
        elif defender_type == 'Camp':
            dragon_attacks_camp(attacker, defender, world)
        elif defender_type in ('Village', 'City'):
            dragon_attacks_settlement(attacker, defender, world)
    
    elif attacker_type == 'Bandit':
        if defender_type == 'Caravan':
            bandit_attacks_caravan(attacker, defender, world)
        elif defender_type in ('Village', 'City'):
            bandit_attacks_settlement(attacker, defender, world)
    
    elif attacker_type == 'Hero':
        if defender_type == 'Dragon':
            hero_attacks_dragon(attacker, defender, world)
        elif defender_type == 'Bandit':
            # Vengeful heroes kill bandits
            from game.entities.hero import HeroMood
            if attacker.mood == HeroMood.VENGEFUL:
                defender.die("hero vengeance")
                attacker.think("One less scoundrel.")
