"""Named entity mixin - for entities that have personal names and pronouns."""
import random
from dataclasses import dataclass


@dataclass
class Pronouns:
    """Pronoun set for any named entity."""
    subject: str = "it"       # he/she/they/it
    object: str = "it"        # him/her/them/it
    possessive: str = "its"   # his/her/their/its

    SETS = {
        "he":    ("he",   "him",  "his"),
        "she":  ("she",  "her",  "her"),
        "they": ("they", "them", "their"),
        "it":      ("it",   "it",   "its"),
        "ze":      ("ze",   "hir",  "hirs"),
        "ae":      ("ae",   "aer",  "aers"),
    }

    @classmethod
    def from_string(cls, pronoun_str: str) -> "Pronouns":
        """Parse 'he/him/his' style string."""
        if not pronoun_str:
            return cls()
        parts = pronoun_str.split("/")
        if len(parts) >= 3:
            return cls(parts[0], parts[1], parts[2])
        return cls()

    @classmethod
    def random(cls) -> "Pronouns":
        """Return a random set."""
        # 80% for he/she (40% each), 20% for others (5% each)
        sets = list(cls.SETS.values())
        weights = [40, 40, 5, 5, 5, 5]  # he, she, they, it, ze, ae
        s, o, p = random.choices(sets, weights=weights, k=1)[0]
        return cls(s, o, p)

    def __repr__(self) -> str:
        return f"{self.subject}/{self.object}/{self.possessive}"


class Named:

    def __init__(self, name: str, pronouns: Pronouns | None = None):
        self.name = name
        self.pronouns: Pronouns = pronouns or Pronouns()
