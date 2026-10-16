export interface Listing {
  id: string;
  source: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  price: number;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  latitude: number;
  longitude: number;
  listedDate: string;
  status: string;
  description: string;
  relevanceScore: number;
  budgetScore: number | null;
  recencyScore: number;
  statusMultiplier?: number;
  isDuplicate: boolean;
  duplicateGroupId?: string | null;
  otherSources: string[];
}

export interface FilterState {
  minPrice: string;
  maxPrice: string;
  minBedrooms: string;
  city: string;
  keyword: string;
  status: string;
  targetBudget: string;
  deduplicate: boolean;
  pageSize: number;
}

export interface SearchResponse {
  results: Listing[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  deduplicatedCount: number;
}
