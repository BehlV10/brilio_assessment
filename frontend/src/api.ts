import { FilterState, SearchResponse } from './types';

export async function fetchCities(): Promise<string[]> {
  try {
    const res = await fetch('/api/listings/cities');
    if (!res.ok) {
      return [];
    }
    return await res.json();
  } catch (err) {
    console.error('Failed to fetch cities:', err);
    return [];
  }
}

export async function searchListings(
  filters: FilterState,
  page: number
): Promise<SearchResponse> {
  const params = new URLSearchParams();

  if (filters.minPrice.trim() !== '') {
    params.set('minPrice', filters.minPrice.trim());
  }
  if (filters.maxPrice.trim() !== '') {
    params.set('maxPrice', filters.maxPrice.trim());
  }
  if (filters.minBedrooms.trim() !== '') {
    params.set('minBedrooms', filters.minBedrooms.trim());
  }
  if (filters.city.trim() !== '') {
    params.set('city', filters.city.trim());
  }
  if (filters.keyword.trim() !== '') {
    params.set('keyword', filters.keyword.trim());
  }
  if (filters.targetBudget.trim() !== '') {
    params.set('targetBudget', filters.targetBudget.trim());
  }
  if (filters.deduplicate) {
    params.set('deduplicate', 'true');
  }

  params.set('page', page.toString());
  params.set('pageSize', filters.pageSize.toString());

  const response = await fetch(`/api/listings/search?${params.toString()}`);
  const data = await response.json();

  if (!response.ok) {
    const errorMsg = data.detail || `Request failed with status ${response.status}`;
    throw new Error(errorMsg);
  }

  return data as SearchResponse;
}
