# external_api.py
"""
External API module to expose BallTracker functionality to other components.
"""

from typing import Optional, Tuple
from backend.ball_tracker import BallTracker

# Global reference to BallTracker instance; set via set_ball_tracker
_ball_tracker: Optional[BallTracker] = None

def set_ball_tracker(ball_tracker: BallTracker) -> None:
    """
    Register the BallTracker instance for external access.

    Args:
        ball_tracker: Instance of BallTracker to be stored globally.
    """
    global _ball_tracker
    _ball_tracker = ball_tracker

def get_target_position() -> Optional[Tuple[int, int, float]]:
    """
    Retrieve the latest hit coordinate and depth from the registered BallTracker.

    Returns:
        Tuple[int, int, float] if a hit has been detected,
        otherwise None.
    """
    if _ball_tracker is None:
        return None
    try:
        # BallTracker provides get_last_reached_coord()
        return _ball_tracker.get_last_reached_coord()
    except Exception as e:
        print(f"external_api error: {e}")
        return None
