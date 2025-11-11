import json
from pathlib import Path
from typing import Tuple, Dict, Any, Optional


class BackendCore:
    """
    Core backend functionality handling screen area and depth logs.
    All paths are relative to the provided base_path (project root or a temporary directory).
    """

    def __init__(self, base_path: str) -> None:
        """
        Initialize the core with a base path where log directories will be created.

        Args:
            base_path: Root directory for storing logs.
        """
        self.base_path = Path(base_path)
        # Ensure log directories exist
        (self.base_path / "ScreenAreaLogs").mkdir(parents=True, exist_ok=True)
        (self.base_path / "ScreenDepthLogs").mkdir(parents=True, exist_ok=True)

        # Internal state
        self._screen_area: Optional[Dict[str, Dict[str, int]]] = None
        self._screen_depth: Optional[float] = None

        # Load any existing data
        self.load_screen_area()
        self.load_screen_depth()

    def set_screen_area(self, top_left: Tuple[int, int], bottom_right: Tuple[int, int]) -> None:
        """
        Save screen area defined by top‑left and bottom‑right points.

        The data is stored as a JSON object:
        {
            "top_left": {"x": <int>, "y": <int>},
            "bottom_right": {"x": <int>, "y": <int>}
        }

        Args:
            top_left: (x, y) of the top‑left corner.
            bottom_right: (x, y) of the bottom‑right corner.
        """
        self._screen_area = {
            "top_left": {"x": top_left[0], "y": top_left[1]},
            "bottom_right": {"x": bottom_right[0], "y": bottom_right[1]},
        }
        area_path = self.base_path / "ScreenAreaLogs" / "area_log.json"
        with open(area_path, "w", encoding="utf-8") as f:
            json.dump(self._screen_area, f, ensure_ascii=False, indent=4)

    def get_screen_area(self) -> Optional[Dict[str, Dict[str, int]]]:
        """
        Return the stored screen area if available.

        Returns:
            A dictionary with "top_left" and "bottom_right" entries or None.
        """
        return self._screen_area

    def load_screen_area(self) -> None:
        """Load screen area from JSON file if it exists."""
        area_path = self.base_path / "ScreenAreaLogs" / "area_log.json"
        if area_path.is_file():
            try:
                with open(area_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Validate structure
                if (
                    isinstance(data, dict)
                    and "top_left" in data
                    and "bottom_right" in data
                    and isinstance(data["top_left"], dict)
                    and isinstance(data["bottom_right"], dict)
                ):
                    self._screen_area = data
                else:
                    self._screen_area = None
            except Exception:
                self._screen_area = None

    def set_screen_depth(self, depth: float) -> None:
        """
        Save the screen depth value.

        Args:
            depth: Depth measurement (float).
        """
        self._screen_depth = depth
        depth_path = self.base_path / "ScreenDepthLogs" / "depth_log.json"
        with open(depth_path, "w", encoding="utf-8") as f:
            json.dump({"depth": depth}, f, ensure_ascii=False, indent=4)

    def load_screen_depth(self) -> None:
        """Load screen depth from JSON file if it exists."""
        depth_path = self.base_path / "ScreenDepthLogs" / "depth_log.json"
        if depth_path.is_file():
            try:
                with open(depth_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "depth" in data:
                    self._screen_depth = float(data["depth"])
                else:
                    self._screen_depth = None
            except Exception:
                self._screen_depth = None

    def get_screen_depth(self) -> Optional[float]:
        """
        Return the stored screen depth.

        Returns:
            The depth value or None if not set.
        """
        return self._screen_depth
