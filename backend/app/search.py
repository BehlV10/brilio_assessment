import math
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from app.models import Listing, ScoredListing, SearchParams


RE_PUNCT = re.compile(r"[,\.]")
RE_HASH = re.compile(r"\#\s*")
RE_UNIT_EXTRACT = re.compile(r"\bunit\s+([a-z0-9\-]+)\b")
RE_EXPANSIONS = [
    (re.compile(r"\bst\b"), "street"),
    (re.compile(r"\bave\b"), "avenue"),
    (re.compile(r"\bct\b"), "court"),
    (re.compile(r"\brd\b"), "road"),
    (re.compile(r"\bln\b"), "lane"),
    (re.compile(r"\bdr\b"), "drive"),
    (re.compile(r"\bblvd\b"), "boulevard"),
    (re.compile(r"\bapt\b"), "unit"),
    (re.compile(r"\bste\b"), "unit"),
    (re.compile(r"\bapartment\b"), "unit"),
    (re.compile(r"\bsuite\b"), "unit"),
]


def normalize_address(address: str) -> str:
    """
    Normalizes an address string for entity resolution:
    - Lowercases & normalizes punctuation
    - Replaces '#' with 'unit '
    - Expands common street abbreviations
    - Normalizes unit/apartment designations to 'unit'
    """
    s = address.lower()
    s = RE_HASH.sub("unit ", s)
    s = RE_PUNCT.sub(" ", s)
    
    for pattern, repl in RE_EXPANSIONS:
        s = pattern.sub(repl, s)
        
    # Collapse multiple whitespaces
    return " ".join(s.split())


def get_deduplication_key(listing: Listing) -> str:
    """
    Generates a canonical key to cluster duplicate listings across feeds.
    Combines:
    1. Street number or leading token
    2. Unit/apartment designator (e.g. 'unit_4b') to protect distinct condos in the same building
    3. Rounded lat/long coordinates (4 decimals ~ 11 meters)
    """
    norm_addr = normalize_address(listing.address)
    tokens = norm_addr.split()
    street_num = tokens[0] if tokens else ""
    
    # Check for unit / apt designation (e.g. "unit 4b")
    unit_match = RE_UNIT_EXTRACT.search(norm_addr)
    unit_part = f"unit_{unit_match.group(1)}" if unit_match else ""
    
    lat_r = round(listing.latitude, 4)
    lon_r = round(listing.longitude, 4)
    
    if unit_part:
        return f"{street_num}_{unit_part}_{lat_r}_{lon_r}"
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
        if params.status and params.status != "all":
            if item.status.strip().lower() != params.status.strip().lower():
                continue
        if city_query:
            # Case-insensitive match (exact or substring)
            if city_query not in item.city.strip().lower():
                continue
        if keyword_query:
            # Case-insensitive substring match in description OR address
            in_desc = keyword_query in item.description.lower()
            in_addr = keyword_query in item.address.lower()
            if not in_desc and not in_addr:
                continue
                
        filtered.append(item)

    return filtered


def sort_scored_listings(listings: List[ScoredListing], sort_by: str = "relevance") -> List[ScoredListing]:
    """Sorts listings based on the specified sort order with deterministic tie-breaking."""
    sb = (sort_by or "relevance").lower()
    if sb == "price_asc":
        listings.sort(key=lambda x: (x.price, -x.relevanceScore, x.id))
    elif sb == "price_desc":
        listings.sort(key=lambda x: (-x.price, -x.relevanceScore, x.id))
    elif sb == "newest":
        listings.sort(key=lambda x: (x.daysAgo, -x.relevanceScore, x.id))
    elif sb == "sqft_desc":
        listings.sort(key=lambda x: (-x.sqft, x.price, x.id))
    else:  # "relevance"
        listings.sort(
            key=lambda x: (
                -x.relevanceScore,
                x.daysAgo,
                x.price,
                x.id,
            )
        )
    return listings


def calculate_scores(
    listings: List[Listing],
    target_budget: Optional[float] = None,
    ref_date: Optional[date] = None,
    sort_by: str = "relevance",
) -> List[ScoredListing]:
    """
    Calculates relevance scores based on:
    1. Budget proximity (if target_budget provided)
    2. Recency decay (relative to ref_date or latest listing date)
    3. Status multiplier: 1.0 for active, 0.7 for pending (30% discount), 0.3 for sold
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
            # Composite base score: 70% budget match, 30% recency
            base_relevance = (0.7 * budget_score) + (0.3 * recency_score)
        else:
            base_relevance = recency_score

        # Status penalty multiplier:
        # Active listings are actionable (1.0).
        # Pending listings (under contract) receive a 30% relevance penalty (0.7).
        # Sold listings receive a 70% relevance penalty (0.3).
        status_norm = item.status.strip().lower()
        if status_norm == "pending":
            status_multiplier = 0.7
        elif status_norm == "sold":
            status_multiplier = 0.3
        else:
            status_multiplier = 1.0

        relevance = round(base_relevance * status_multiplier, 1)
        price_per_sqft = round(item.price / item.sqft) if item.sqft > 0 else None

        scored.append(
            ScoredListing(
                **item.model_dump(),
                relevanceScore=relevance,
                budgetScore=budget_score,
                recencyScore=recency_score,
                statusMultiplier=status_multiplier,
                pricePerSqft=price_per_sqft,
                daysAgo=days_ago,
                isDuplicate=False,
                duplicateGroupId=get_deduplication_key(item),
                otherSources=[],
            )
        )

    # Sort based on requested sort order
    sort_scored_listings(scored, sort_by=sort_by)
    return scored


def deduplicate_scored_listings(
    listings: List[ScoredListing],
    sort_by: str = "relevance",
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
        # Select best listing (prefer active status, then top score)
        best = cluster[0]
        active_candidates = [c for c in cluster if c.status.lower() == "active"]
        if active_candidates and best.status.lower() != "active":
            best = active_candidates[0]

        other_sources = sorted(list({c.source for c in cluster if c.id != best.id}))
        
        updated_best = best.model_copy(
            update={
                "isDuplicate": len(cluster) > 1,
                "otherSources": other_sources,
            }
        )
        deduplicated.append(updated_best)
        removed_count += len(cluster) - 1

    # Preserve requested sort order
    sort_scored_listings(deduplicated, sort_by=sort_by)
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
