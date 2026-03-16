from enum import Enum

class SettlementEvent(Enum):
    """Daily settlement events."""
    NONE = "none"           # Normal day - may send caravans, spawn heroes
    MOURNING = "mourning"   # After dragon attack - no caravans
    MARKET_DAY = "market_day"  # Every 5 days - attracts heroes, trading
    REPAIRS = "repairs"     # After market day if damaged - restore HP
    CELEBRATION = "celebration"  # After collecting a blessing - similar to market day