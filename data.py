"""Racer data persistence — JSON file storage."""

import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "racers.json"


def load() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"next_id": 1, "racers": []}


def save(store: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(store, f, indent=2)
