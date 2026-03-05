"""Unit tests for the AI-powered product recommendation service."""

import pytest
from recommendation_service import Product, ProductNotFoundError, RecommendationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    """A fresh RecommendationService pre-populated with sample products."""
    svc = RecommendationService()
    products = [
        Product(1, "Classic White T-Shirt", "top", 19.99, "Everyday cotton tee", ["cotton", "casual"], stock=100),
        Product(2, "Blue Denim Jeans", "bottom", 49.99, "Slim-fit denim jeans", ["denim", "casual"], stock=80),
        Product(3, "Black Leather Jacket", "outerwear", 129.99, "Genuine leather biker jacket", ["leather", "casual"], stock=30),
        Product(4, "Floral Summer Dress", "dress", 59.99, "Light floral print dress", ["floral", "casual"], stock=50),
        Product(5, "Running Sneakers", "footwear", 89.99, "Lightweight running shoes", ["sport", "casual"], stock=60),
        Product(6, "Formal White Shirt", "top", 39.99, "Business formal shirt", ["formal", "office"], stock=45),
        Product(7, "Striped T-Shirt", "top", 24.99, "Casual striped cotton tee", ["cotton", "casual", "stripes"], stock=70),
        Product(8, "Slim Chinos", "bottom", 44.99, "Smart casual chino trousers", ["casual", "smart"], stock=55),
    ]
    for p in products:
        svc.add_product(p)
    return svc


@pytest.fixture
def empty_service():
    return RecommendationService()


# ---------------------------------------------------------------------------
# get_similar_products
# ---------------------------------------------------------------------------


def test_get_similar_products_returns_list(service):
    results = service.get_similar_products(1, n=3)
    assert isinstance(results, list)
    assert len(results) == 3


def test_get_similar_products_excludes_reference(service):
    results = service.get_similar_products(1)
    ids = [p.id for p in results]
    assert 1 not in ids


def test_get_similar_products_prefers_same_category(service):
    """Products in the same category (top) should rank first."""
    results = service.get_similar_products(1, n=3)
    top_ids = [p.id for p in results]
    # Products 6 and 7 are also tops – at least one should appear in top-3
    assert 6 in top_ids or 7 in top_ids


def test_get_similar_products_unknown_id_raises(service):
    with pytest.raises(ProductNotFoundError, match="not found"):
        service.get_similar_products(999)


def test_get_similar_products_respects_n(service):
    for n in (1, 2, 5):
        results = service.get_similar_products(1, n=n)
        assert len(results) == n


# ---------------------------------------------------------------------------
# get_recommendations
# ---------------------------------------------------------------------------


def test_get_recommendations_returns_list(service):
    results = service.get_recommendations("user_a")
    assert isinstance(results, list)


def test_get_recommendations_excludes_purchased(service):
    service.record_purchase("user_a", 1)
    service.record_purchase("user_a", 2)
    results = service.get_recommendations("user_a")
    ids = [p.id for p in results]
    assert 1 not in ids
    assert 2 not in ids


def test_get_recommendations_excludes_viewed(service):
    service.record_view("user_b", 3)
    results = service.get_recommendations("user_b")
    ids = [p.id for p in results]
    assert 3 not in ids


def test_get_recommendations_respects_n(service):
    results = service.get_recommendations("new_user", n=3)
    assert len(results) <= 3


def test_get_recommendations_new_user(service):
    """New users without history should still receive recommendations."""
    results = service.get_recommendations("brand_new_user", n=5)
    assert len(results) > 0


def test_get_recommendations_category_preference(service):
    """After purchasing tops the user should receive more top recommendations."""
    service.record_purchase("fan_of_tops", 1)
    service.record_purchase("fan_of_tops", 6)
    results = service.get_recommendations("fan_of_tops", n=4)
    categories = [p.category for p in results]
    # At least one recommended item should be a top (product 7)
    assert "top" in categories


# ---------------------------------------------------------------------------
# get_trending
# ---------------------------------------------------------------------------


def test_get_trending_returns_list(service):
    results = service.get_trending(n=5)
    assert isinstance(results, list)
    assert len(results) <= 5


def test_get_trending_reflects_views(service):
    """Products with more views should rank higher."""
    for _ in range(10):
        service.record_view("user_x", 4)  # Floral Dress
    results = service.get_trending(n=3)
    assert results[0].id == 4


def test_get_trending_purchases_outweigh_views(service):
    """Purchases (weight 3) should outweigh views (weight 1)."""
    for _ in range(5):
        service.record_view("u1", 2)   # 5 views for product 2
    for _ in range(2):
        service.record_purchase("u2", 5)  # 2 purchases for product 5 (score=6)
    results = service.get_trending(n=2)
    top_ids = [p.id for p in results]
    assert top_ids[0] == 5


def test_get_trending_category_filter(service):
    service.record_view("u1", 1)
    service.record_view("u2", 1)
    results = service.get_trending(n=5, category="top")
    assert all(p.category == "top" for p in results)


def test_get_trending_unknown_category_returns_empty(service):
    results = service.get_trending(n=5, category="nonexistent")
    assert results == []


# ---------------------------------------------------------------------------
# record_view / record_purchase
# ---------------------------------------------------------------------------


def test_record_view_updates_product_count(service):
    service.record_view("u1", 1)
    service.record_view("u2", 1)
    assert service._product_views[1] == 2


def test_record_purchase_updates_product_count(service):
    service.record_purchase("u1", 2)
    assert service._product_purchases[2] == 1


# ---------------------------------------------------------------------------
# add_product / remove_product
# ---------------------------------------------------------------------------


def test_add_product(empty_service):
    p = Product(10, "New Top", "top", 29.99)
    empty_service.add_product(p)
    assert 10 in empty_service._products


def test_remove_product(service):
    service.remove_product(1)
    assert 1 not in service._products
    # Similar products should no longer include it
    results = service.get_similar_products(2)
    assert all(p.id != 1 for p in results)


# ---------------------------------------------------------------------------
# Similarity scores (internal helpers)
# ---------------------------------------------------------------------------


def test_same_category_gets_full_category_score(service):
    p1 = service._products[1]   # top
    p7 = service._products[7]   # top
    assert service._category_similarity(p1, p7) == 1.0


def test_different_category_gets_zero_category_score(service):
    p1 = service._products[1]   # top
    p2 = service._products[2]   # bottom
    assert service._category_similarity(p1, p2) == 0.0


def test_same_price_bucket_full_price_similarity(service):
    p1 = Product(100, "A", "top", 30.0)
    p2 = Product(101, "B", "top", 50.0)
    assert service._price_similarity(p1, p2) == 1.0


def test_distant_price_buckets_low_similarity(service):
    cheap = Product(100, "A", "top", 10.0)
    expensive = Product(101, "B", "top", 400.0)
    score = service._price_similarity(cheap, expensive)
    assert score < 0.5


@pytest.mark.parametrize("text1,text2,expected_min", [
    ("cotton casual shirt", "cotton casual tee", 0.3),
    ("completely different words", "nothing in common here xyz", 0.0),
])
def test_text_similarity(service, text1, text2, expected_min):
    p1 = Product(100, text1, "top", 20.0)
    p2 = Product(101, text2, "top", 20.0)
    score = service._text_similarity(p1, p2)
    assert score >= expected_min
