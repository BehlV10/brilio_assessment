import math
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from app.models import Listing, ScoredListing, SearchParams


# Precompiled regular expressions at module level for high-throughput string operations.
# Addresses from disparate MLS providers use inconsistent punctuation and abbreviations
# (e.g., "#4B", "Apt 4B", "Unit 4B", "St", "Street"). Precompiling avoids regex compilation inside loops.
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
    Normalizes a free-text street address for reliable cross-feed entity resolution:
    - Lowercases & normalizes punctuation.
    - Standardizes "#" into "unit " so "#4B" and "Unit 4B" resolve to the identical token.
    - Expands common road suffixes ('st' -> 'street', 'ct' -> 'court') and unit markers ('apt' -> 'unit').
    - Collapses multiple whitespace characters.
    """
    s = address.lower()
    s = RE_HASH.sub("unit ", s)
    s = RE_PUNCT.sub(" ", s)
    
    for pattern, repl in RE_EXPANSIONS:
        s = pattern.sub(repl, s)
        
    # Collapse extra whitespace into single spaces
    return " ".join(s.split())


def get_deduplication_key(listing: Listing) -> str:
    """
    Generates a canonical clustering key to detect duplicate listings across MLS providers.
    
    Combines:
    1. Street number or leading root token (e.g., "123")
    2. Unit/apartment token (e.g., "unit_4b") - CRITICAL for multi-unit condos:
       Prevents distinct units at the same building/GPS coordinates from colliding and being deleted.
    3. GPS coordinates rounded to 4 decimals (~11 meters):
       Tolerates minor GPS measurement discrepancies between syndication feeds.
    
    Examples:
    - '123 Main St, Apt 4B'  -> '123_unit_4b_38.7893_-77.1873' (Matches MLS_B '123 Main Street, Unit 4B')
    - '123 Main St, Apt 2A'  -> '123_unit_2a_38.7893_-77.1873' (Preserved as a distinct condo!)
    """
    norm_addr = normalize_address(listing.address)
    tokens = norm_addr.split()
    street_num = tokens[0] if tokens else ""
    
    # Extract unit / apartment identifier if present
    unit_match = RE_UNIT_EXTRACT.search(norm_addr)
    unit_part = f"unit_{unit_match.group(1)}" if unit_match else ""
    
    # 4 decimal places gives ~11m precision, ideal for parcel-level deduplication
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
    """
    Sorts listings based on user-requested order with deterministic multi-level tie-breaking.
    Tie-breaking ensures idempotent pagination (no duplicate items across page boundaries).
    
    Default 'relevance' cascade:
    1. relevanceScore (descending - highest match first)
    2. daysAgo (ascending - fresher listings win ties, faster than re-parsing dates)
    3. price (ascending - more affordable listing wins secondary tie)
    4. id (ascending - stable alphabetical tie-breaker)
    """
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
    Calculates relevance scores (0-100) combining:
    1. Budget Proximity Score: Exponential decay curve based on relative % deviation.
    2. Recency Score: 30-day half-life decay from the reference date.
    3. Status Multiplier: Penalizes pending (-30%) and sold (-70%) inventory.
    """
    if not listings:
        return []

    # Reference date for recency calculations.
    # Anchored to the latest listing date in the dataset (or current date in production)
    # to keep recency scores deterministic and independent of query filters.
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
        
        # 1. Recency Score (30-day half-life reciprocal decay: 100 at 0d, 50 at 30d, 33 at 60d)
        recency_score_normalized = 1.0 / (1.0 + (days_ago / 30.0))
        recency_score = round(recency_score_normalized * 100.0, 1)

        # 2. Budget Proximity Score (Exponential decay)
        # Using relative difference Delta = |price - budget| / budget:
        # - Delta = 0%  -> 100.0 score (exact match)
        # - Delta = 10% -> ~74.1 score
        # - Delta = 25% -> ~47.2 score
        # Exponential curve provides smooth, realistic decay similar to Elasticsearch decay scoring.
        budget_score = None
        if target_budget is not None and target_budget > 0:
            rel_diff = abs(item.price - target_budget) / target_budget
            budget_score_normalized = math.exp(-3.0 * rel_diff)
            budget_score = round(budget_score_normalized * 100.0, 1)
            # Composite base: 70% budget match (primary constraint), 30% recency (discovery booster)
            base_relevance = (0.7 * budget_score) + (0.3 * recency_score)
        else:
            # If no targetBudget provided, recency acts as the primary relevance signal
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
    Identifies and merges duplicate property listings across disparate MLS syndication feeds.
    
    Algorithm:
    1. Cluster listings into buckets sharing the identical deduplication key.
    2. For each cluster, elect the single best 'canonical' listing:
       - Priority 1: Status preference ('active' is favored over 'pending' or 'sold' contracts).
       - Priority 2: Highest relevance score / sort ranking.
    3. Annotate the canonical listing with 'isDuplicate=True' and list merged 'otherSources'.
    4. Re-sort the deduplicated set to preserve the user's requested sort order.
    
    Returns:
    - deduplicated list of ScoredListing
    - total count of removed duplicate feed entries
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
        # Select best listing: prefer active listings first, then highest score
        best = cluster[0]
        active_candidates = [c for c in cluster if c.status.lower() == "active"]
        if active_candidates and best.status.lower() != "active":
            best = active_candidates[0]

        # Record which other MLS feeds were syndicating this property
        other_sources = sorted(list({c.source for c in cluster if c.id != best.id}))
        
        updated_best = best.model_copy(
            update={
                "isDuplicate": len(cluster) > 1,
                "otherSources": other_sources,
            }
        )
        deduplicated.append(updated_best)
        removed_count += len(cluster) - 1

    # Preserve user's requested sort order across the deduplicated collection
    sort_scored_listings(deduplicated, sort_by=sort_by)
    return deduplicated, removed_count


def paginate_listings(
    listings: List[ScoredListing], page: int, pageSize: int
) -> Tuple[List[ScoredListing], int, int]:
    """
    Slices listings array into a 1-indexed page window.
    
    Returns:
    - page_results: sliced listings for the requested page
    - total: total number of matching listings
    - total_pages: ceiling of total / pageSize (0 if empty)
    """
    total = len(listings)
    total_pages = math.ceil(total / pageSize) if total > 0 else 0
    start = (page - 1) * pageSize
    end = start + pageSize

    # Handle out-of-bounds page requests gracefully (returns empty list without crashing)
    if start >= total:
        return [], total, total_pages

    return listings[start:end], total, total_pages
