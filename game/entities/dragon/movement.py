from math import atan2, degrees, cos, sin, pi
from typing import TYPE_CHECKING

from game.entities.base.scheduled import ActionType
from .actions import on_movement_complete
from .types import DragonType

if TYPE_CHECKING:
	from . import Dragon

# Circling behavior
CIRCLE_RADIUS = 6        # Distance to circle around target
CIRCLE_STEPS = 8         # Number of steps to complete a circle (8 = octagon)

# SERPENT confusion
CONFUSE_RADIUS = 8       # Tiles within which SERPENT disorients nearby entities
ERRATIC_STEPS = 4        # Movement steps of erratic behavior for partially-exempt heroes

def _is_exempt_hero(hero) -> bool:
	"""Heroes on critical missions are partially exempt from SERPENT confusion."""
	if not hero.current_action:
		return False
	return hero.current_action.action_type in (
		ActionType.ESCORT,
		ActionType.PROTECT,
		ActionType.ATTACK,
	)


def _apply_confusion(dragon: 'Dragon') -> None:
	"""Disorient nearby non-dragon mobile entities.

	Fully confused entities wander randomly until the next hour.
	Heroes on critical missions (ESCORT/PROTECT/ATTACK) are partially exempt
	and receive a short burst of erratic movement instead.
	"""
	from game.entities.base.mobile import Mobile
	for entity in dragon.get_nearby_entities(CONFUSE_RADIUS):
		if entity.__class__.__name__ == 'Dragon':
			continue
		if not isinstance(entity, Mobile):
			continue
		if entity.is_engaged():
			continue
		if entity.__class__.__name__ == 'Hero' and _is_exempt_hero(entity):
			if entity.erratic_steps == 0:
				entity.erratic_steps = ERRATIC_STEPS
		else:
			entity.confused = True


def update_movement(dragon: 'Dragon') -> None:
	"""Process movement using Bresenham-style approach."""
	if dragon.current_action and dragon.current_action.action_type != ActionType.REST and not dragon.in_transit:
		_update_circling(dragon)
		return

	if not (dragon.in_transit and dragon.destination):
		return

	# Check diagonal debt (unless blade type ignores it)
	if dragon.dragon_type != DragonType.BLADE and dragon.should_skip_movement():
		return

	target_coords = dragon.destination
	
	dx_full = target_coords[0] - dragon.coordinates[0]
	dy_full = target_coords[1] - dragon.coordinates[1]
	
	if dx_full == 0 and dy_full == 0:
		return
	
	abs_dx = abs(dx_full)
	abs_dy = abs(dy_full)
	
	dx = 0
	dy = 0
	
	if abs_dx == 0:
		dy = 1 if dy_full > 0 else -1
	elif abs_dy == 0:
		dx = 1 if dx_full > 0 else -1
	else:
		ratio = abs_dy / abs_dx
		
		if abs_dx >= abs_dy:
			dx = 1 if dx_full > 0 else -1
			dragon.move_error += ratio
			if dragon.move_error >= 1.0:
				dy = 1 if dy_full > 0 else -1
				dragon.move_error -= 1.0
		else:
			dy = 1 if dy_full > 0 else -1
			dragon.move_error += 1.0 / ratio
			if dragon.move_error >= 1.0:
				dx = 1 if dx_full > 0 else -1
				dragon.move_error -= 1.0
	
	# Update rotation for visual
	if dx != 0 or dy != 0:
		heading = degrees(atan2(dy, dx))
		dragon.rotation = heading - dragon.base_rotation
	
	# Move (blade type ignores diagonal debt)
	dragon.move_to(
		(dragon.coordinates[0] + dx, dragon.coordinates[1] + dy),
		forego_debt=dragon.dragon_type == DragonType.BLADE
	)

	# SERPENT: confuse nearby entities while actively travelling
	if dragon.dragon_type == DragonType.SERPENT:
		_apply_confusion(dragon)

	# Check if arrived
	if dragon.coordinates == dragon.destination:
		dragon.in_transit = False
		on_movement_complete(dragon)

def _update_circling(dragon: 'Dragon') -> None:
	"""Update circling movement around target."""
	# Advance angle and move to next position
	if not dragon.destination:
		return
	
	dragon.circle_angle += (2 * pi) / CIRCLE_STEPS
	target_x, target_y = dragon.destination
	
	# Calculate position on circle
	# Serpents do figure-8 pattern, others do simple circle
	if dragon.dragon_type == DragonType.SERPENT:
		# Figure-8: use sin for x offset to create crossing pattern
		angle = dragon.circle_angle
		offset_x = CIRCLE_RADIUS * sin(2 * angle)
		offset_y = CIRCLE_RADIUS * sin(angle)
	else:
		# Simple circle
		offset_x = CIRCLE_RADIUS * cos(dragon.circle_angle)
		offset_y = CIRCLE_RADIUS * sin(dragon.circle_angle)
	
	dest_x = int(target_x + offset_x)
	dest_y = int(target_y + offset_y)
	
	# Clamp to world bounds
	dest_x = max(0, min(dragon.world.WIDTH - 1, dest_x))
	dest_y = max(0, min(dragon.world.HEIGHT - 1, dest_y))
	
	dragon.move_to((dest_x, dest_y), forego_debt=True)