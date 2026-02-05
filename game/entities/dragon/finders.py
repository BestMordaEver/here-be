from typing import Any, List, Optional, TYPE_CHECKING
from random import choice, randint

from game.entities.base.entity import Coordinates

if TYPE_CHECKING:
	from . import Dragon
	from game.entities.spirit import Spirit

def _find_cattle(self: Dragon) -> Optional[Any]:
	"""Find cattle to hunt."""
	for entity in self.world.entities:
		if entity.__class__.__name__ == 'Cattle' and entity.is_alive:
			if self.get_distance(entity.coordinates) <= 50:
				return entity
	return None

def _find_grazing_spot(self: Dragon) -> Optional[Coordinates]:
	"""Find a plains tile to graze."""
	for _ in range(20):
		x = randint(0, self.world.WIDTH - 1)
		y = randint(0, self.world.HEIGHT - 1)
		if self.world.get_biome_from_height(self.world.height_map[y][x]) == 'field':
			return (x, y)
	return None

def _find_human_target(self: Dragon) -> Optional[Any]:
	"""Find a human entity to attack."""
	humans = []
	for entity in self.world.entities:
		if entity.__class__.__name__ in ('Hero', 'Bandit', 'Caravan'):
			if entity.is_alive:
				humans.append(entity)
	if humans:
		return choice(humans)
	return None

def _find_settlement_target(self: Dragon) -> Optional[Any]:
	"""Find a settlement to attack."""
	settlements = []
	for entity in self.world.entities:
		if entity.__class__.__name__ in ('Village', 'City', 'Camp'):
			if entity.is_alive:
				settlements.append(entity)
	if settlements:
		return choice(settlements)
	return None

def _find_settlement_with_blessing(self: Dragon) -> Optional[Any]:
	"""Find a settlement that has blessings to steal."""
	settlements = []
	for entity in self.world.entities:
		if entity.__class__.__name__ in ('Village', 'City'):
			if entity.is_alive and hasattr(entity, 'blessings') and entity.blessings > 0:
				settlements.append(entity)
	if settlements:
		return choice(settlements)
	return None

def _find_nearby_spirit(self: Dragon) -> Optional['Spirit']:
	"""Find a spirit near the domain."""
	if not self.domain:
		return None
	
	spirits = []
	for entity in self.world.entities:
		if entity.__class__.__name__ == 'Spirit' and entity.is_alive:
			dist = self.domain.get_distance(entity.coordinates)
			if dist <= 30:  # Within reasonable range
				spirits.append((dist, entity))
	
	if spirits:
		spirits.sort(key=lambda x: x[0])
		return spirits[0][1]
	return None

def _find_distant_spirits(self: Dragon, count: int = 2) -> List['Spirit']:
	"""Find distant spirits to visit."""
	if not self.domain:
		return []
	
	spirits = []
	for entity in self.world.entities:
		if entity.__class__.__name__ == 'Spirit' and entity.is_alive:
			dist = self.domain.get_distance(entity.coordinates)
			if dist > 30:  # Far from domain
				spirits.append((dist, entity))
	
	# Sort by distance, return furthest
	spirits.sort(key=lambda x: x[0], reverse=True)
	return [s[1] for s in spirits[:count]]