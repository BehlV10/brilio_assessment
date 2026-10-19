from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class Listing(BaseModel):
    """Raw MLS listing ingested from provider syndication feeds."""
    id: str
    source: str
    address: str
    city: str
    state: str
    zip: str
    price: float
    bedrooms: int
    bathrooms: float
    sqft: int
    latitude: float
    longitude: float
    listedDate: str
    status: str
    description: str


class ScoredListing(Listing):
    """Enriched listing annotated with calculated relevance metrics, status adjustments, and deduplication info."""
    relevanceScore: float = Field(..., description="Overall relevance score 0-100")
    budgetScore: Optional[float] = Field(None, description="Budget proximity score 0-100")
    recencyScore: float = Field(..., description="Recency score 0-100")
    statusMultiplier: float = Field(1.0, description="Status penalty multiplier (1.0 for active, 0.7 for pending, 0.3 for sold)")
    pricePerSqft: Optional[int] = Field(None, description="Calculated price per square foot")
    daysAgo: Optional[int] = Field(None, description="Days since listed date relative to market reference")
    isDuplicate: bool = Field(False, description="Whether this property was detected on multiple MLS feeds")
    duplicateGroupId: Optional[str] = Field(None, description="Canonical clustering key used for deduplication")
    otherSources: List[str] = Field(default_factory=list, description="Other MLS feeds where this duplicate property was found")


class SearchParams(BaseModel):
    """
    Validates user search parameters.
    Handout Requirement: 'Handle invalid input deliberately rather than incidentally — 
    a clear error response beats a crash, a silent empty result, or wrong data.'
    """
    minPrice: Optional[float] = None
    maxPrice: Optional[float] = None
    minBedrooms: Optional[int] = None
    city: Optional[str] = None
    keyword: Optional[str] = None
    status: Optional[str] = "all"
    targetBudget: Optional[float] = None
    deduplicate: bool = False
    useExpanded: bool = False
    sortBy: Optional[str] = "relevance"
    page: int = 1
    pageSize: int = 5

    @model_validator(mode="after")
    def validate_rules(self):
        # 1. Non-negative price constraints
        if self.minPrice is not None and self.minPrice < 0:
            raise ValueError("minPrice cannot be negative")
        if self.maxPrice is not None and self.maxPrice < 0:
            raise ValueError("maxPrice cannot be negative")
            
        # 2. Price range order constraint with human-friendly formatted error
        if self.minPrice is not None and self.maxPrice is not None and self.minPrice > self.maxPrice:
            raise ValueError(
                f"minPrice (${self.minPrice:,.0f}) cannot be greater than maxPrice (${self.maxPrice:,.0f})"
            )
            
        # 3. Bedroom constraint
        if self.minBedrooms is not None and self.minBedrooms < 0:
            raise ValueError("minBedrooms cannot be negative")
            
        # 4. Budget constraint (must be positive if specified)
        if self.targetBudget is not None and self.targetBudget <= 0:
            raise ValueError("targetBudget must be greater than zero")
            
        # 5. Pagination boundary constraints (1-indexed pages, upper limit to prevent memory exhaustion)
        if self.page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if self.pageSize < 1:
            raise ValueError("pageSize must be greater than or equal to 1")
        if self.pageSize > 100:
            raise ValueError("pageSize cannot exceed 100")
            
        # 6. Status enumeration validation and canonical lowercasing
        if self.status:
            normalized_status = self.status.strip().lower()
            if normalized_status not in ["all", "active", "pending", "sold"]:
                raise ValueError("status must be one of: all, active, pending, sold")
            self.status = normalized_status
            
        # 7. Sort order enumeration validation
        if self.sortBy:
            normalized_sort = self.sortBy.strip().lower()
            if normalized_sort not in ["relevance", "price_asc", "price_desc", "newest", "sqft_desc"]:
                raise ValueError("sortBy must be one of: relevance, price_asc, price_desc, newest, sqft_desc")
            self.sortBy = normalized_sort
            
        return self


class SearchResponse(BaseModel):
    """Standardized REST API response format with paginated results and search summary."""
    results: List[ScoredListing]
    total: int
    page: int
    pageSize: int
    totalPages: int
    deduplicatedCount: int = 0
