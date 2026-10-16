import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["totalListingsLoaded"] == 12


def test_list_cities():
    response = client.get("/api/listings/cities")
    assert response.status_code == 200
    cities = response.json()
    assert "Springfield" in cities
    assert "Fairfax" in cities
    assert "Reston" in cities


def test_search_default_parameters():
    response = client.get("/api/listings/search")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 12
    assert data["page"] == 1
    assert data["pageSize"] == 5
    assert data["totalPages"] == 3
    assert len(data["results"]) == 5


def test_search_with_filters():
    response = client.get(
        "/api/listings/search",
        params={
            "minPrice": 400000,
            "maxPrice": 500000,
            "minBedrooms": 3,
            "city": "Springfield",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0  # 3 bedrooms in Springfield are $525k and $527.5k

    # Test match with higher maxPrice
    response2 = client.get(
        "/api/listings/search",
        params={
            "minPrice": 500000,
            "maxPrice": 550000,
            "minBedrooms": 3,
            "city": "Springfield",
        },
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["total"] == 2  # A2 and B8


def test_search_with_target_budget_relevance():
    response = client.get(
        "/api/listings/search",
        params={"targetBudget": 600000, "pageSize": 3},
    )
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) == 3
    # First result should be closest to $600k (e.g. A4 at $610k or B10 at $585k)
    top_price = results[0]["price"]
    assert top_price in [610000, 585000]
    assert results[0]["budgetScore"] is not None
    assert results[0]["relevanceScore"] > 80.0


def test_search_with_deduplication():
    # Without deduplication
    r_no_dedup = client.get("/api/listings/search", params={"deduplicate": False, "pageSize": 100})
    assert r_no_dedup.status_code == 200
    assert r_no_dedup.json()["total"] == 12

    # With deduplication
    r_dedup = client.get("/api/listings/search", params={"deduplicate": True, "pageSize": 100})
    assert r_dedup.status_code == 200
    data = r_dedup.json()
    assert data["total"] == 8
    assert data["deduplicatedCount"] == 4


def test_search_status_filter():
    # Active only
    res_active = client.get("/api/listings/search", params={"status": "active", "pageSize": 100})
    assert res_active.status_code == 200
    assert res_active.json()["total"] == 11
    assert all(r["status"].lower() == "active" for r in res_active.json()["results"])

    # Pending only
    res_pending = client.get("/api/listings/search", params={"status": "pending"})
    assert res_pending.status_code == 200
    assert res_pending.json()["total"] == 1
    assert res_pending.json()["results"][0]["id"] == "A7"


def test_invalid_status_value():
    response = client.get("/api/listings/search", params={"status": "unknown_status"})
    assert response.status_code == 400
    assert "status must be one of: all, active, pending, sold" in response.json()["detail"]


# ==========================================
# Deliberate Error Handling Tests
# ==========================================

def test_invalid_price_range_min_greater_than_max():
    response = client.get("/api/listings/search", params={"minPrice": 600000, "maxPrice": 400000})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "minPrice" in detail
    assert "cannot be greater than maxPrice" in detail


def test_invalid_negative_price():
    response = client.get("/api/listings/search", params={"minPrice": -100})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "minPrice cannot be negative" in detail


def test_invalid_negative_bedrooms():
    response = client.get("/api/listings/search", params={"minBedrooms": -1})
    assert response.status_code == 400
    assert "minBedrooms cannot be negative" in response.json()["detail"]


def test_invalid_target_budget_zero_or_negative():
    response = client.get("/api/listings/search", params={"targetBudget": 0})
    assert response.status_code == 400
    assert "targetBudget must be greater than zero" in response.json()["detail"]

    response2 = client.get("/api/listings/search", params={"targetBudget": -500})
    assert response2.status_code == 400
    assert "targetBudget must be greater than zero" in response2.json()["detail"]


def test_invalid_page_size_zero_or_negative():
    response = client.get("/api/listings/search", params={"pageSize": 0})
    assert response.status_code == 400
    assert "pageSize must be greater than or equal to 1" in response.json()["detail"]

    response2 = client.get("/api/listings/search", params={"pageSize": -5})
    assert response2.status_code == 400
    assert "pageSize must be greater than or equal to 1" in response2.json()["detail"]


def test_invalid_page_zero_or_negative():
    response = client.get("/api/listings/search", params={"page": 0})
    assert response.status_code == 400
    assert "page must be greater than or equal to 1" in response.json()["detail"]


def test_invalid_page_size_exceeds_max():
    response = client.get("/api/listings/search", params={"pageSize": 101})
    assert response.status_code == 400
    assert "pageSize cannot exceed 100" in response.json()["detail"]


def test_invalid_page_non_numeric():
    response = client.get("/api/listings/search", params={"page": "not_a_number"})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "page" in detail
    assert "valid integer" in detail


def test_empty_results_valid_response():
    response = client.get("/api/listings/search", params={"city": "NonExistentCity"})
    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []
    assert data["total"] == 0
    assert data["totalPages"] == 0


def test_expanded_dataset_toggle():
    # Sample dataset has 12 items
    res_sample = client.get("/api/listings/search", params={"useExpanded": False, "pageSize": 100})
    assert res_sample.status_code == 200
    assert res_sample.json()["total"] == 12

    # Expanded dataset has > 100 items
    res_expanded = client.get("/api/listings/search", params={"useExpanded": True, "pageSize": 10})
    assert res_expanded.status_code == 200
    data_expanded = res_expanded.json()
    assert data_expanded["total"] > 100
    assert data_expanded["totalPages"] > 10

    # Cities in expanded dataset include Arlington, Alexandria, Bethesda
    res_cities = client.get("/api/listings/cities", params={"useExpanded": True})
    assert res_cities.status_code == 200
    cities = res_cities.json()
    assert "Arlington" in cities
    assert "Alexandria" in cities
    assert "Bethesda" in cities


def test_sort_by_price_ascending():
    res = client.get("/api/listings/search", params={"sortBy": "price_asc", "pageSize": 12})
    assert res.status_code == 200
    prices = [r["price"] for r in res.json()["results"]]
    assert prices == sorted(prices)


def test_sort_by_price_descending():
    res = client.get("/api/listings/search", params={"sortBy": "price_desc", "pageSize": 12})
    assert res.status_code == 200
    prices = [r["price"] for r in res.json()["results"]]
    assert prices == sorted(prices, reverse=True)


def test_sort_by_newest():
    res = client.get("/api/listings/search", params={"sortBy": "newest", "pageSize": 12})
    assert res.status_code == 200
    dates = [r["listedDate"] for r in res.json()["results"]]
    assert dates == sorted(dates, reverse=True)


def test_sort_by_sqft_descending():
    res = client.get("/api/listings/search", params={"sortBy": "sqft_desc", "pageSize": 12})
    assert res.status_code == 200
    sqfts = [r["sqft"] for r in res.json()["results"]]
    assert sqfts == sorted(sqfts, reverse=True)


def test_invalid_sort_by():
    res = client.get("/api/listings/search", params={"sortBy": "invalid_order"})
    assert res.status_code == 400
    assert "sortBy must be one of: relevance, price_asc, price_desc, newest, sqft_desc" in res.json()["detail"]


