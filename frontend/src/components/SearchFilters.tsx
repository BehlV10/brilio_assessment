import React from 'react';
import { FilterState } from '../types';
import { Search, RotateCcw, CopyCheck, Database } from 'lucide-react';

interface SearchFiltersProps {
  filters: FilterState;
  cities: string[];
  onChange: (updated: Partial<FilterState>) => void;
  onSubmit: (e: React.FormEvent) => void;
  onReset: () => void;
  isLoading: boolean;
}

export const SearchFilters: React.FC<SearchFiltersProps> = ({
  filters,
  cities,
  onChange,
  onSubmit,
  onReset,
  isLoading,
}) => {
  return (
    <form className="filter-card" onSubmit={onSubmit}>
      {/* Dataset Selection Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.75rem',
          paddingBottom: '1rem',
          marginBottom: '1.25rem',
          borderBottom: '1px solid var(--border)',
        }}
      >
        {/* Dataset Selection: Allows testing with candidate handout data (12) vs expanded synthetic data (112) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', fontWeight: 600 }}>
          <Database size={16} color="var(--primary)" />
          <span>Active Dataset:</span>
        </div>

        <div style={{ display: 'inline-flex', background: '#f1f5f9', padding: '3px', borderRadius: '8px' }}>
          <button
            type="button"
            className="btn"
            style={{
              padding: '0.35rem 0.85rem',
              fontSize: '0.8rem',
              borderRadius: '6px',
              border: 'none',
              background: !filters.useExpanded ? 'white' : 'transparent',
              color: !filters.useExpanded ? 'var(--primary)' : 'var(--text-muted)',
              boxShadow: !filters.useExpanded ? '0 1px 2px rgba(0,0,0,0.08)' : 'none',
              fontWeight: !filters.useExpanded ? 700 : 500,
            }}
            onClick={() => onChange({ useExpanded: false, city: '' })}
          >
            Sample (12 listings)
          </button>
          <button
            type="button"
            className="btn"
            style={{
              padding: '0.35rem 0.85rem',
              fontSize: '0.8rem',
              borderRadius: '6px',
              border: 'none',
              background: filters.useExpanded ? 'white' : 'transparent',
              color: filters.useExpanded ? 'var(--primary)' : 'var(--text-muted)',
              boxShadow: filters.useExpanded ? '0 1px 2px rgba(0,0,0,0.08)' : 'none',
              fontWeight: filters.useExpanded ? 700 : 500,
            }}
            onClick={() => onChange({ useExpanded: true, city: '' })}
          >
            Expanded (112 listings)
          </button>
        </div>
      </div>

      <div className="filter-grid">
        {/* Keyword Search */}
        <div className="filter-group" style={{ gridColumn: 'span 2' }}>
          <label className="filter-label" htmlFor="keyword">
            Keywords (searches description)
          </label>
          <input
            id="keyword"
            type="text"
            className="filter-input"
            placeholder="e.g. condo, pet friendly, fenced yard, garage"
            value={filters.keyword}
            onChange={(e) => onChange({ keyword: e.target.value })}
          />
        </div>

        {/* City Filter */}
        <div className="filter-group">
          <label className="filter-label" htmlFor="city">
            City
          </label>
          <select
            id="city"
            className="filter-select"
            value={filters.city}
            onChange={(e) => onChange({ city: e.target.value })}
          >
            <option value="">All Cities</option>
            {cities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        {/* Min Bedrooms */}
        <div className="filter-group">
          <label className="filter-label" htmlFor="minBedrooms">
            Min Bedrooms
          </label>
          <select
            id="minBedrooms"
            className="filter-select"
            value={filters.minBedrooms}
            onChange={(e) => onChange({ minBedrooms: e.target.value })}
          >
            <option value="">Any Bedrooms</option>
            <option value="1">1+ Bedrooms</option>
            <option value="2">2+ Bedrooms</option>
            <option value="3">3+ Bedrooms</option>
            <option value="4">4+ Bedrooms</option>
          </select>
        </div>

        {/* Listing Status */}
        <div className="filter-group">
          <label className="filter-label" htmlFor="status">
            Listing Status
          </label>
          <select
            id="status"
            className="filter-select"
            value={filters.status}
            onChange={(e) => onChange({ status: e.target.value })}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="pending">Pending Only</option>
            <option value="sold">Sold Only</option>
          </select>
        </div>

        {/* Min Price */}
        <div className="filter-group">
          <label className="filter-label" htmlFor="minPrice">
            Min Price ($)
          </label>
          <input
            id="minPrice"
            type="number"
            step="5000"
            className="filter-input"
            placeholder="e.g. 400000"
            value={filters.minPrice}
            onChange={(e) => onChange({ minPrice: e.target.value })}
          />
        </div>

        {/* Max Price */}
        <div className="filter-group">
          <label className="filter-label" htmlFor="maxPrice">
            Max Price ($)
          </label>
          <input
            id="maxPrice"
            type="number"
            step="5000"
            className="filter-input"
            placeholder="e.g. 600000"
            value={filters.maxPrice}
            onChange={(e) => onChange({ maxPrice: e.target.value })}
          />
        </div>

        {/* Target Budget */}
        <div className="filter-group">
          <label className="filter-label" htmlFor="targetBudget">
            Target Budget ($ for ranking)
          </label>
          <input
            id="targetBudget"
            type="number"
            step="5000"
            className="filter-input"
            placeholder="e.g. 500000"
            value={filters.targetBudget}
            onChange={(e) => onChange({ targetBudget: e.target.value })}
          />
        </div>

        {/* Sort Order */}
        <div className="filter-group">
          <label className="filter-label" htmlFor="sortBy">
            Sort Order
          </label>
          <select
            id="sortBy"
            className="filter-select"
            value={filters.sortBy}
            onChange={(e) => onChange({ sortBy: e.target.value })}
          >
            <option value="relevance">Best Match (Relevance)</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="newest">Newest Listed First</option>
            <option value="sqft_desc">SqFt: Largest First</option>
          </select>
        </div>

        {/* Page Size */}
        <div className="filter-group">
          <label className="filter-label" htmlFor="pageSize">
            Page Size
          </label>
          <select
            id="pageSize"
            className="filter-select"
            value={filters.pageSize}
            onChange={(e) => onChange({ pageSize: Number(e.target.value) })}
          >
            <option value={3}>3 per page</option>
            <option value={5}>5 per page</option>
            <option value={10}>10 per page</option>
          </select>
        </div>
      </div>

      {/* Deduplication & Actions */}
      <div className="filter-actions-row">
        {/* Keyboard-accessible custom toggle switch: Announces role="switch" and aria-checked to screen readers */}
        <button
          type="button"
          role="switch"
          aria-checked={filters.deduplicate}
          className="toggle-container"
          onClick={() => onChange({ deduplicate: !filters.deduplicate })}
          onKeyDown={(e) => {
            if (e.key === ' ' || e.key === 'Enter') {
              e.preventDefault();
              onChange({ deduplicate: !filters.deduplicate });
            }
          }}
          title="Cluster matching listings across MLS sources and retain the best result"
          style={{ background: 'none', border: 'none', padding: 0, font: 'inherit', textAlign: 'left', cursor: 'pointer' }}
        >
          <div className={`toggle-switch ${filters.deduplicate ? 'active' : ''}`} aria-hidden="true">
            <div className="toggle-thumb" />
          </div>
          <span className="toggle-text" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <CopyCheck size={16} aria-hidden="true" /> Hide duplicates across MLS sources
          </span>
        </button>

        <div className="btn-group">
          <button type="button" className="btn btn-secondary" onClick={onReset}>
            <RotateCcw size={15} /> Reset
          </button>
          <button type="submit" className="btn btn-primary" disabled={isLoading}>
            <Search size={15} /> {isLoading ? 'Searching...' : 'Apply Search'}
          </button>
        </div>
      </div>
    </form>
  );
};
