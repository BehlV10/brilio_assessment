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
  if (filters.sortBy) {
    params.set('sortBy', filters.sortBy);
  }

  params.set('page', page.toString());
  params.set('pageSize', filters.pageSize.toString());

  try {
    const response = await fetch(`/api/listings/search?${params.toString()}`);
    
    // Deliberate 400 validation error from FastAPI
    if (response.status === 400) {
      const data = await response.json();
      throw new Error(data.detail || 'Invalid search parameters');
    }

    // 5xx Server Error: do NOT swallow, alert user
    if (response.status >= 500) {
      throw new Error(`Server Error (${response.status}): Failed to execute search.`);
    }

    if (response.ok) {
      const data: SearchResponse = await response.json();
      return { ...data, engineMode: 'backend' };
    }
  } catch (err: any) {
    // If it's an explicit validation or server error, re-throw it!
    if (
      err.message &&
      !err.message.includes('fetch') &&
      !err.message.includes('NetworkError') &&
      !err.message.includes('Failed to fetch') &&
      !err.message.includes('Load failed')
    ) {
      throw err;
    }
  }

  // If backend is unreachable (e.g. GitHub Pages static demo), execute client-side engine:
  const clientData = executeClientSearch(filters, page);
  return { ...clientData, engineMode: 'client' };
}
