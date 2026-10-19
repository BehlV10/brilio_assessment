import json
from pathlib import Path
from typing import List, Optional
from app.models import Listing

# Resolved data paths relative to package directory to ensure portability across environments
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_PATH = DATA_DIR / "sample_listings.json"
EXPANDED_PATH = DATA_DIR / "expanded_listings.json"


def load_listings(file_path: Optional[Path] = None, use_expanded: bool = False) -> List[Listing]:
    """
    Ingests and parses mock MLS listing datasets into typed Pydantic Listing objects.
    Supports switching between candidate handout dataset (12 listings) and synthetic expanded dataset (112 listings).
    """
    if file_path is None:
        file_path = EXPANDED_PATH if use_expanded else SAMPLE_PATH

    if not file_path.exists():
        raise FileNotFoundError(f"Listings file not found at: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Unpack JSON dictionaries into Pydantic models with schema validation
    return [Listing(**item) for item in data]
