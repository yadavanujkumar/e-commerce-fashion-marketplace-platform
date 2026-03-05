"""Unit tests for the AI-powered fashion styling service."""

import pytest
from styling_service import Product, StylingService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return StylingService()


@pytest.fixture
def wardrobe():
    """A small wardrobe of fashion products for testing outfit suggestions."""
    return [
        Product(1, "White T-Shirt", "top", 19.99, style="casual", color="white", stock=100),
        Product(2, "Blue Jeans", "bottom", 49.99, style="casual", color="blue", stock=80),
        Product(3, "Black Boots", "footwear", 89.99, style="casual", color="black", stock=40),
        Product(4, "Brown Leather Belt", "accessory", 29.99, style="casual", color="brown", stock=60),
        Product(5, "Navy Blazer", "outerwear", 119.99, style="formal", color="navy", stock=25),
        Product(6, "Floral Summer Dress", "dress", 59.99, style="casual", color="pink", stock=50),
        Product(7, "Running Sneakers", "footwear", 79.99, style="sporty", color="white", stock=70),
        Product(8, "Canvas Tote Bag", "accessory", 24.99, style="casual", color="beige", stock=90),
    ]


# ---------------------------------------------------------------------------
# categorise_item
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name,category,expected", [
    ("Basic Tee", "t-shirt", "top"),
    ("Skinny Jeans", "jeans", "bottom"),
    ("Floral Dress", "dress", "dress"),
    ("White Sneakers", "sneakers", "footwear"),
    ("Wool Coat", "coat", "outerwear"),
    ("Leather Bag", "bag", "accessory"),
    ("Silk Blouse", "blouse", "top"),
    ("Bermuda Shorts", "shorts", "bottom"),
])
def test_categorise_item(service, name, category, expected):
    product = Product(1, name, category, 50.0)
    assert service.categorise_item(product) == expected


def test_categorise_item_falls_back_to_name(service):
    """When the category field is unrecognised, the name should be checked."""
    product = Product(1, "Leather Boots", "footwear_unknown", 100.0)
    # 'boots' keyword is in the name
    result = service.categorise_item(product)
    assert result in ("footwear", "other")


def test_categorise_item_returns_other_for_unknown(service):
    product = Product(1, "Unknown Widget", "unknown_cat", 10.0)
    result = service.categorise_item(product)
    assert result == "other"


# ---------------------------------------------------------------------------
# suggest_outfit
# ---------------------------------------------------------------------------


def test_suggest_outfit_returns_list(service, wardrobe):
    base = wardrobe[0]  # White T-Shirt (top)
    outfit = service.suggest_outfit(base, wardrobe)
    assert isinstance(outfit, list)


def test_suggest_outfit_excludes_base_item(service, wardrobe):
    base = wardrobe[0]  # top
    outfit = service.suggest_outfit(base, wardrobe)
    assert base not in outfit


def test_suggest_outfit_top_includes_bottom_and_footwear(service, wardrobe):
    base = wardrobe[0]  # top
    outfit = service.suggest_outfit(base, wardrobe)
    categories = [service.categorise_item(p) for p in outfit]
    assert "bottom" in categories
    assert "footwear" in categories


def test_suggest_outfit_dress_includes_footwear(service, wardrobe):
    base = wardrobe[5]  # Floral Summer Dress
    outfit = service.suggest_outfit(base, wardrobe)
    categories = [service.categorise_item(p) for p in outfit]
    assert "footwear" in categories


def test_suggest_outfit_respects_max_items(service, wardrobe):
    base = wardrobe[0]  # top
    for max_items in (1, 2, 3):
        outfit = service.suggest_outfit(base, wardrobe, max_items=max_items)
        assert len(outfit) <= max_items


def test_suggest_outfit_empty_wardrobe(service):
    base = Product(1, "White Tee", "top", 19.99)
    outfit = service.suggest_outfit(base, [])
    assert outfit == []


def test_suggest_outfit_no_compatible_items(service):
    """Only the base item available – should return empty outfit."""
    base = Product(1, "White Tee", "top", 19.99)
    outfit = service.suggest_outfit(base, [base])
    assert outfit == []


# ---------------------------------------------------------------------------
# score_outfit_compatibility
# ---------------------------------------------------------------------------


