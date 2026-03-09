"""Save/Load/Delete game functionality.

Save files are stored as JSON in the saves/ directory at project root.
Up to 10 save slots (save_0.json through save_9.json).
"""

import json
import os
from datetime import datetime
from src.settings import SAVES_PATH

# SAVES_PATH already resolves to the correct writable location for both
# development (project_root/saves/) and PyInstaller bundles (%APPDATA%/…).
SAVES_DIR = SAVES_PATH
AUTOSAVE_PATH = os.path.join(SAVES_PATH, "autosave.json")
MAX_SAVE_SLOTS = 10
MAX_SAVE_NAME_LENGTH = 20


def ensure_saves_dir():
    """Create the saves/ directory if it does not exist."""
    os.makedirs(SAVES_DIR, exist_ok=True)


def get_save_path(slot: int) -> str:
    """Return the file path for a given save slot."""
    return os.path.join(SAVES_DIR, f"save_{slot}.json")


def list_saves() -> list:
    """Return a list of 5 entries, each None (empty) or a summary dict.

    Summary dict keys: slot, name, hero_name, hero_id, level,
    stage_num, stage_type, gold, timestamp.
    """
    results = []
    for slot in range(MAX_SAVE_SLOTS):
        path = get_save_path(slot)
        if not os.path.exists(path):
            results.append(None)
            continue
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            results.append({
                "slot": slot,
                "name": data.get("name", f"Save {slot + 1}"),
                "hero_name": data.get("hero_name", "Unknown"),
                "hero_id": data.get("hero_id", ""),
                "level": data.get("level", 1),
                "stage_num": data.get("stage_num", 1),
                "stage_type": data.get("stage_type", "combat"),
                "gold": data.get("gold", 0),
                "timestamp": data.get("timestamp", ""),
            })
        except (json.JSONDecodeError, OSError, KeyError):
            results.append(None)
    return results


def save_game(slot: int, name: str, game_state: dict) -> bool:
    """Serialize the full game state to a JSON save file.

    game_state should contain all player and game fields needed
    for restoration.  Returns True on success.
    """
    ensure_saves_dir()
    game_state["name"] = name[:MAX_SAVE_NAME_LENGTH]
    game_state["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    game_state["version"] = 1
    path = get_save_path(slot)
    try:
        with open(path, 'w') as f:
            json.dump(game_state, f, indent=2)
        return True
    except OSError:
        return False


def load_save(slot: int) -> dict | None:
    """Read and return the full save dict, or None on error."""
    path = get_save_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def delete_save(slot: int) -> bool:
    """Delete a save file.  Returns True on success."""
    path = get_save_path(slot)
    try:
        if os.path.exists(path):
            os.remove(path)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Autosave (single file, written on exit-to-menu, loaded via Resume button)
# ---------------------------------------------------------------------------

def has_autosave() -> bool:
    """Return True if an autosave file exists."""
    return os.path.exists(AUTOSAVE_PATH)


def save_autosave(game_state: dict) -> bool:
    """Serialize game state to the autosave file (no slot index, no name prompt).

    Overwrites any existing autosave.  Returns True on success.
    """
    ensure_saves_dir()
    data = dict(game_state)
    data["name"] = "Autosave"
    data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["version"] = 1
    try:
        with open(AUTOSAVE_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except OSError:
        return False


def load_autosave() -> dict | None:
    """Read and return the autosave dict, or None if missing/corrupt."""
    if not os.path.exists(AUTOSAVE_PATH):
        return None
    try:
        with open(AUTOSAVE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def delete_autosave() -> bool:
    """Delete the autosave file.  Returns True on success."""
    try:
        if os.path.exists(AUTOSAVE_PATH):
            os.remove(AUTOSAVE_PATH)
        return True
    except OSError:
        return False
