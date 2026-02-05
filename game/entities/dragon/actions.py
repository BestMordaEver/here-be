from typing import TYPE_CHECKING, Optional
from game.entities.base.scheduled import ScheduledAction, ActionType, EngagementType

if TYPE_CHECKING:
	from . import Dragon
	from game.entities.base import Mobile
	
TEND_RADIUS_DRUID = 8    # Druids tend all spirits in this radius

# Encounter radii
SCARE_RADIUS = 8         # Radius that scares bandits/cattle
PROTECTION_RADIUS = 10   # Radius for good dragons to protect humans
TERRITORIAL_RADIUS = 12  # Radius for territorial attacks

def execute_action_start(self: Dragon, action: ScheduledAction) -> None:
	"""Start executing a scheduled action."""
	if action.action_type == ActionType.TEND_HOARD:
		# Instant - generate blessing
		self.blessings += 1
		max_blessings = 10 if self.dragon_type == 'midas' else 5
		self.blessings = min(self.blessings, max_blessings)
		self.think("I tend to my hoard, feeling it grow.")
		self.complete_current_action()
		
	elif action.action_type == ActionType.FEED:
		# Find food based on diet and start moving toward it
		_start_feeding(self)
		
	elif action.action_type == ActionType.TEND_SPIRIT:
		if action.target:
			self.set_target_entity(action.target, self.world)
			self.current_target = action.target
			self.think(f"I shall visit the spirit.")
		else:
			self.complete_current_action()
			
	elif action.action_type == ActionType.ATTACK:
		if action.target and hasattr(action.target, 'coordinates'):
			# Circle settlements before attacking (unless already circled)
			target_class = action.target.__class__.__name__
			is_settlement = target_class in ('Village', 'City', 'Camp', 'Domain')
			already_circled = action.metadata.get('circled', False)
			
			if is_settlement and not already_circled:
				# Switch to circling first
				self.circle_target = action.target
				self.circle_angle = 0.0
				self.circle_steps_done = 0
				self._move_to_circle_position()
				self.current_action.action_type = ActionType.CIRCLE
				self.think("I circle my prey.")
			else:
				# Direct attack (mobile targets or already circled)
				self.set_target_entity(action.target, self.world)
				self.current_target = action.target
				self.think("Destruction awaits.")
		else:
			self.complete_current_action()
			
	elif action.action_type == ActionType.RETURN_HOME:
		if self.domain:
			self.set_destination(self.domain.coordinates, self.world)
			self.think("Time to return to my domain.")
		else:
			self.complete_current_action()
			
	elif action.action_type == ActionType.REST:
		self.think("I rest and gather my strength.")
		self.complete_current_action()
		
	elif action.action_type == ActionType.CIRCLE:
		if action.target and hasattr(action.target, 'coordinates'):
			self.circle_target = action.target
			self.circle_angle = 0.0
			self.circle_steps_done = 0
			self._move_to_circle_position()
			self.think("I circle my prey.")
		else:
			self.complete_current_action()

def check_for_encounters(self) -> Optional[Mobile]:
	"""Check for entities that trigger encounters."""
	nearby = self.get_nearby_entities(SCARE_RADIUS)
	
	for entity in nearby:
		# Bandits flee from dragons - including if they're engaged
		if entity.__class__.__name__ == 'Bandit' and entity.is_alive:
			return entity
		
		# Good dragons protect humans from threats
		if self.is_good:
			if entity.__class__.__name__ in ('Caravan', 'Hero'):
				# Check if they're being threatened (engaged by attacker)
				if hasattr(entity, 'current_engagement') and entity.current_engagement:
					engagement = entity.current_engagement
					if engagement.engagement_type in (EngagementType.ROBBERY, EngagementType.COMBAT):
						if engagement.initiator.is_alive:
							return engagement.initiator
				# Also check for nearby bandits
				for other in self.get_nearby_entities(PROTECTION_RADIUS):
					if other.__class__.__name__ == 'Bandit' and other.is_alive:
						return other
	
	# Territorial dragons attack nearby humans when near their domain
	if self.is_territorial and self.domain:
		if self.get_distance(self.domain.coordinates) <= TERRITORIAL_RADIUS:
			for entity in nearby:
				if entity.__class__.__name__ in ('Hero', 'Caravan', 'Bandit') and entity.is_alive:
					return entity
	
	# Evil dragons attack humans near spirits they are tending
	if self.is_evil and self.current_action:
		if self.current_action.action_type == ActionType.TEND_SPIRIT:
			for entity in nearby:
				if entity.__class__.__name__ in ('Hero', 'Caravan', 'Bandit') and entity.is_alive:
					return entity
	
	return None

def _start_feeding(self) -> None:
	"""Start feeding behavior based on diet."""
	if self.is_greed:
		# Greed dragons don't feed - tend hoard instead
		self.blessings += 1
		self.think("Gold is my sustenance.")
		self.complete_current_action()
		return
	
	# Find appropriate food
	target = None
	
	if self.is_carnivore:
		target = self._find_cattle()
	elif self.is_herbivore:
		target = self._find_grazing_spot()
	elif self.is_anthropophage:
		target = self._find_human_target()
	
	if target:
		if isinstance(target, tuple):
			self.set_destination(target, self.world)
		else:
			self.set_target_entity(target, self.world)
		self.current_target = target
		self.think("Hunger drives me.")
	else:
		self.think("No prey to be found.")
		self.complete_current_action()

