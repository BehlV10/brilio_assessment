import json
from pathlib import Path
from typing import List
from app.models import Listing

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_listings.json"


def load_listings(file_path: Path = DATA_PATH) -> List[Listing]:
    """Loads listings from JSON file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Listings file not found at: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Listing(**item) for item in data]
