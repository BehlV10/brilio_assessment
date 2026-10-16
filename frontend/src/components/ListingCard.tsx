import React from 'react';
import { Listing } from '../types';
import { Bed, Bath, Maximize2, Calendar, Sparkles } from 'lucide-react';

interface ListingCardProps {
  listing: Listing;
}

export const ListingCard: React.FC<ListingCardProps> = ({ listing }) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const isHighRelevance = listing.relevanceScore >= 85;

  return (
    <article className="listing-card">
      <div className="listing-card-header">
        <div className="listing-address-box">
          <h2 className="listing-address">{listing.address}</h2>
          <p className="listing-location">
            {listing.city}, {listing.state} {listing.zip}
          </p>
        </div>

        <div className="score-badge-container">
          <div className="listing-price">{formatCurrency(listing.price)}</div>
          <div
            className={`score-badge ${isHighRelevance ? 'high' : ''}`}
            title="Composite score based on target budget proximity and recency"
          >
            <Sparkles size={13} />
            Relevance: {listing.relevanceScore.toFixed(1)} / 100
          </div>
          <div className="score-breakdown">
            {listing.budgetScore !== null && (
              <span>Budget: {listing.budgetScore.toFixed(0)}%</span>
            )}
            <span>Recency: {listing.recencyScore.toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Badges */}
      <div className="badges-row">
        <span className="badge badge-source">{listing.source}</span>
        <span
          className={`badge ${
            listing.status.toLowerCase() === 'active'
              ? 'badge-active'
              : 'badge-pending'
          }`}
        >
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
        <div className="stat-item" style={{ color: 'var(--text-muted)' }}>
          <Calendar size={15} />
          <span>Listed {listing.listedDate}</span>
        </div>
      </div>

      <p className="listing-description">{listing.description}</p>
    </article>
  );
};
