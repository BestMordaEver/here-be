from .camp import Camp
from .village import Village
from .city import City
from .spire import Spire
from .settlement import Settlement

from .schedule import build_schedule
Village.build_schedule = build_schedule
City.build_schedule = build_schedule

from .actions import start_action, resolve_engagement
Village.start_action = start_action
City.start_action = start_action
Village.resolve_engagement = resolve_engagement
City.resolve_engagement = resolve_engagement
Camp.resolve_engagement = resolve_engagement

__all__ = ["Camp", "Village", "City", "Spire", "Settlement"]