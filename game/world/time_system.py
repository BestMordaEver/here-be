"""Day/night cycle and time management for the game world."""
import time
from dataclasses import dataclass
from enum import Enum
from typing import List


class TimeOfDay(Enum):
    """Periods of the day."""
    DAWN = "dawn"       # 6:00 - entities wake, build schedules
    DAY = "day"         # 7:00-19:00 - active period
    DUSK = "dusk"       # 20:00 - entities return home
    NIGHT = "night"     # 21:00-5:00 - entities sleep


# Default hours for each period
DAWN_HOUR = 6
DAY_START_HOUR = 7
DUSK_HOUR = 20
NIGHT_HOUR = 21


@dataclass
class GameTime:
    """Represents a point in game time."""
    day: int
    hour: int  # 0-23

    def __str__(self) -> str:
        return f"Day {self.day}, {self.hour:02d}:00"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, GameTime):
            return False
        return self.day == other.day and self.hour == other.hour
    
    def __lt__(self, other: 'GameTime') -> bool:
        if self.day != other.day:
            return self.day < other.day
        return self.hour < other.hour
    
    def __le__(self, other: 'GameTime') -> bool:
        return self == other or self < other
    
    def hours_until(self, other: 'GameTime') -> int:
        """Calculate hours until another time."""
        day_diff = other.day - self.day
        hour_diff = other.hour - self.hour
        return day_diff * 24 + hour_diff
    
    def add_hours(self, hours: int) -> 'GameTime':
        """Return a new GameTime with hours added."""
        total_hours = self.hour + hours
        new_day = self.day + total_hours // 24
        new_hour = total_hours % 24
        return GameTime(new_day, new_hour)
    
    def get_period(self) -> TimeOfDay:
        """Get the current period of the day."""
        if self.hour == DAWN_HOUR:
            return TimeOfDay.DAWN
        elif DAY_START_HOUR <= self.hour < DUSK_HOUR:
            return TimeOfDay.DAY
        elif self.hour == DUSK_HOUR:
            return TimeOfDay.DUSK
        else:
            return TimeOfDay.NIGHT


class DayNightCycle:
    """Manages the game's day/night cycle and time progression."""
    
    def __init__(
        self,
        real_seconds_per_game_day: float = 86400.0,  # Default: 1 real day = 1 game day
        start_day: int = 1,
        start_hour: int = DAWN_HOUR,
    ):
        """
        Initialize the day/night cycle.
        
        Args:
            real_seconds_per_game_day: How many real seconds equal one game day.
                                       86400 = real-time, 120 = 2-minute days for testing
            start_day: Starting day number
            start_hour: Starting hour (0-23)
        """
        self.real_seconds_per_game_day = real_seconds_per_game_day
        self.real_seconds_per_game_hour = real_seconds_per_game_day / 24.0
        
        self._current_day = start_day
        self._current_hour = start_hour
        self._last_real_time = time.time()
        self._accumulated_time = 0.0
        
        # Track the last hour we processed (for detecting hour changes)
        self._last_processed_hour = start_hour
        self._last_processed_day = start_day
    
    @property
    def current_time(self) -> GameTime:
        """Get the current game time."""
        return GameTime(self._current_day, self._current_hour)
    
    @property
    def current_day(self) -> int:
        return self._current_day
    
    @property
    def current_hour(self) -> int:
        return self._current_hour
    
    def get_period(self) -> TimeOfDay:
        """Get the current time of day period."""
        return self.current_time.get_period()
    
    def update(self) -> List[GameTime]:
        """
        Update the time based on real elapsed time.
        
        Returns:
            List of GameTime objects representing each hour that passed
            (for triggering hourly events). Empty if no hour passed.
        """
        current_real_time = time.time()
        elapsed = current_real_time - self._last_real_time
        self._last_real_time = current_real_time
        
        self._accumulated_time += elapsed
        
        hours_passed = []
        
        # Process each hour that has passed
        while self._accumulated_time >= self.real_seconds_per_game_hour:
            self._accumulated_time -= self.real_seconds_per_game_hour
            self._advance_hour()
            hours_passed.append(GameTime(self._current_day, self._current_hour))
        
        return hours_passed
    
    def _advance_hour(self) -> None:
        """Advance the game time by one hour."""
        self._current_hour += 1
        if self._current_hour >= 24:
            self._current_hour = 0
            self._current_day += 1
    
    def skip_to_hour(self, target_hour: int) -> List[GameTime]:
        """
        Skip time forward to a specific hour (useful for debugging).
        If target_hour is earlier than current, skips to next day.
        
        Returns:
            List of GameTime objects for each hour skipped.
        """
        hours_passed = []
        
        while self._current_hour != target_hour:
            self._advance_hour()
            hours_passed.append(GameTime(self._current_day, self._current_hour))
        
        return hours_passed
    
    def set_speed(self, real_seconds_per_game_day: float) -> None:
        """Change the game speed."""
        self.real_seconds_per_game_day = real_seconds_per_game_day
        self.real_seconds_per_game_hour = real_seconds_per_game_day / 24.0
    
    def get_hours_until_dusk(self) -> int:
        """Get hours until next dusk."""
        if self._current_hour <= DUSK_HOUR:
            return DUSK_HOUR - self._current_hour
        else:
            return (24 - self._current_hour) + DUSK_HOUR
    
    def serialize(self) -> dict:
        """Serialize for saving/API."""
        return {
            "day": self._current_day,
            "hour": self._current_hour,
            "period": self.get_period().value,
            "speed": self.real_seconds_per_game_day,
        }
