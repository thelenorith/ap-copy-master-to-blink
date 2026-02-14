"""
State file management for flexible flat frame matching.

The state file is a YAML mapping of blink directory path to cutoff date.
Flats from the cutoff date or later are considered valid candidates.
The cutoff advances when exact-match flats are used or when the user
selects a flat interactively.

State file format:
    "/data/RedCat51@f4.9+ASI2600MM/10_Blink": "2025-09-01"
"""

from pathlib import Path
from typing import Dict, Optional
import logging

import yaml

logger = logging.getLogger(__name__)


def load_state(state_path: Path) -> Dict[str, str]:
    """
    Load flat state from YAML file.

    Args:
        state_path: Path to state file

    Returns:
        Dictionary mapping blink directory path to cutoff date string.
        Returns empty dict if file does not exist.
    """
    if not state_path.exists():
        logger.debug(f"State file does not exist: {state_path}")
        return {}

    with open(state_path, "r") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}

    if not isinstance(data, dict):
        logger.warning(f"State file has unexpected format: {state_path}")
        return {}

    # Ensure all values are strings
    result = {}
    for key, value in data.items():
        result[str(key)] = str(value)

    logger.debug(f"Loaded state file with {len(result)} entries")
    return result


def save_state(state_path: Path, state: Dict[str, str]) -> None:
    """
    Save flat state to YAML file.

    Args:
        state_path: Path to state file
        state: Dictionary mapping blink directory path to cutoff date string
    """
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with open(state_path, "w") as f:
        yaml.dump(state, f, default_flow_style=False)

    logger.debug(f"Saved state file with {len(state)} entries")


def get_cutoff(state: Dict[str, str], blink_dir: str) -> Optional[str]:
    """
    Get the cutoff date for a blink directory.

    Args:
        state: State dictionary
        blink_dir: Blink directory path string

    Returns:
        Cutoff date string (YYYY-MM-DD), or None if no cutoff set
    """
    return state.get(blink_dir)


def update_cutoff(state: Dict[str, str], blink_dir: str, date: str) -> None:
    """
    Update the cutoff date for a blink directory.

    Only advances the cutoff (never moves it backward).

    Args:
        state: State dictionary (modified in place)
        blink_dir: Blink directory path string
        date: New cutoff date string (YYYY-MM-DD)
    """
    current = state.get(blink_dir)
    if current is None or date >= current:
        state[blink_dir] = date
        logger.debug(f"Updated cutoff for {blink_dir}: {current} -> {date}")
    else:
        logger.debug(
            f"Cutoff not advanced for {blink_dir}: " f"{date} < current {current}"
        )
