import sampleData from './data/sample_listings.json';
import expandedData from './data/expanded_listings.json';
import { FilterState, Listing, SearchResponse } from './types';

export function getClientCities(useExpanded: boolean = false): string[] {
  const dataset = useExpanded ? expandedData : sampleData;
  const cities = Array.from(new Set((dataset as any[]).map((i) => i.city)));
  return cities.sort();
}

function normalizeAddress(address: string): string {
  let s = address.toLowerCase();
  s = s.replace(/#\s*/g, 'unit ');
  s = s.replace(/[,.]/g, ' ');
  const map: [RegExp, string][] = [
    [/\bst\b/g, 'street'],
    [/\bave\b/g, 'avenue'],
    [/\bct\b/g, 'court'],
    [/\brd\b/g, 'road'],
    [/\bln\b/g, 'lane'],
    [/\bdr\b/g, 'drive'],
    [/\bblvd\b/g, 'boulevard'],
    [/\bapt\b/g, 'unit'],
    [/\bste\b/g, 'unit'],
    [/\bapartment\b/g, 'unit'],
    [/\bsuite\b/g, 'unit'],
  ];
  for (const [pattern, repl] of map) {
    s = s.replace(pattern, repl);
  }
  return s.split(/\s+/).join(' ').trim();
}

function getDeduplicationKey(listing: any): string {
  const normAddr = normalizeAddress(listing.address);
  const tokens = normAddr.split(' ');
  const streetNum = tokens[0] || '';
  const unitMatch = normAddr.match(/\bunit\s+([a-z0-9-]+)\b/);
  const unitPart = unitMatch ? `unit_${unitMatch[1]}` : '';
  const latR = Number(listing.latitude).toFixed(4);
  const lonR = Number(listing.longitude).toFixed(4);
  return unitPart ? `${streetNum}_${unitPart}_${latR}_${lonR}` : `${streetNum}_${latR}_${lonR}`;
}

export function executeClientSearch(filters: FilterState, page: number): SearchResponse {
  const minP = filters.minPrice.trim() !== '' ? Number(filters.minPrice) : null;
  const maxP = filters.maxPrice.trim() !== '' ? Number(filters.maxPrice) : null;
  const minBed = filters.minBedrooms.trim() !== '' ? Number(filters.minBedrooms) : null;
  const budget = filters.targetBudget.trim() !== '' ? Number(filters.targetBudget) : null;
  const pageSize = Number(filters.pageSize) || 5;

  // Deliberate validations
  if (minP !== null && minP < 0) throw new Error('minPrice cannot be negative');
  if (maxP !== null && maxP < 0) throw new Error('maxPrice cannot be negative');
  if (minP !== null && maxP !== null && minP > maxP) {
    throw new Error(
      `minPrice ($${minP.toLocaleString()}) cannot be greater than maxPrice ($${maxP.toLocaleString()})`
    );
  }
  if (minBed !== null && minBed < 0) throw new Error('minBedrooms cannot be negative');
  if (budget !== null && budget <= 0) throw new Error('targetBudget must be greater than zero');
  if (pageSize < 1) throw new Error('pageSize must be greater than or equal to 1');
  if (pageSize > 100) throw new Error('pageSize cannot exceed 100');
  if (page < 1) throw new Error('page must be greater than or equal to 1');

  // 1. Filtering
  const cityQ = filters.city.trim().toLowerCase();
  const kwQ = filters.keyword.trim().toLowerCase();
  const statusQ = filters.status ? filters.status.trim().toLowerCase() : 'all';

  const dataset = filters.useExpanded ? expandedData : sampleData;

  // Reference date anchored to dataset maximum (deterministic across queries)
  const refDate = new Date(
    Math.max(...(dataset as any[]).map((item) => new Date(item.listedDate).getTime()))
  );

  const filtered = (dataset as any[]).filter((item) => {
    if (minP !== null && item.price < minP) return false;
    if (maxP !== null && item.price > maxP) return false;
    if (minBed !== null && item.bedrooms < minBed) return false;
    if (statusQ && statusQ !== 'all' && item.status.toLowerCase() !== statusQ) return false;
    if (cityQ && !item.city.toLowerCase().includes(cityQ)) return false;
    if (kwQ) {
      const inDesc = item.description.toLowerCase().includes(kwQ);
      const inAddr = item.address.toLowerCase().includes(kwQ);
      if (!inDesc && !inAddr) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    return {
      results: [],
      total: 0,
      page,
      pageSize,
      totalPages: 0,
      deduplicatedCount: 0,
    };
  }

  // 2. Scoring & Ranking
  const scored: Listing[] = filtered.map((item) => {
    const itemDate = new Date(item.listedDate);
    const diffDays = Math.max(
      0,
      Math.floor((refDate.getTime() - itemDate.getTime()) / (1000 * 60 * 60 * 24))
    );

    // 30-day half-life decay
    const recencyNormalized = 1.0 / (1.0 + diffDays / 30.0);
    const recencyScore = Number((recencyNormalized * 100.0).toFixed(1));

    let budgetScore: number | null = null;
    let baseRelevance: number = recencyScore;

    if (budget !== null && budget > 0) {
      const relDiff = Math.abs(item.price - budget) / budget;
      const budgetNormalized = Math.exp(-3.0 * relDiff);
      budgetScore = Number((budgetNormalized * 100.0).toFixed(1));
      baseRelevance = 0.7 * budgetScore + 0.3 * recencyScore;
    }

    // Status penalty multiplier: 1.0 active, 0.7 pending, 0.3 sold
    const itemStatus = item.status.toLowerCase();
    const statusMultiplier = itemStatus === 'pending' ? 0.7 : itemStatus === 'sold' ? 0.3 : 1.0;
    const relevanceScore = Number((baseRelevance * statusMultiplier).toFixed(1));
    const pricePerSqft = item.sqft > 0 ? Math.round(item.price / item.sqft) : undefined;

    return {
      ...item,
      relevanceScore,
      budgetScore,
      recencyScore,
      statusMultiplier,
      pricePerSqft,
      daysAgo: diffDays,
      isDuplicate: false,
      duplicateGroupId: getDeduplicationKey(item),
      otherSources: [],
    };
  });

  function sortClientListings(list: Listing[], sortBy: string): Listing[] {
    const sb = (sortBy || 'relevance').toLowerCase();
    list.sort((a, b) => {
      if (sb === 'price_asc') {
        if (a.price !== b.price) return a.price - b.price;
        return b.relevanceScore - a.relevanceScore;
      }
      if (sb === 'price_desc') {
        if (a.price !== b.price) return b.price - a.price;
        return b.relevanceScore - a.relevanceScore;
      }
      if (sb === 'newest') {
        const dateDiff = new Date(b.listedDate).getTime() - new Date(a.listedDate).getTime();
        if (dateDiff !== 0) return dateDiff;
        return b.relevanceScore - a.relevanceScore;
      }
      if (sb === 'sqft_desc') {
        if (a.sqft !== b.sqft) return b.sqft - a.sqft;
        return a.price - b.price;
      }
      // 'relevance'
      if (b.relevanceScore !== a.relevanceScore) {
        return b.relevanceScore - a.relevanceScore;
      }
      const dateDiff = new Date(b.listedDate).getTime() - new Date(a.listedDate).getTime();
      if (dateDiff !== 0) return dateDiff;
      if (a.price !== b.price) return a.price - b.price;
      return a.id.localeCompare(b.id);
    });
    return list;
  }

  // Initial sort
  sortClientListings(scored, filters.sortBy);

  // 3. Deduplication
  let finalResults = scored;
  let dedupCount = 0;

  if (filters.deduplicate) {
    const groups = new Map<string, Listing[]>();
    for (const item of scored) {
      const key = item.duplicateGroupId || getDeduplicationKey(item);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(item);
    }

    const deduped: Listing[] = [];
    for (const cluster of groups.values()) {
      let best = cluster[0];
      const activeCandidates = cluster.filter((c) => c.status.toLowerCase() === 'active');
      if (activeCandidates.length > 0 && best.status.toLowerCase() !== 'active') {
        best = activeCandidates[0];
      }
      const otherSources = Array.from(
        new Set(
          cluster
            .filter((c) => c.id !== best.id || c.source !== best.source)
            .map((c) => c.source)
        )
      );

      deduped.push({
        ...best,
        isDuplicate: cluster.length > 1,
        otherSources,
      });
      dedupCount += cluster.length - 1;
    }

    sortClientListings(deduped, filters.sortBy);
    finalResults = deduped;
  }

  // 4. Pagination
  const total = finalResults.length;
  const totalPages = Math.ceil(total / pageSize);
  const start = (page - 1) * pageSize;
  const pageItems = start < total ? finalResults.slice(start, start + pageSize) : [];

  return {
    results: pageItems,
    total,
    page,
    pageSize,
    totalPages,
    deduplicatedCount: dedupCount,
  };
}
