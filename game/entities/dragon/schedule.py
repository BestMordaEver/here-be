from typing import TYPE_CHECKING
from random import random
from game.entities.base.scheduled import ActionType
from . import finders

if TYPE_CHECKING:
	from . import Dragon

from enum import Enum

class DragonMood(Enum):
    """Dragon daily moods determining behavior."""
    DREARY = "dreary"       # Tends hoard, attacks if not good
    INSPIRED = "inspired"   # Tends hoard, travels to distant spirits
    PENSIVE = "pensive"     # Feeds once, tends nearby spirit
    HUNGRY = "hungry"       # Feeds twice, rests between (every 3 days)
    COVETOUS = "covetous"   # Attacks settlement, steals blessing


def build_schedule(self: Dragon) -> None:
	"""Build the day's schedule based on mood."""
	self.schedule = []
	self.current_action = None
	
	# Ensure domain exists
	if self.domain is None:
		self.create_domain(self.world)
	
	self.mood = _determine_mood(self)
	self.days_since_hungry += 1
	
	if self.mood == DragonMood.DREARY:
		_schedule_dreary(self)
	elif self.mood == DragonMood.INSPIRED:
		_schedule_inspired(self)
	elif self.mood == DragonMood.PENSIVE:
		_schedule_pensive(self)
	elif self.mood == DragonMood.HUNGRY:
		_schedule_hungry(self)
	elif self.mood == DragonMood.COVETOUS:
		_schedule_covetous(self)
	
	# Always end day by returning home
	self.add_scheduled_action(19, ActionType.RETURN_HOME, self.domain)
	
	self.think(f"Today I feel {self.mood.value}.")

def _determine_mood(self) -> DragonMood:
	"""Determine today's mood based on conditions."""
	# Hungry every 3 days (unless greed)
	if not self.is_greed and self.days_since_hungry >= 3:
		self.days_since_hungry = 0
		return DragonMood.HUNGRY
	
	# Greed dragons get covetous when they would be hungry
	if self.is_greed and self.days_since_hungry >= 3:
		self.days_since_hungry = 0
		if self.is_good:  # Good dragons become inspired instead
			return DragonMood.INSPIRED
		return DragonMood.COVETOUS
	
	# Covetous for evil dragons occasionally
	if self.is_evil and random() < 0.2:
		if not self.is_good:  # Good dragons become inspired instead
			return DragonMood.COVETOUS
		return DragonMood.INSPIRED
	
	# Random between dreary, inspired, pensive
	roll = random()
	if roll < 0.3:
		return DragonMood.DREARY
	elif roll < 0.6:
		return DragonMood.INSPIRED
	else:
		return DragonMood.PENSIVE

def _schedule_dreary(self: Dragon) -> None:
	"""Dreary: tend hoard, attack if not good."""
	actions = [(ActionType.TEND_HOARD, None)]
	if not self.is_good:
		target = finders._find_human_target(self)
		if target:
			actions.append((ActionType.ATTACK, target))
	if self.is_evil:
		settlement = finders._find_settlement_target(self)
		if settlement:
			actions.append((ActionType.ATTACK, settlement))
	self.schedule_actions(actions)

def _schedule_inspired(self: Dragon) -> None:
	"""Inspired: tend hoard, visit distant spirits."""
	actions = [(ActionType.TEND_HOARD, None)]
	spirits = finders._find_distant_spirits(self, count=2)
	for spirit in spirits:
		actions.append((ActionType.TEND_SPIRIT, spirit))
	self.schedule_actions(actions)

def _schedule_pensive(self: Dragon) -> None:
	"""Pensive: feed once, tend nearby spirit."""
	actions = [(ActionType.FEED, None)]
	spirit = finders._find_nearby_spirit(self)
	if spirit:
		actions.append((ActionType.TEND_SPIRIT, spirit))
	self.schedule_actions(actions)

def _schedule_hungry(self: Dragon) -> None:
	"""Hungry: feed, rest, feed again."""
	if self.is_anthropophage:
		# Anthropophage attacks a settlement to feed
		target = finders._find_settlement_target(self)
		if target:
			actions = [
				(ActionType.ATTACK, target),
				(ActionType.REST, None),
			]
		else:
			actions = [
				(ActionType.REST, None),
			]
	else:
		actions = [
			(ActionType.FEED, None),
			(ActionType.REST, None),
			(ActionType.FEED, None),
		]
	
	# Evil dragons replace rest with attack
	if self.is_evil:
		target = finders._find_human_target(self)
		if target:
			actions = [(ActionType.ATTACK, target) if a[0] == ActionType.REST else a for a in actions]
	
	self.schedule_actions(actions)

def _schedule_covetous(self: Dragon) -> None:
	"""Covetous: attack settlement, steal blessing."""
	settlement = finders._find_settlement_with_blessing(self)
	if not settlement:
		settlement = finders._find_settlement_target(self)
	if settlement:
		self.schedule_actions([(ActionType.ATTACK, settlement)])