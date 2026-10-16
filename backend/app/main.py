from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Request, status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.loader import load_listings
from app.models import Listing, SearchParams, SearchResponse
from app.search import (
    calculate_scores,
    deduplicate_scored_listings,
    filter_listings,
    paginate_listings,
)

from contextlib import asynccontextmanager

# In-memory stores of ingested listings
_sample_listings: List[Listing] = []
_expanded_listings: List[Listing] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _sample_listings, _expanded_listings
    _sample_listings = load_listings(use_expanded=False)
    _expanded_listings = load_listings(use_expanded=True)
    yield


app = FastAPI(
    title="Listing Search Service API",
    description="Full-stack real estate listing search service with relevance scoring and cross-MLS deduplication.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_listings(use_expanded: bool = False) -> List[Listing]:
    global _sample_listings, _expanded_listings
    if use_expanded:
        if not _expanded_listings:
            _expanded_listings = load_listings(use_expanded=True)
        return _expanded_listings
    else:
        if not _sample_listings:
            _sample_listings = load_listings(use_expanded=False)
        return _sample_listings


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Transforms Pydantic validation errors into clean, human-readable 400 responses.
    """
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid parameter")
        # Strip internal Pydantic prefixes if any
        if msg.startswith("Value error, "):
            msg = msg.replace("Value error, ", "")
        errors.append(f"{field}: {msg}")
    
    return JSONResponse(
        status_code=http_status.HTTP_400_BAD_REQUEST,
        content={"detail": "; ".join(errors)},
    )


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "totalListingsLoaded": len(get_listings()),
    }


@app.get("/api/listings/cities", response_model=List[str])
def list_cities(
    useExpanded: bool = Query(False, description="Whether to include cities from expanded dataset"),
):
    """Returns sorted unique cities available in the dataset."""
    listings = get_listings(use_expanded=useExpanded)
    cities = sorted(list({item.city for item in listings}))
    return cities


@app.get("/api/listings/search", response_model=SearchResponse)
def search_listings(
    minPrice: Optional[float] = Query(None, description="Minimum price filter"),
    maxPrice: Optional[float] = Query(None, description="Maximum price filter"),
    minBedrooms: Optional[int] = Query(None, description="Minimum bedrooms filter"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    keyword: Optional[str] = Query(None, description="Keyword search in description"),
    status: Optional[str] = Query("all", description="Filter by status: all, active, pending, sold"),
    targetBudget: Optional[float] = Query(None, description="User's target budget for relevance scoring"),
    deduplicate: bool = Query(False, description="Whether to deduplicate cross-MLS listings"),
    useExpanded: bool = Query(False, description="Whether to search the expanded synthetic dataset"),
    sortBy: Optional[str] = Query("relevance", description="Sort order: relevance, price_asc, price_desc, newest, sqft_desc"),
    page: int = Query(1, description="Page number (1-indexed)"),
    pageSize: int = Query(5, description="Number of results per page"),
):
    """
    Search and rank property listings.
    Supports filtering, target-budget and recency relevance scoring, deduplication, and pagination.
    """
    # Explicit domain validation using SearchParams
    try:
        params = SearchParams(
            minPrice=minPrice,
            maxPrice=maxPrice,
            minBedrooms=minBedrooms,
            city=city,
            keyword=keyword,
            status=status,
            targetBudget=targetBudget,
            deduplicate=deduplicate,
            useExpanded=useExpanded,
            sortBy=sortBy,
            page=page,
            pageSize=pageSize,
        )
    except (ValidationError, ValueError) as e:
        # Extract user-facing message
        if isinstance(e, ValidationError):
            msgs = [err.get("msg", str(err)).replace("Value error, ", "") for err in e.errors()]
            error_message = "; ".join(msgs)
        else:
            error_message = str(e)
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    listings = get_listings(use_expanded=params.useExpanded)

    # 1. Filtering
    filtered = filter_listings(listings, params)

    # 2. Relevance Scoring & Sorting
    scored = calculate_scores(filtered, target_budget=params.targetBudget, sort_by=params.sortBy)

    # 3. Deduplication (if requested)
    dedup_count = 0
    if params.deduplicate:
        scored, dedup_count = deduplicate_scored_listings(scored, sort_by=params.sortBy)

    # 4. Pagination
    page_results, total_count, total_pages = paginate_listings(
        scored, page=params.page, pageSize=params.pageSize
    )

    return SearchResponse(
        results=page_results,
        total=total_count,
        page=params.page,
        pageSize=params.pageSize,
        totalPages=total_pages,
        deduplicatedCount=dedup_count,
    )
