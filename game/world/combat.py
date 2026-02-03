"""Combat resolution for entity encounters."""
from typing import TYPE_CHECKING, Optional
from random import choice

if TYPE_CHECKING:
    from game.world import World
    from game.entities.base import Mobile


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


def resolve_attack(attacker, defender, world: 'World') -> None:
    """Resolve an attack based on entity types."""
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