def test_compatibility_top_and_bottom(service):
    top = Product(1, "T-Shirt", "top", 20.0, style="casual", color="white")
    bottom = Product(2, "Jeans", "bottom", 50.0, style="casual", color="blue")
    score = service.score_outfit_compatibility(top, bottom)
    assert 0.0 <= score <= 1.0
    assert score > 0.5  # compatible pair should score above mid-point


def test_compatibility_same_category_lower_score(service):
    """Two tops should score lower than a top + bottom pair."""
    top1 = Product(1, "T-Shirt", "top", 20.0, style="casual", color="white")
    top2 = Product(2, "Blouse", "top", 30.0, style="casual", color="black")
    bottom = Product(3, "Jeans", "bottom", 50.0, style="casual", color="blue")
    score_same = service.score_outfit_compatibility(top1, top2)
    score_diff = service.score_outfit_compatibility(top1, bottom)
    assert score_diff > score_same


def test_compatibility_score_range(service, wardrobe):
    """All compatibility scores must be in [0, 1]."""
    for i, p1 in enumerate(wardrobe):
        for p2 in wardrobe[i + 1:]:
            score = service.score_outfit_compatibility(p1, p2)
            assert 0.0 <= score <= 1.0, f"Score out of range for {p1} and {p2}"


def test_colour_neutral_with_anything(service):
    """Black (neutral) should be highly compatible with any colour."""
    black_top = Product(1, "Black Tee", "top", 20.0, color="black")
    blue_bottom = Product(2, "Blue Jeans", "bottom", 50.0, color="blue")
    score = service._colour_compatibility(black_top, blue_bottom)
    assert score == 1.0


def test_colour_same_family(service):
    navy_top = Product(1, "Navy Shirt", "top", 30.0, color="navy")
    cobalt_bottom = Product(2, "Cobalt Jeans", "bottom", 55.0, color="cobalt")
    score = service._colour_compatibility(navy_top, cobalt_bottom)
    assert score >= 0.8


def test_style_same_is_fully_compatible(service):
    p1 = Product(1, "Casual Tee", "top", 20.0, style="casual")
    p2 = Product(2, "Casual Jeans", "bottom", 50.0, style="casual")
    score = service._style_compatibility(p1, p2)
    assert score == 1.0


def test_style_incompatible_pair(service):
    formal = Product(1, "Suit Jacket", "outerwear", 200.0, style="formal")
    sporty = Product(2, "Running Shorts", "bottom", 30.0, style="sporty")
    score = service._style_compatibility(formal, sporty)
    assert score < 0.5


# ---------------------------------------------------------------------------
# get_style_profile
# ---------------------------------------------------------------------------


def test_style_profile_empty_history(service):
    profile = service.get_style_profile([])
    assert profile["preferred_categories"] == []
    assert profile["preferred_styles"] == []
    assert profile["preferred_colors"] == []
    assert profile["avg_price"] == 0.0


def test_style_profile_returns_expected_keys(service, wardrobe):
    profile = service.get_style_profile(wardrobe)
    assert "preferred_categories" in profile
    assert "preferred_styles" in profile
    assert "preferred_colors" in profile
    assert "avg_price" in profile


def test_style_profile_preferred_category(service):
    history = [
        Product(1, "Tee", "top", 20.0),
        Product(2, "Shirt", "top", 30.0),
        Product(3, "Blouse", "top", 25.0),
        Product(4, "Jeans", "bottom", 50.0),
    ]
    profile = service.get_style_profile(history)
    assert profile["preferred_categories"][0] == "top"


def test_style_profile_avg_price(service):
    history = [
        Product(1, "A", "top", 10.0),
        Product(2, "B", "bottom", 30.0),
    ]
    profile = service.get_style_profile(history)
    assert profile["avg_price"] == 20.0


@pytest.mark.parametrize("styles,expected_top", [
    (["casual", "casual", "sporty"], "casual"),
    (["formal", "formal", "formal"], "formal"),
])
def test_style_profile_preferred_style(service, styles, expected_top):
    history = [
        Product(i, f"Item {i}", "top", 20.0, style=s)
        for i, s in enumerate(styles)
    ]
    profile = service.get_style_profile(history)
    assert profile["preferred_styles"][0] == expected_top
