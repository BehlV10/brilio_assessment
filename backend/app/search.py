import math
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from app.models import Listing, ScoredListing, SearchParams


def normalize_address(address: str) -> str:
    """
    Normalizes an address string for entity resolution:
    - Lowercases & removes punctuation
    - Expands common street abbreviations
    - Normalizes unit/apartment designations
    """
    s = address.lower()
    s = re.sub(r"[,\.\#]", " ", s)
    
    # Expand street suffixes
    replacements = {
        r"\bst\b": "street",
        r"\bave\b": "avenue",
        r"\bct\b": "court",
        r"\brd\b": "road",
        r"\bln\b": "lane",
        r"\bdr\b": "drive",
        r"\bblvd\b": "boulevard",
        r"\bapt\b": "unit",
        r"\bste\b": "unit",
    }
    for pattern, repl in replacements.items():
        s = re.sub(pattern, repl, s)
        
    # Collapse multiple whitespaces
    s = " ".join(s.split())
    return s


def get_deduplication_key(listing: Listing) -> str:
    """
    Generates a canonical key to cluster duplicate listings.
    Uses rounded lat/long coordinates (within ~10m) and street number + root,
    ensuring robust matching across MLS feeds.
    """
    norm_addr = normalize_address(listing.address)
    # Extract leading numbers if any (e.g. "123")
    tokens = norm_addr.split()
    street_num = tokens[0] if tokens and tokens[0].isdigit() else ""
    # Use rounded lat/long (4 decimals ~ 11 meters)
    lat_r = round(listing.latitude, 4)
    lon_r = round(listing.longitude, 4)
    return f"{street_num}_{lat_r}_{lon_r}"


def filter_listings(listings: List[Listing], params: SearchParams) -> List[Listing]:
    """Filters listings based on minPrice, maxPrice, minBedrooms, city, and keyword."""
    filtered = []
    
    city_query = params.city.strip().lower() if params.city else None
    keyword_query = params.keyword.strip().lower() if params.keyword else None

    for item in listings:
        if params.minPrice is not None and item.price < params.minPrice:
            continue
        if params.maxPrice is not None and item.price > params.maxPrice:
            continue
        if params.minBedrooms is not None and item.bedrooms < params.minBedrooms:
            continue
        if city_query:
            # Case-insensitive match (exact or substring)
            if city_query not in item.city.strip().lower():
                continue
        if keyword_query:
            # Case-insensitive substring match in description
            if keyword_query not in item.description.lower():
                continue
                
        filtered.append(item)

    return filtered


def calculate_scores(
    listings: List[Listing],
    target_budget: Optional[float] = None,
    ref_date: Optional[date] = None,
) -> List[ScoredListing]:
    """
    Calculates relevance scores based on:
    1. Budget proximity (if target_budget provided)
    2. Recency decay (relative to ref_date or latest listing date)
    
    Formula:
      - Budget score: max(0.0, 1.0 - |price - targetBudget| / targetBudget) * 100
      - Recency score: (1.0 / (1.0 + daysAgo / 30.0)) * 100
      - Overall relevance:
          With target_budget: 0.6 * budget_score + 0.4 * recency_score
          Without target_budget: recency_score
    """
    if not listings:
        return []

    # Determine reference date for recency calculations
    if ref_date is None:
        dates = [
            datetime.strptime(item.listedDate, "%Y-%m-%d").date()
            for item in listings
        ]
        ref_date = max(dates)

    scored: List[ScoredListing] = []

    for item in listings:
        item_date = datetime.strptime(item.listedDate, "%Y-%m-%d").date()
        days_ago = max(0, (ref_date - item_date).days)
        
        # 30-day half-life decay
        recency_score_normalized = 1.0 / (1.0 + (days_ago / 30.0))
        recency_score = round(recency_score_normalized * 100.0, 1)

        budget_score = None
        if target_budget is not None and target_budget > 0:
            rel_diff = abs(item.price - target_budget) / target_budget
            # Exponential decay: listings with 0% deviation score 100.0; 
            # 10% deviation scores ~74.0, decaying gracefully.
            budget_score_normalized = math.exp(-3.0 * rel_diff)
            budget_score = round(budget_score_normalized * 100.0, 1)
            # Composite score: 70% budget match, 30% recency
            relevance = round((0.7 * budget_score) + (0.3 * recency_score), 1)
        else:
            relevance = recency_score

        scored.append(
            ScoredListing(
                **item.model_dump(),
                relevanceScore=relevance,
                budgetScore=budget_score,
                recencyScore=recency_score,
                isDuplicate=False,
                duplicateGroupId=get_deduplication_key(item),
                otherSources=[],
            )
        )

    # Deterministic sorting:
    # 1. Relevance score descending
    # 2. Listed date descending
    # 3. Price ascending
    # 4. ID ascending
    scored.sort(
        key=lambda x: (
            -x.relevanceScore,
            -datetime.strptime(x.listedDate, "%Y-%m-%d").toordinal(),
            x.price,
            x.id,
        )
    )

    return scored


def deduplicate_scored_listings(
    listings: List[ScoredListing],
) -> Tuple[List[ScoredListing], int]:
    """
    Clusters listings representing the same property across different MLS sources.
    Keeps the highest-ranked listing in each cluster and records other sources.
    """
    groups: Dict[str, List[ScoredListing]] = {}
    for item in listings:
        key = item.duplicateGroupId or get_deduplication_key(item)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    deduplicated: List[ScoredListing] = []
    removed_count = 0

    for cluster in groups.values():
        # The listings are already sorted by relevance score descending
        # Select best listing (prefer active status, then top score)
        best = cluster[0]
        # If best is pending and another is active, pick active
        active_candidates = [c for c in cluster if c.status.lower() == "active"]
        if active_candidates and best.status.lower() != "active":
            best = active_candidates[0]

        other_sources = [c.source for c in cluster if c.id != best.id or c.source != best.source]
        
        # Clone with other sources populated
        updated_best = best.model_copy(
            update={
                "isDuplicate": len(cluster) > 1,
                "otherSources": list(set(other_sources)),
            }
        )
        deduplicated.append(updated_best)
        removed_count += len(cluster) - 1

    # Preserve sorted order
    deduplicated.sort(
        key=lambda x: (
            -x.relevanceScore,
            -datetime.strptime(x.listedDate, "%Y-%m-%d").toordinal(),
            x.price,
            x.id,
        )
    )

    return deduplicated, removed_count


def paginate_listings(
    listings: List[ScoredListing], page: int, pageSize: int
) -> Tuple[List[ScoredListing], int, int]:
    """
    Returns (page_items, total_count, total_pages).
    """
    total = len(listings)
    total_pages = math.ceil(total / pageSize) if total > 0 else 0
    start = (page - 1) * pageSize
    end = start + pageSize

    if start >= total:
        return [], total, total_pages

    return listings[start:end], total, total_pages
