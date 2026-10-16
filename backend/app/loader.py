import json
from pathlib import Path
from typing import List
from app.models import Listing

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_PATH = DATA_DIR / "sample_listings.json"
EXPANDED_PATH = DATA_DIR / "expanded_listings.json"


def load_listings(file_path: Path = None, use_expanded: bool = False) -> List[Listing]:
    """Loads listings from JSON file (sample or expanded)."""
    if file_path is None:
        file_path = EXPANDED_PATH if use_expanded else SAMPLE_PATH

    if not file_path.exists():
        raise FileNotFoundError(f"Listings file not found at: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Listing(**item) for item in data]
