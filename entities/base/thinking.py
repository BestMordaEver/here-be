"""Thinking entity mixin - for entities that have thoughts."""
from typing import List


class Thinking:

    def __init__(self):
        self.thoughts: List[str] = []

    def think(self, thought: str) -> None:
        self.thoughts.append(thought)
