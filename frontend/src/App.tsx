import React, { useState, useEffect, useCallback } from 'react';
import { FilterState, SearchResponse } from './types';
import { fetchCities, searchListings } from './api';
import { SearchFilters } from './components/SearchFilters';
import { ListingCard } from './components/ListingCard';
import { Pagination } from './components/Pagination';
import { ErrorAlert } from './components/ErrorAlert';
import { Building2, Layers } from 'lucide-react';

const initialFilters: FilterState = {
  minPrice: '',
  maxPrice: '',
  minBedrooms: '',
  city: '',
  keyword: '',
  status: 'all',
  targetBudget: '',
  deduplicate: false,
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
    fetchCities().then(setCities);
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

    // If deduplicate toggle, status dropdown, or pageSize was flipped, trigger search immediately
    if (
      updated.deduplicate !== undefined ||
      updated.status !== undefined ||
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
            <ListingCard key={`${listing.source}-${listing.id}`} listing={listing} />
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
