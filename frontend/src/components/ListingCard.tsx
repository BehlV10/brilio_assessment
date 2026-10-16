import React, { useState } from 'react';
import { Listing } from '../types';
import { Bed, Bath, Maximize2, Calendar, Sparkles, Tag, ChevronDown, ChevronUp, Info } from 'lucide-react';

interface ListingCardProps {
  listing: Listing;
  keyword?: string;
  targetBudget?: string;
}

export const ListingCard: React.FC<ListingCardProps> = ({
  listing,
  keyword,
  targetBudget,
}) => {
  const [showMath, setShowMath] = useState(false);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const isHighRelevance = listing.relevanceScore >= 85;

  // Highlight matching keyword
  const highlightText = (text: string, searchWord?: string) => {
    if (!searchWord || !searchWord.trim()) return text;
    const q = searchWord.trim();
    const regex = new RegExp(`(${q})`, 'gi');
    const parts = text.split(regex);
    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark
          key={i}
          style={{
            backgroundColor: '#fef08a',
            color: '#854d0e',
            padding: '1px 3px',
            borderRadius: '3px',
            fontWeight: 600,
          }}
        >
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  const statusLower = listing.status.toLowerCase();
  const statusBadgeClass =
    statusLower === 'active'
      ? 'badge-active'
      : statusLower === 'pending'
      ? 'badge-pending'
      : 'badge-source';

  const budgetNum = targetBudget && targetBudget.trim() !== '' ? Number(targetBudget) : null;
  const budgetDiff = budgetNum ? listing.price - budgetNum : null;

  return (
    <article className="listing-card">
      <div className="listing-card-header">
        <div className="listing-address-box">
          <h2 className="listing-address">{highlightText(listing.address, keyword)}</h2>
          <p className="listing-location">
            {listing.city}, {listing.state} {listing.zip}
          </p>
        </div>

        <div className="score-badge-container">
          <div className="listing-price">{formatCurrency(listing.price)}</div>
          <div
            className={`score-badge ${isHighRelevance ? 'high' : ''}`}
            title="Composite score based on target budget proximity, recency, and status"
          >
            <Sparkles size={13} />
            Relevance: {listing.relevanceScore.toFixed(1)} / 100
          </div>
          <div className="score-breakdown">
            {listing.budgetScore !== null && (
              <span>Budget: {listing.budgetScore.toFixed(0)}%</span>
            )}
            <span>Recency: {listing.recencyScore.toFixed(0)}%</span>
            {statusLower === 'pending' && (
              <span style={{ color: '#d97706', fontWeight: 600 }}>(-30% pending)</span>
            )}
            {statusLower === 'sold' && (
              <span style={{ color: '#64748b', fontWeight: 600 }}>(-70% sold)</span>
            )}
          </div>
        </div>
      </div>

      {/* Badges */}
      <div className="badges-row">
        <span className="badge badge-source">{listing.source}</span>
        <span className={`badge ${statusBadgeClass}`}>
          {listing.status}
        </span>
        {listing.otherSources && listing.otherSources.length > 0 && (
          <span className="badge badge-other-sources" title="Duplicate feed sources merged">
            Also available on {listing.otherSources.join(', ')}
          </span>
        )}
      </div>

      {/* Property Details */}
      <div className="listing-stats">
        <div className="stat-item">
          <Bed size={16} />
          <span>
            <strong>{listing.bedrooms}</strong> beds
          </span>
        </div>
        <div className="stat-item">
          <Bath size={16} />
          <span>
            <strong>{listing.bathrooms}</strong> baths
          </span>
        </div>
        <div className="stat-item">
          <Maximize2 size={15} />
          <span>
            <strong>{listing.sqft.toLocaleString()}</strong> sqft
          </span>
        </div>
        {listing.pricePerSqft && (
          <div className="stat-item" style={{ color: 'var(--text-muted)' }}>
            <Tag size={14} />
            <span>
              <strong>${listing.pricePerSqft}</strong> /sqft
            </span>
          </div>
        )}
        <div className="stat-item" style={{ color: 'var(--text-muted)' }}>
          <Calendar size={14} />
          <span>
            {listing.daysAgo !== undefined ? `${listing.daysAgo}d ago (${listing.listedDate})` : listing.listedDate}
          </span>
        </div>
      </div>

      <p className="listing-description">{highlightText(listing.description, keyword)}</p>

      {/* Score Explainability Toggle */}
      <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px dashed var(--border)' }}>
        <button
          type="button"
          onClick={() => setShowMath(!showMath)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--primary)',
            fontSize: '0.75rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.3rem',
            padding: '2px 0',
          }}
        >
          <Info size={13} />
          {showMath ? 'Hide Score Formula' : 'Explain Score Calculation'}
          {showMath ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>

        {showMath && (
          <div
            style={{
              marginTop: '0.5rem',
              padding: '0.75rem 1rem',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '0.775rem',
              color: '#334155',
              lineHeight: 1.6,
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: '0.25rem', color: 'var(--text-main)' }}>
              Relevance Calculation Breakdown:
            </div>
            {budgetNum !== null && listing.budgetScore !== null ? (
              <div>
                • <strong>Budget Match ({listing.budgetScore.toFixed(1)}%)</strong>: Target is{' '}
                {formatCurrency(budgetNum)}. Property is {formatCurrency(listing.price)}{' '}
                ({budgetDiff! >= 0 ? `+$${Math.abs(budgetDiff!).toLocaleString()} over` : `-$${Math.abs(budgetDiff!).toLocaleString()} under`} budget,{' '}
                {((Math.abs(budgetDiff!) / budgetNum) * 100).toFixed(1)}% deviation). Uses exponential decay: exp(-3.0 × Δ).
              </div>
            ) : (
              <div>• <strong>Budget Match</strong>: No target budget specified (bypassed).</div>
            )}
            <div>
              • <strong>Recency Match ({listing.recencyScore.toFixed(1)}%)</strong>: Listed{' '}
              {listing.daysAgo !== undefined ? `${listing.daysAgo} days ago` : `on ${listing.listedDate}`}. Uses 30-day half-life decay formula: 1 / (1 + days/30).
            </div>
            <div>
              • <strong>Status Multiplier ({listing.statusMultiplier || 1.0}×)</strong>:{' '}
              {statusLower === 'active'
                ? '1.0× (Active property ready for purchase)'
                : statusLower === 'pending'
                ? '0.7× (-30% discount because property is already under contract)'
                : '0.3× (-70% discount for historical sold comp)'}
            </div>
            <div style={{ marginTop: '0.35rem', paddingTop: '0.35rem', borderTop: '1px solid #e2e8f0', fontWeight: 600 }}>
              Formula: {budgetNum ? `(0.70 × ${listing.budgetScore?.toFixed(1)}% + 0.30 × ${listing.recencyScore.toFixed(1)}%)` : `${listing.recencyScore.toFixed(1)}%`}{' '}
              × {listing.statusMultiplier || 1.0} = <span style={{ color: 'var(--primary)' }}>{listing.relevanceScore.toFixed(1)} / 100</span>
            </div>
          </div>
        )}
      </div>
    </article>
  );
};
