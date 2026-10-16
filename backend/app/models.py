from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class Listing(BaseModel):
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
    relevanceScore: float = Field(..., description="Overall relevance score 0-100")
    budgetScore: Optional[float] = Field(None, description="Budget proximity score 0-100")
    recencyScore: float = Field(..., description="Recency score 0-100")
    statusMultiplier: float = Field(1.0, description="Status penalty multiplier (1.0 for active, 0.7 for pending)")
    isDuplicate: bool = Field(False, description="Whether this is a duplicate of another listing")
    duplicateGroupId: Optional[str] = Field(None, description="Cluster ID for duplicates")
    otherSources: List[str] = Field(default_factory=list, description="Other MLS sources for this same property")


class SearchParams(BaseModel):
    minPrice: Optional[float] = None
    maxPrice: Optional[float] = None
    minBedrooms: Optional[int] = None
    city: Optional[str] = None
    keyword: Optional[str] = None
    status: Optional[str] = "all"
    targetBudget: Optional[float] = None
    deduplicate: bool = False
    page: int = 1
    pageSize: int = 5

    @model_validator(mode="after")
    def validate_rules(self):
        if self.minPrice is not None and self.minPrice < 0:
            raise ValueError("minPrice cannot be negative")
        if self.maxPrice is not None and self.maxPrice < 0:
            raise ValueError("maxPrice cannot be negative")
        if self.minPrice is not None and self.maxPrice is not None and self.minPrice > self.maxPrice:
            raise ValueError(
                f"minPrice (${self.minPrice:,.0f}) cannot be greater than maxPrice (${self.maxPrice:,.0f})"
            )
        if self.minBedrooms is not None and self.minBedrooms < 0:
            raise ValueError("minBedrooms cannot be negative")
        if self.targetBudget is not None and self.targetBudget <= 0:
            raise ValueError("targetBudget must be greater than zero")
        if self.page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if self.pageSize < 1:
            raise ValueError("pageSize must be greater than or equal to 1")
        if self.status:
            normalized_status = self.status.strip().lower()
            if normalized_status not in ["all", "active", "pending", "sold"]:
                raise ValueError("status must be one of: all, active, pending, sold")
            self.status = normalized_status
        if self.pageSize > 100:
            raise ValueError("pageSize cannot exceed 100")
        return self


class SearchResponse(BaseModel):
    results: List[ScoredListing]
    total: int
    page: int
    pageSize: int
    totalPages: int
    deduplicatedCount: int = 0
