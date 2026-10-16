import React, { useState, useEffect, useCallback } from 'react';
import { FilterState, SearchResponse } from './types';
import { fetchCities, searchListings } from './api';
import { SearchFilters } from './components/SearchFilters';
import { ListingCard } from './components/ListingCard';
import { Pagination } from './components/Pagination';
import { ErrorAlert } from './components/ErrorAlert';
import { Building2, Layers, X } from 'lucide-react';

const initialFilters: FilterState = {
  minPrice: '',
  maxPrice: '',
  minBedrooms: '',
  city: '',
  keyword: '',
  status: 'all',
  targetBudget: '',
  deduplicate: false,
  useExpanded: false,
  sortBy: 'relevance',
  pageSize: 5,
};

export const App: React.FC = () => {
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [cities, setCities] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load available cities on mount
  useEffect(() => {
    fetchCities(false).then(setCities);
  }, []);

  // Fetch listings function
  const executeSearch = useCallback(
    async (searchFilters: FilterState, targetPage: number) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await searchListings(searchFilters, targetPage);
        setData(response);
      } catch (err: any) {
        setError(err.message || 'An unexpected error occurred.');
        setData(null);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  // Initial load
  useEffect(() => {
    executeSearch(filters, 1);
  }, []);

  const handleFilterChange = (updated: Partial<FilterState>) => {
    const nextFilters = { ...filters, ...updated };
    setFilters(nextFilters);

    // If dataset toggle was changed, also reload cities
    if (updated.useExpanded !== undefined) {
      fetchCities(nextFilters.useExpanded).then(setCities);
      setCurrentPage(1);
      executeSearch(nextFilters, 1);
      return;
    }

    // If deduplicate toggle, status dropdown, sort order, or pageSize was flipped, trigger search immediately
    if (
      updated.deduplicate !== undefined ||
      updated.status !== undefined ||
      updated.sortBy !== undefined ||
      (updated.pageSize !== undefined && updated.pageSize !== filters.pageSize)
    ) {
      setCurrentPage(1);
      executeSearch(nextFilters, 1);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    executeSearch(filters, 1);
  };

  const handleReset = () => {
    setFilters(initialFilters);
    setCurrentPage(1);
    executeSearch(initialFilters, 1);
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    executeSearch(filters, newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const removeFilter = (key: keyof FilterState) => {
    const updated: Partial<FilterState> = {};
    if (key === 'deduplicate') updated.deduplicate = false;
    else if (key === 'status') updated.status = 'all';
    else if (key === 'sortBy') updated.sortBy = 'relevance';
    else if (key === 'pageSize') updated.pageSize = 5;
    else (updated as any)[key] = '';
    handleFilterChange(updated);
  };

  // Collect active filters for chips
  const activeChips: { label: string; key: keyof FilterState }[] = [];
  if (filters.city) activeChips.push({ label: `City: ${filters.city}`, key: 'city' });
  if (filters.keyword) activeChips.push({ label: `Keyword: "${filters.keyword}"`, key: 'keyword' });
  if (filters.status !== 'all') activeChips.push({ label: `Status: ${filters.status}`, key: 'status' });
  if (filters.minBedrooms) activeChips.push({ label: `${filters.minBedrooms}+ Beds`, key: 'minBedrooms' });
  if (filters.minPrice) activeChips.push({ label: `Min: $${Number(filters.minPrice).toLocaleString()}`, key: 'minPrice' });
  if (filters.maxPrice) activeChips.push({ label: `Max: $${Number(filters.maxPrice).toLocaleString()}`, key: 'maxPrice' });
  if (filters.targetBudget) activeChips.push({ label: `Budget: $${Number(filters.targetBudget).toLocaleString()}`, key: 'targetBudget' });
  if (filters.sortBy !== 'relevance') activeChips.push({ label: `Sort: ${filters.sortBy.replace('_', ' ')}`, key: 'sortBy' });
  if (filters.deduplicate) activeChips.push({ label: 'Deduplicated', key: 'deduplicate' });

  return (
    <div className="container">
      {/* Header */}
      <header className="app-header">
        <div>
          <h1 className="app-title">
            <Building2 size={30} color="#2563eb" />
            Listing Search Service
          </h1>
          <p className="app-subtitle">
            Cross-MLS property aggregator with relevance scoring & deduplication
          </p>
        </div>
      </header>

      {/* Search Filters */}
      <SearchFilters
        filters={filters}
        cities={cities}
        onChange={handleFilterChange}
        onSubmit={handleFormSubmit}
        onReset={handleReset}
        isLoading={isLoading}
      />

      {/* Error Alert */}
      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Active Filter Chips */}
      {activeChips.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)' }}>
            Active Filters:
          </span>
          {activeChips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={() => removeFilter(chip.key)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.2rem 0.55rem',
                background: '#e0f2fe',
                color: '#0369a1',
                borderRadius: '999px',
                border: '1px solid #bae6fd',
                fontSize: '0.75rem',
                fontWeight: 500,
                cursor: 'pointer',
              }}
              title={`Remove ${chip.label}`}
            >
              <span>{chip.label}</span>
              <X size={12} />
            </button>
          ))}
          <button
            type="button"
            onClick={handleReset}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--primary)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              textDecoration: 'underline',
              marginLeft: '0.25rem',
            }}
          >
            Clear all
          </button>
        </div>
      )}

      {/* Results Header / Meta */}
      {data && !error && (
        <div className="results-meta">
          <div>
            Found <span className="results-count">{data.total}</span> listing
            {data.total === 1 ? '' : 's'}
            {filters.city && ` in ${filters.city}`}
            {filters.targetBudget && ` (ranked around $${Number(filters.targetBudget).toLocaleString()} budget)`}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {data.deduplicatedCount > 0 && (
              <span className="dedup-pill">
                <Layers size={13} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'text-bottom' }} />
                {data.deduplicatedCount} duplicate{data.deduplicatedCount === 1 ? '' : 's'} hidden
              </span>
            )}
            <span>
              Page {data.page} of {Math.max(1, data.totalPages)}
            </span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="state-box">
          <div className="spinner" />
          <div className="state-title">Loading Listings</div>
          <p>Scoring relevance and filtering results...</p>
        </div>
      )}

      {/* Results List */}
      {!isLoading && data && data.results.length > 0 && (
        <main className="listings-list">
          {data.results.map((listing) => (
            <ListingCard
              key={`${listing.source}-${listing.id}`}
              listing={listing}
              keyword={filters.keyword}
              targetBudget={filters.targetBudget}
            />
          ))}
        </main>
      )}

      {/* No Results Empty State */}
      {!isLoading && data && data.results.length === 0 && (
        <div className="state-box">
          <div className="state-title">No listings found</div>
          <p>No properties match your current search criteria.</p>
          <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
            Try broadening your price range, clearing the keyword, or selecting "All Cities".
          </p>
        </div>
      )}

      {/* Pagination */}
      {data && (
        <Pagination
          currentPage={currentPage}
          totalPages={data.totalPages}
          totalResults={data.total}
          pageSize={data.pageSize}
          onPageChange={handlePageChange}
        />
      )}
    </div>
  );
};

export default App;