def _on_movement_complete(self) -> None:
	"""Called when movement to target completes."""
	if not self.current_action:
		return
	
	action = self.current_action
	
	if action.action_type == ActionType.FEED:
		self._complete_feeding()
	elif action.action_type == ActionType.TEND_SPIRIT:
		self._complete_tending()
	elif action.action_type == ActionType.ATTACK:
		self._complete_attack()
	elif action.action_type == ActionType.RETURN_HOME:
		self.complete_current_action()

def _complete_feeding(self) -> None:
	"""
	Initiate feeding engagement with target. Resolution happens at hour-end.
	Herbivores just graze (instant), carnivores/anthropophages hunt (engagement).
	"""
	if self.current_target and hasattr(self.current_target, 'is_alive'):
		if self.current_target.is_alive:
			if self.is_carnivore or self.is_anthropophage:
				# Start feeding engagement - target might escape if interrupted
				self.engage(self.current_target, EngagementType.FEEDING, can_be_interrupted=False)
				self.think("Hunger drives me.")
				# Don't complete action - let on_hour_end handle resolution
				self.current_target = None
				return
			else:
				# Herbivore - instant grazing
				self.think("My hunger is sated.")
	
	self.complete_current_action()
	self.current_target = None

def _complete_tending(self) -> None:
	"""
	Complete tending a spirit. Uses engagement for single spirits.
	Druid type tends all spirits in range instantly (area effect).
	"""
	if self.dragon_type == 'druid':
		# Area tenders bless all spirits within radius - instant
		count = 0
		for entity in self.world.entities:
			if entity.__class__.__name__ == 'Spirit' and entity.is_alive:
				if self.get_distance(entity.coordinates) <= TEND_RADIUS_DRUID:
					if not getattr(entity, 'has_blessing', False):
						entity.has_blessing = True
						count += 1
		if count > 0:
			self.think(f"I bless {count} spirits with my presence.")
		else:
			self.think("The spirits here already flourish.")
		self.complete_current_action()
		self.current_target = None
	else:
		# Normal dragons create tending engagement with single spirit
		if self.current_target and self.current_target.__class__.__name__ == 'Spirit':
			self.engage(self.current_target, EngagementType.TENDING)
			self.think("I commune with the spirit.")
			# Don't complete action - let on_hour_end handle resolution
			self.current_target = None
		else:
			self.complete_current_action()
			self.current_target = None

def _complete_attack(self) -> None:
	"""
	Initiate combat engagement with target. Resolution happens at hour-end.
	Falls back to legacy instant resolution for non-engagement-aware targets.
	Blade dragons cannot be defended against (can_be_interrupted=False).
	"""
	from game.world.combat import initiate_combat, resolve_attack
	
	if self.current_target and hasattr(self.current_target, 'is_alive') and self.current_target.is_alive:
		target = self.current_target
		target_type = target.__class__.__name__
		
		# Blade dragons cannot be interrupted - heroes can't protect victims
		undefendable = (self.dragon_type == 'blade')
		
		# Use engagement system for entities that support it
		if target_type in ('Hero', 'Bandit', 'Caravan'):
			initiate_combat(self, target, can_be_interrupted=not undefendable)
			# Don't complete action - let on_hour_end handle resolution
			self.current_target = None
			return
		else:
			# Legacy instant resolution for settlements, camps, etc.
			resolve_attack(self, target)
	
	self.complete_current_action()
	self.current_target = None

def react_to_encounter(self, other: 'Mobile') -> Optional[ScheduledAction]:
	"""React to an encountered entity."""
	# Scare bandits away - interrupt their engagements
	if other.__class__.__name__ == 'Bandit':
		# Force bandit to disengage and flee
		if hasattr(other, 'is_engaged') and other.is_engaged():
			if hasattr(other, 'disengage'):
				other.disengage("A dragon! I must flee!")
		
		if not self.is_territorial and not self.is_evil:
			self.think("A bandit flees before me.")
			return None  # No action needed, bandit's encounter check will make it flee
	
	# Good dragons protect humans from bandits
	if self.is_good and other.__class__.__name__ == 'Bandit':
		from game.world.combat import initiate_combat
		undefendable = (self.dragon_type == 'blade')
		initiate_combat(self, other, can_be_interrupted=not undefendable)
		self.think("I shall protect the innocent.")
		return ScheduledAction(
			hour=self.world.time.current_hour,
			action_type=ActionType.ATTACK,
			target=other,
			priority=10,
			metadata={'circled': True}  # Skip circling for reactive attacks
		)
	
	# Territorial attack - when near domain
	if self.is_territorial and self.domain:
		if self.get_distance(self.domain.coordinates) <= TERRITORIAL_RADIUS:
			if other.__class__.__name__ in ('Hero', 'Caravan', 'Bandit'):
				from game.world.combat import initiate_combat
				undefendable = (self.dragon_type == 'blade')
				initiate_combat(self, other, can_be_interrupted=not undefendable)
				self.think("Intruders in my territory!")
				return ScheduledAction(
					hour=self.world.time.current_hour,
					action_type=ActionType.ATTACK,
					target=other,
					priority=10,
					metadata={'circled': True}
				)
	
	# Evil dragons attack humans near spirits they tend
	if self.is_evil and self.current_action:
		if self.current_action.action_type == ActionType.TEND_SPIRIT:
			if other.__class__.__name__ in ('Hero', 'Caravan', 'Bandit'):
				from game.world.combat import initiate_combat
				undefendable = (self.dragon_type == 'blade')
				initiate_combat(self, other, can_be_interrupted=not undefendable)
				self.think("You dare approach while I commune with the spirit?")
				return ScheduledAction(
					hour=self.world.time.current_hour,
					action_type=ActionType.ATTACK,
					target=other,
					priority=10,
					metadata={'circled': True}
				)
	
	return None