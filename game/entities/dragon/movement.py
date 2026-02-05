from math import atan2, degrees, cos, sin
from typing import TYPE_CHECKING

from game.entities.base.scheduled import ActionType, ScheduledAction

if TYPE_CHECKING:
	from . import Dragon

# Circling behavior
CIRCLE_RADIUS = 6        # Distance to circle around target
CIRCLE_STEPS = 8         # Number of steps to complete a circle (8 = octagon)

def update_movement(self: Dragon) -> None:
	"""Process movement using Bresenham-style approach."""
	# Handle circling movement separately
	if self.current_action and self.current_action.action_type == ActionType.CIRCLE:
		_update_circling(self)
		return
	
	if self.state != "moving" or not self.destination:
		return

	# Check diagonal debt (unless blade type ignores it)
	if self.dragon_type != 'blade' and self.should_skip_movement():
		return

	target_coords = self.destination
	
	dx_full = target_coords[0] - self.coordinates[0]
	dy_full = target_coords[1] - self.coordinates[1]
	
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
			self.move_error += ratio
			if self.move_error >= 1.0:
				dy = 1 if dy_full > 0 else -1
				self.move_error -= 1.0
		else:
			dy = 1 if dy_full > 0 else -1
			self.move_error += 1.0 / ratio
			if self.move_error >= 1.0:
				dx = 1 if dx_full > 0 else -1
				self.move_error -= 1.0
	
	# Update rotation for visual
	if dx != 0 or dy != 0:
		heading = degrees(atan2(dy, dx))
		self.rotation = heading - self.base_rotation
	
	# Move (blade type ignores diagonal debt)
	self.move_to(
		(self.coordinates[0] + dx, self.coordinates[1] + dy),
		forego_debt=self.dragon_type == 'blade'
	)
	
	# Check if arrived
	if self.coordinates == self.destination:
		self.state = "arrived"
		self._on_movement_complete()

def _update_circling(self: Dragon) -> None:
	"""Update circling movement around target."""
	from math import pi
	
	if not self.circle_target:
		self.complete_current_action()
		return
	
	# Check if target is still alive
	if hasattr(self.circle_target, 'is_alive') and not self.circle_target.is_alive:
		self.circle_target = None
		self.complete_current_action()
		return
	
	# If we're still moving to a circle position, continue
	if self.state == "moving" and self.destination:
		if self.dragon_type != 'blade' and self.should_skip_movement():
			return
		self._bresenham_move()
		if self.coordinates == self.destination:
			self.state = "arrived"
	
	# If arrived at circle position, move to next
	if self.state == "arrived" or self.state == "created":
		self.circle_steps_done += 1
	
		# Advance angle and move to next position
		self.circle_angle += (2 * pi) / CIRCLE_STEPS
		_move_to_circle_position(self)

def _complete_circling(self: Dragon) -> None:
	"""Complete circling and transition to attack."""
	target = self.circle_target
	self.circle_target = None
	self.circle_steps_done = 0
	self.circle_angle = 0.0
	
	self.complete_current_action()
	
	# Automatically start attack on the circled target
	if target and hasattr(target, 'is_alive') and target.is_alive:
		attack_action = ScheduledAction(
			hour=self.world.time.current_hour,
			action_type=ActionType.ATTACK,
			target=target,
			priority=10,
			metadata={'circled': True}  # Mark as already circled
		)
		self.start_action(attack_action)
		self._execute_action_start(attack_action)

def _move_to_circle_position(self: Dragon) -> None:
	"""Calculate and move to the next position on the circle around target."""
	if not self.circle_target or not hasattr(self.circle_target, 'coordinates'):
		return
	
	target_x, target_y = self.circle_target.coordinates
	
	# Calculate position on circle
	# Serpents do figure-8 pattern, others do simple circle
	if self.dragon_type == 'serpent':
		# Figure-8: use sin for x offset to create crossing pattern
		angle = self.circle_angle
		offset_x = CIRCLE_RADIUS * sin(2 * angle)
		offset_y = CIRCLE_RADIUS * sin(angle)
	else:
		# Simple circle
		offset_x = CIRCLE_RADIUS * cos(self.circle_angle)
		offset_y = CIRCLE_RADIUS * sin(self.circle_angle)
	
	dest_x = int(target_x + offset_x)
	dest_y = int(target_y + offset_y)
	
	# Clamp to world bounds
	dest_x = max(0, min(self.world.WIDTH - 1, dest_x))
	dest_y = max(0, min(self.world.HEIGHT - 1, dest_y))
	
	self.set_destination((dest_x, dest_y), self.world)