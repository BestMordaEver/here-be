from .base import Coordinates, Mobile, Thinking, Mortal


class Bandit(Mortal, Mobile, Thinking):

    def __init__(
        self,
        coordinates: Coordinates,
    ):
        Mobile.__init__(self, "#960000", 'Ω', coordinates, 20)
        Thinking.__init__(self)
        self.loiter = 1
    
    def approach_target(self, world) -> None:
        pass
    
    def update(self, world) -> None:
        super().update(world)
