import json
import shutil
from pathlib import Path
from typing import Any, Dict, List


def _backup(file_path: Path) -> None:
    """Create a backup of the given file with a `_backup` suffix."""
    backup_path = file_path.with_name(f"{file_path.stem}_backup{file_path.suffix}")
    shutil.copy2(file_path, backup_path)


def _migrate_area_log(area_log_path: Path) -> None:
    """
    Migrate ``ScreenAreaLogs/area_log.json`` from the old dict format
    ``{"screen_area": [...], "screen_depth": ...}`` to the new list format
    ``[{"points": [...], "screen_depth": ...}]``.

    If the file is already a list, no action is taken.
    """
    if not area_log_path.is_file():
        return

    with open(area_log_path, "r", encoding="utf-8") as f:
        data: Any = json.load(f)

    # Already migrated?
    if isinstance(data, list):
        return

    # Backup original file before overwriting
    _backup(area_log_path)

    points = data.get("screen_area")
    depth = data.get("screen_depth")

    new_entry: Dict[str, Any] = {}
    if points is not None:
        new_entry["points"] = points
    if depth is not None:
        new_entry["screen_depth"] = depth

    migrated: List[Dict[str, Any]] = [new_entry] if new_entry else []

    with open(area_log_path, "w", encoding="utf-8") as f:
        json.dump(migrated, f, ensure_ascii=False, indent=4)


def _migrate_depth_log(depth_log_path: Path) -> None:
    """
    Migrate ``ScreenDepthLogs/depth_log.json`` from the old dict format
    ``{"screen_depth": ...}`` to the new list format ``[{"screen_depth": ...}]``.

    If the file is already a list, no action is taken.
    """
    if not depth_log_path.is_file():
        return

    with open(depth_log_path, "r", encoding="utf-8") as f:
        data: Any = json.load(f)

    # Already migrated?
    if isinstance(data, list):
        return

    # Backup original file before overwriting
    _backup(depth_log_path)

    depth = data.get("screen_depth")
    migrated: List[Dict[str, Any]] = [{"screen_depth": depth}] if depth is not None else []

    with open(depth_log_path, "w", encoding="utf-8") as f:
        json.dump(migrated, f, ensure_ascii=False, indent=4)


def main() -> None:
    """
    Entry point for the migration script.
    It resolves the project root (two levels up from this file) and migrates
    both area and depth logs if necessary.
    """
    # Resolve the project root directory (d:/VSCode/ttg)
    project_root = Path(__file__).resolve().parents[1]

    area_log_path = project_root / "ScreenAreaLogs" / "area_log.json"
    depth_log_path = project_root / "ScreenDepthLogs" / "depth_log.json"

    _migrate_area_log(area_log_path)
    _migrate_depth_log(depth_log_path)


if __name__ == "__main__":
    main()
