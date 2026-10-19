import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalResults: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  totalResults,
  pageSize,
  onPageChange,
}) => {
  if (totalPages <= 1) {
    return null;
  }

  const startResult = (currentPage - 1) * pageSize + 1;
  const endResult = Math.min(currentPage * pageSize, totalResults);

  // Sliding Window Pagination Algorithm:
  // Prevents DOM explosion when searching large datasets (e.g., 50+ pages).
  // If totalPages <= 7, renders all numbers. Otherwise, renders a sliding window
  // with ellipses around the current page: [1, '...', curr-1, curr, curr+1, '...', totalPages].
  const getPageNumbers = (): (number | string)[] => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages: (number | string)[] = [];
    pages.push(1);

    const start = Math.max(2, currentPage - 1);
    const end = Math.min(totalPages - 1, currentPage + 1);

    if (start > 2) {
      pages.push('ellipsis-start');
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (end < totalPages - 1) {
      pages.push('ellipsis-end');
    }

    pages.push(totalPages);
    return pages;
  };

  const pageItems = getPageNumbers();

  return (
    <nav className="pagination" aria-label="Search results pagination">
      <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
        Showing <strong>{startResult}</strong> – <strong>{endResult}</strong> of{' '}
        <strong>{totalResults}</strong> listings
      </div>

      <div className="pagination-controls">
        <button
          className="page-btn"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          aria-label="Previous Page"
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </button>

        {pageItems.map((item, idx) => {
          if (typeof item === 'string') {
            return (
              <span key={`ellipsis-${idx}`} style={{ padding: '0 4px', color: 'var(--text-muted)' }}>
                …
              </span>
            );
          }
          return (
            <button
              key={item}
              className={`page-btn ${item === currentPage ? 'active' : ''}`}
              onClick={() => onPageChange(item)}
              aria-current={item === currentPage ? 'page' : undefined}
              aria-label={`Go to page ${item}`}
            >
              {item}
            </button>
          );
        })}

        <button
          className="page-btn"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          aria-label="Next Page"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </nav>
  );
};
