# tests for OxGame hit handling and board updates
import sys

from PyQt6.QtWidgets import QApplication

# Ensure a QApplication exists for Qt widgets
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

# Dummy components to inject into OxGame
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker
from typing import Any, Tuple, Dict

class DummyCameraManager(CameraManager):
    def get_frame(self) -> Any:
        # Return None to trigger placeholder handling
        return None

    def close_camera(self) -> None:
        pass


class DummyScreenManager(ScreenManager):
    def load_log(self) -> None:
        pass


class DummyBallTracker(BallTracker):
    def __init__(self, *args: Any, **kwargs: Any):
        # Bypass the original initializer
        self._hit = (100, 150, 0.5)  # default hit coordinates
        self._detection_info: Dict[str, Any] = {
            "detected": True,
            "max_area": 2500,
            "detected_position": (120, 130),
            "pixel_count": 12345,
            "contour_count": 3,
            "grid_position": (0, 0),
        }

    def check_target_hit(self, frame: Any) -> Tuple[int, int, float]:
        # Ignore frame, return preset hit
        return self._hit

    def get_detection_info(self, frame: Any) -> Dict[str, Any]:
        return self._detection_info


def test_process_hit_updates_board_and_switches_player():
    from frontend.ox_game import OxGame
    from typing import cast
    cam = DummyCameraManager()
    scr = DummyScreenManager()
    tracker = DummyBallTracker()

    # Cast to expected types to silence static type checkers
    game_widget = OxGame(cast(CameraManager, cam), cast(ScreenManager, scr), cast(BallTracker, tracker))

    # initial player should be 1
    assert game_widget.current_player == 1
    # process a hit at (100,150) -> grid cell (0,0)
    game_widget._process_hit((100, 150, 0.5))  # type: ignore[protected-access]

    # board should contain the mark for player 1 at (0,0)
    assert game_widget.game_logic.board.get((0, 0)) == 1
    # after processing, player should have switched to 2
    assert game_widget.current_player == 2


def test_victory_clears_board_and_resets_first_hit():
    from frontend.ox_game import OxGame
    from typing import cast
    cam = DummyCameraManager()
    scr = DummyScreenManager()
    tracker = DummyBallTracker()

    game_widget = OxGame(cast(CameraManager, cam), cast(ScreenManager, scr), cast(BallTracker, tracker))

    # Manually set up a winning condition for player 1
    game_widget.game_logic.board = {(0, 0): 1, (0, 1): 1}
    game_widget.current_player = 1
    # Hit that will fill the third cell in the top row -> x around 600 (>2*266)
    game_widget._process_hit((600, 150, 0.5))  # type: ignore[protected-access]

    # After victory, board should be cleared and first hit reset
    assert not game_widget.game_logic.board  # empty dict
    assert game_widget.first_hit_coord is None


def test_resume_tracking_resets_collision_flag():
    from frontend.ox_game import OxGame
    from typing import cast
    cam = DummyCameraManager()
    scr = DummyScreenManager()
    tracker = DummyBallTracker()

    game_widget = OxGame(cast(CameraManager, cam), cast(ScreenManager, scr), cast(BallTracker, tracker))

    # Simulate that a collision has been shown
    game_widget.collision_shown = True
    # Call resume_tracking which should reset the flag
    game_widget.resume_tracking()
    assert not game_widget.collision_shown
