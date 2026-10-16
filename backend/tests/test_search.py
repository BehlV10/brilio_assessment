from datetime import date
import pytest
from app.loader import load_listings
from app.models import Listing, SearchParams
from app.search import (
    calculate_scores,
    deduplicate_scored_listings,
    filter_listings,
    get_deduplication_key,
    normalize_address,
    paginate_listings,
)


@pytest.fixture
def sample_data():
    return load_listings()


# ==========================================
# Filtering Tests
# ==========================================

def test_filter_by_price_range(sample_data):
    # Filter between $400,000 and $500,000
    params = SearchParams(minPrice=400000, maxPrice=500000)
    results = filter_listings(sample_data, params)
    
    assert len(results) > 0
    for item in results:
        assert 400000 <= item.price <= 500000


def test_filter_by_min_bedrooms(sample_data):
    params = SearchParams(minBedrooms=4)
    results = filter_listings(sample_data, params)
    
    assert len(results) == 2  # A4 (Reston) and A7 (Chantilly)
    for item in results:
        assert item.bedrooms >= 4


def test_filter_by_city_case_insensitive(sample_data):
    params = SearchParams(city="fairfax")
    results = filter_listings(sample_data, params)
    assert len(results) == 2
    assert all(r.city.lower() == "fairfax" for r in results)

    # Substring match
    params_sub = SearchParams(city="Spring")
    results_sub = filter_listings(sample_data, params_sub)
    assert len(results_sub) == 4  # A1, B7, A2, B8 in Springfield


def test_filter_by_keyword_in_description(sample_data):
    # Search for "pets"
    params = SearchParams(keyword="pet")
    results = filter_listings(sample_data, params)
    assert len(results) > 0
    for r in results:
        assert "pet" in r.description.lower()

    # Search for specific phrase "garage"
    params_garage = SearchParams(keyword="garage")
    results_garage = filter_listings(sample_data, params_garage)
    assert len(results_garage) == 1
    assert results_garage[0].id == "B10"


def test_filter_no_matches(sample_data):
    params = SearchParams(minPrice=9000000)
    results = filter_listings(sample_data, params)
    assert len(results) == 0


# ==========================================
# Scoring & Ranking Tests
# ==========================================

def test_scoring_with_target_budget(sample_data):
    # Set target budget to $450,000
    target_budget = 450000.0
    ref_date = date(2026, 9, 4)
    
    scored = calculate_scores(sample_data, target_budget=target_budget, ref_date=ref_date)
    
    assert len(scored) == len(sample_data)
    # The top ranked listing should be very close to $450k and recent
    top = scored[0]
    assert abs(top.price - target_budget) <= 2000  # A1 ($450k) or B7 ($452k)
    assert top.relevanceScore > 80.0
    assert top.budgetScore is not None
    assert top.budgetScore >= 99.0  # Close to 100% budget match


def test_scoring_without_target_budget_relies_on_recency(sample_data):
    ref_date = date(2026, 9, 4)
    scored = calculate_scores(sample_data, target_budget=None, ref_date=ref_date)
    
    # When targetBudget is None, relevanceScore equals recencyScore
    for item in scored:
        assert item.budgetScore is None
        assert item.relevanceScore == item.recencyScore

    # Newest listing (A5 listed on 2026-09-04) should have highest recency score of 100.0
    top = scored[0]
    assert top.listedDate == "2026-09-04"
    assert top.recencyScore == 100.0


def test_tied_scores_deterministic_sort():
    # Two listings with same score and date, sorted by lower price then id
    l1 = Listing(
        id="Z2", source="MLS_A", address="10 Main St", city="Springfield",
        state="VA", zip="22150", price=500000, bedrooms=2, bathrooms=1.0,
        sqft=1000, latitude=38.0, longitude=-77.0, listedDate="2026-09-01",
        status="active", description="Test 1"
    )
    l2 = Listing(
        id="Z1", source="MLS_B", address="20 Main St", city="Springfield",
        state="VA", zip="22150", price=400000, bedrooms=2, bathrooms=1.0,
        sqft=1000, latitude=38.0, longitude=-77.0, listedDate="2026-09-01",
        status="active", description="Test 2"
    )
    
    scored = calculate_scores([l1, l2], target_budget=None, ref_date=date(2026, 9, 1))
    # Both have recency 100.0, l2 has lower price ($400k vs $500k), so l2 comes first
    assert scored[0].id == "Z1"
    assert scored[1].id == "Z2"


# ==========================================
# Deduplication Tests
# ==========================================

def test_address_normalization():
    assert normalize_address("123 Main St, Apt 4B") == "123 main street unit 4b"
    assert normalize_address("123 Main Street, Unit 4B") == "123 main street unit 4b"
    assert normalize_address("456 Oak Ave") == "456 oak avenue"
    assert normalize_address("456 Oak Avenue") == "456 oak avenue"


def test_deduplication_removes_cross_mls_duplicates(sample_data):
    # Total sample listings: 12
    # Known duplicates:
    # A1 & B7 (123 Main St)
    # A2 & B8 (456 Oak Ave)
    # A3 & B9 (789 Pine Rd)
    # A5 & B11 (55 Elm Ct)
    # Unique properties: 8
    scored = calculate_scores(sample_data, target_budget=500000)
    deduped, removed_count = deduplicate_scored_listings(scored)
    
    assert removed_count == 4
    assert len(deduped) == 8

    # Check that duplicates retained otherSources
    main_st = next(x for x in deduped if "123 Main" in x.address)
    assert main_st.isDuplicate is True
    assert len(main_st.otherSources) == 1


# ==========================================
# Pagination Boundary Tests
# ==========================================

def test_pagination_boundaries(sample_data):
    scored = calculate_scores(sample_data)
    total = len(scored)  # 12
    
    # Page 1 of 5 items
    p1, total_count, total_pages = paginate_listings(scored, page=1, pageSize=5)
    assert len(p1) == 5
    assert total_count == 12
    assert total_pages == 3
    assert p1[0].id == scored[0].id

    # Page 3 (last page, should have 2 items: 12 - 10)
    p3, _, _ = paginate_listings(scored, page=3, pageSize=5)
    assert len(p3) == 2
    assert p3[-1].id == scored[-1].id

    # Page 4 (out of bounds)
    p4, total_count, total_pages = paginate_listings(scored, page=4, pageSize=5)
    assert len(p4) == 0
    assert total_count == 12
    assert total_pages == 3


def test_pagination_empty_list():
    page_items, total, total_pages = paginate_listings([], page=1, pageSize=10)
    assert page_items == []
    assert total == 0
    assert total_pages == 0
