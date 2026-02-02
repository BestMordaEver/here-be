"""Thinking entity mixin - for entities that have thoughts."""
from typing import List
import random

# Thinking constants
MAX_THOUGHTS = 20  # Maximum thoughts kept in history
THOUGHT_INTERVAL_HOURS_MIN = 2  # Minimum game hours between thoughts
THOUGHT_INTERVAL_HOURS_MAX = 6  # Maximum game hours between thoughts

# Thought templates for different intents/states
IDLE_THOUGHTS = [
    "The wind whispers through the grass...",
    "What lies beyond the horizon?",
    "A peaceful moment in troubled times.",
    "The sun feels warm today.",
    "I wonder what tomorrow will bring.",
]

ACTION_THOUGHTS = {
    "moving": [
        "Onward to {destination}.",
        "The road stretches ahead.",
        "Each step brings me closer.",
    ],
    "trading": [
        "Bartering for fair exchange.",
        "Commerce keeps us all alive.",
        "A good trade benefits both parties.",
    ],
    "fleeing": [
        "Must escape! Must survive!",
        "No time to look back!",
        "Danger behind, safety ahead!",
    ],
    "arrived": [
        "Finally, I have arrived.",
        "The journey is complete.",
        "This place will do.",
    ],
}

INTENT_THOUGHTS = {
    "settle": [
        "A new home awaits construction.",
        "This land will serve us well.",
    ],
    "trade": [
        "Goods to deliver, resources to collect.",
        "The economy depends on us.",
    ],
    "foraging": [
        "The grass here looks tasty.",
        "Where is the best grazing?",
    ],
}


class Thinking:

    def __init__(self, intent: str = "idle"):
        self.thoughts: List[str] = []
        self.intent: str = intent
        self._last_thought_hour: int = -999
        self._next_thought_interval: int = random.randint(THOUGHT_INTERVAL_HOURS_MIN, THOUGHT_INTERVAL_HOURS_MAX)

    def think(self, thought: str) -> None:
        """Add a thought to the entity's thought history."""
        self.thoughts.append(thought)
        # Keep only last N thoughts
        if len(self.thoughts) > MAX_THOUGHTS:
            self.thoughts.pop(0)
    
    def generate_thought(self) -> None:
        """Generate a thought based on current state and intent."""
        # Only think occasionally (based on game hours)

        current_time = self.world.time.get_current_time()
        total_hours = current_time.day * 24 + current_time.hour
        if total_hours - self._last_thought_hour < self._next_thought_interval:
            return
        self._last_thought_hour = total_hours
        self._next_thought_interval = random.randint(THOUGHT_INTERVAL_HOURS_MIN, THOUGHT_INTERVAL_HOURS_MAX)
        
        thought = None
        
        # Try action-based thought first (based on state)
        if hasattr(self, 'state') and self.state in ACTION_THOUGHTS:
            templates = ACTION_THOUGHTS[self.state]
            thought = random.choice(templates)
            # Format destination if available
            if hasattr(self, 'destination') and self.destination:
                dest_name = getattr(self.destination, 'name', str(self.destination))
                thought = thought.format(destination=dest_name)
        
        # Try intent-based thought
        elif self.intent != "idle":
            for intent_key, templates in INTENT_THOUGHTS.items():
                if intent_key in self.intent:
                    thought = random.choice(templates)
                    break
        
        # Fall back to idle thought
        if thought is None:
            thought = random.choice(IDLE_THOUGHTS)
        
        self.think(thought)
