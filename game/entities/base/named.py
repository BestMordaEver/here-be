"""Named entity mixin - for entities that have personal names."""
class Named:

    def __init__(self, name: str):
        self.name = name
