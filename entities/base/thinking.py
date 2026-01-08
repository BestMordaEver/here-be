"""Thinking entity mixin - for entities that have thoughts."""
from typing import List


class Thinking:

    def __init__(self, intent: str = "idle"):
        self.thoughts: List[str] = []
        self.intent: str = intent

    def think(self, thought: str) -> None:
        self.thoughts.append(thought)
