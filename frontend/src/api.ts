import { FilterState, SearchResponse } from './types';
import { executeClientSearch, getClientCities } from './clientSearch';

export async function fetchCities(useExpanded: boolean = false): Promise<string[]> {
  try {
    const res = await fetch(`/api/listings/cities?useExpanded=${useExpanded}`);
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Backend API not reachable (e.g. running on GitHub Pages)
  }

  // Fallback to client-side data
  return getClientCities(useExpanded);
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
  if (filters.status && filters.status.trim() !== '') {
    params.set('status', filters.status.trim());
  }
  if (filters.targetBudget.trim() !== '') {
    params.set('targetBudget', filters.targetBudget.trim());
  }
  if (filters.deduplicate) {
    params.set('deduplicate', 'true');
  }
  if (filters.useExpanded) {
    params.set('useExpanded', 'true');
  }

  params.set('page', page.toString());
  params.set('pageSize', filters.pageSize.toString());

  try {
    const response = await fetch(`/api/listings/search?${params.toString()}`);
    
    // If backend returned a deliberate 400 or other error
    if (response.status === 400) {
      const data = await response.json();
      throw new Error(data.detail || 'Invalid search parameters');
    }

    if (response.ok) {
      return await response.json();
    }
  } catch (err: any) {
    // If this was a deliberate 400 error thrown above, re-throw it!
    if (err.message && !err.message.includes('fetch') && !err.message.includes('NetworkError')) {
      throw err;
    }
  }

  // If backend is not available (such as on GitHub Pages static hosting),
  // execute the exact same search logic client-side:
  return executeClientSearch(filters, page);
}
