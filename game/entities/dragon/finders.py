from typing import List, Optional, TYPE_CHECKING
from random import choice, randint

if TYPE_CHECKING:
	from . import Dragon
	from game.entities.base.entity import Coordinates
	from game.entities.cattle import Cattle
	from game.entities.bandit import Bandit
	from game.entities.caravan import Caravan
	from game.entities.hero import Hero
	from game.entities.spirit import Spirit
	from game.entities.settlement.settlement import Settlement

def find_cattle(dragon: Dragon) -> Optional[Cattle]:
	"""Find cattle to hunt."""
	for entity in dragon.world.entities:
		if entity.__class__.__name__ == 'Cattle' and entity.is_alive and not entity.current_engagement:
			if dragon.get_distance(entity.coordinates) <= 50:
				return entity
	return None

def find_grazing_spot(dragon: Dragon) -> Optional[Coordinates]:
	"""Find a plains tile to graze."""
	for _ in range(20):
		x = randint(0, dragon.world.WIDTH - 1)
		y = randint(0, dragon.world.HEIGHT - 1)
		if dragon.world.get_biome_from_height(dragon.world.height_map[y][x]) == 'field':
			return (x, y)
	return None

def find_human_target(dragon: Dragon) -> Optional['Hero | Bandit | Caravan']:
	"""Find a human entity to attack."""
	humans = []
	for entity in dragon.world.entities:
		if entity.__class__.__name__ in ('Hero', 'Bandit', 'Caravan'):
			if entity.is_alive:
				humans.append(entity)
	if humans:
		return choice(humans)
	return None

def find_settlement_target(dragon: Dragon) -> Optional['Settlement']:
	"""Find a settlement to attack."""
	settlements = []
	for entity in dragon.world.entities:
		if entity.__class__.__name__ in ('Village', 'City', 'Camp'):
			if entity.is_alive:
				settlements.append(entity)
	if settlements:
		return choice(settlements)
	return None

def find_settlement_with_blessing(dragon: Dragon) -> Optional['Settlement']:
	"""Find a settlement that has blessings to steal."""
	settlements = []
	for entity in dragon.world.entities:
		if entity.__class__.__name__ in ('Village', 'City', 'Camp'):
			if entity.is_alive and hasattr(entity, 'blessings') and entity.blessings > 0:
				settlements.append(entity)
	if settlements:
		return choice(settlements)
	return None

def find_spirits(
	dragon: Dragon,
	count: int = 1,
	distance_min: int = 1,
	distance_max: int = 20,
	has_blessing: Optional[bool] = None,
	spirit_types: Optional[List[str]] = None
) -> List['Spirit']:
	"""
	Find spirits matching criteria.
	
	Args:
		count: Max number of spirits to return
		distance_min: Minimum distance from domain (exclusive)
		distance_max: Maximum distance from domain (inclusive)
		has_blessing: None = don't care, True = must have, False = must not have
		spirit_types: Filter by type. None = any type.
	"""
	if not dragon.domain:
		return []
	
	spirits = []
	for entity in dragon.world.entities:
		if entity.__class__.__name__ == 'Spirit' and entity.is_alive and not entity.current_engagement:
			if spirit_types and entity.spirit_type not in spirit_types:
				continue
			if has_blessing is not None and entity.has_blessing != has_blessing:
				continue
			dist = dragon.domain.get_distance(entity.coordinates)
			if dist > distance_min and dist <= distance_max:
				spirits.append((dist, entity))
	
	spirits.sort(key=lambda x: x[0])
	return [s[1] for s in spirits[:count]]

__all__ = [
	"find_cattle",
	"find_grazing_spot",
	"find_human_target",
	"find_settlement_target",
	"find_settlement_with_blessing",
	"find_spirits",
]