"""AI-powered product recommendation engine using content-based filtering.

Provides personalized product recommendations by computing similarity scores
based on product attributes such as category, price range, description text,
and user interaction history (views and purchases).
"""

from __future__ import annotations

import logging
import math
from collections import Counter
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Product:
    """Lightweight product data class for the recommendation engine."""

    def __init__(
        self,
        id: int,
        name: str,
        category: str,
        price: float,
        description: str = "",
        tags: Optional[List[str]] = None,
        stock: int = 0,
    ) -> None:
        self.id = id
        self.name = name
        self.category = category.lower()
        self.price = price
        self.description = description
        self.tags = [t.lower() for t in (tags or [])]
        self.stock = stock

    def __repr__(self) -> str:  # pragma: no cover
        return f"Product(id={self.id}, name={self.name!r}, category={self.category!r})"


class ProductNotFoundError(Exception):
    """Raised when a requested product does not exist in the catalogue."""


class RecommendationService:
    """Content-based filtering recommendation engine for fashion products.

    Similarity between products is computed as a weighted sum of:
    - Category similarity (exact match)
    - Price-range similarity (bucketed)
    - Text similarity (word-overlap / Jaccard) of name + description + tags

    Personalised recommendations are built from a user's view and purchase
    history: items already interacted with are excluded, and scores are
    boosted for products in categories the user has previously purchased.
    """

    # Price buckets: (lower_inclusive, upper_exclusive)
    _PRICE_BUCKETS = [(0, 25), (25, 75), (75, 150), (150, 300), (300, math.inf)]

    # Weights for the similarity components
    _W_CATEGORY = 0.45
    _W_PRICE = 0.25
    _W_TEXT = 0.30

    def __init__(self) -> None:
        self._products: Dict[int, Product] = {}
        self._user_views: Dict[str, List[int]] = {}
        self._user_purchases: Dict[str, List[int]] = {}
        self._product_views: Dict[int, int] = Counter()
        self._product_purchases: Dict[int, int] = Counter()

    # ------------------------------------------------------------------
    # Catalogue management
    # ------------------------------------------------------------------

    def add_product(self, product: Product) -> None:
        """Register a product in the recommendation catalogue."""
        self._products[product.id] = product
        logger.debug("Registered product %d in recommendation catalogue", product.id)

    def remove_product(self, product_id: int) -> None:
        """Remove a product from the catalogue."""
        self._products.pop(product_id, None)

    # ------------------------------------------------------------------
    # Interaction tracking
    # ------------------------------------------------------------------

    def record_view(self, user_id: str, product_id: int) -> None:
        """Record that a user viewed a product."""
        self._user_views.setdefault(user_id, []).append(product_id)
        self._product_views[product_id] = self._product_views.get(product_id, 0) + 1

    def record_purchase(self, user_id: str, product_id: int) -> None:
        """Record that a user purchased a product."""
        self._user_purchases.setdefault(user_id, []).append(product_id)
        self._product_purchases[product_id] = (
            self._product_purchases.get(product_id, 0) + 1
        )

    # ------------------------------------------------------------------
    # Recommendation API
    # ------------------------------------------------------------------

    def get_similar_products(
        self, product_id: int, n: int = 5
    ) -> List[Product]:
        """Return the *n* most similar products to the given product.

        Args:
            product_id: ID of the reference product.
            n: Number of recommendations to return.

        Returns:
            Ranked list of similar products (excluding the reference item).

        Raises:
            ProductNotFoundError: If *product_id* is not in the catalogue.
        """
        if product_id not in self._products:
            raise ProductNotFoundError(
                f"Product with id {product_id} not found in catalogue."
            )
        reference = self._products[product_id]
        candidates = [p for p in self._products.values() if p.id != product_id]
        ranked = sorted(
            candidates,
            key=lambda p: self._similarity_score(reference, p),
            reverse=True,
        )
        return ranked[:n]

    def get_recommendations(
        self, user_id: str, n: int = 5
    ) -> List[Product]:
        """Return personalised product recommendations for a user.

        Recommendations are based on the categories and items the user has
        previously viewed or purchased.  Products already seen or bought are
        excluded from the results.

        Args:
            user_id: Identifier of the user.
            n: Number of recommendations to return.

        Returns:
            Ranked list of recommended products.
        """
        seen = set(self._user_views.get(user_id, []))
        bought = set(self._user_purchases.get(user_id, []))
        interacted = seen | bought

        # Build a category preference score from purchase history
        purchased_products = [
            self._products[pid]
            for pid in bought
            if pid in self._products
        ]
        preferred_categories: Counter = Counter(
            p.category for p in purchased_products
        )

        # Compute a personalised score for every unseen product
        candidates = [
            p for p in self._products.values() if p.id not in interacted
        ]

        def personalised_score(product: Product) -> float:
            base = self._product_views.get(product.id, 0) * 0.01
            base += self._product_purchases.get(product.id, 0) * 0.05
            # Boost products whose category matches the user's preferences
            base += preferred_categories.get(product.category, 0) * 0.2
            # If user has purchase history, blend in content-based scores
            if purchased_products:
                max_sim = max(
                    self._similarity_score(ref, product)
                    for ref in purchased_products
                )
                base += max_sim * 0.6
            return base

        ranked = sorted(candidates, key=personalised_score, reverse=True)
        logger.info(
            "Generated %d recommendations for user %s", min(n, len(ranked)), user_id
        )
        return ranked[:n]

    def get_trending(
        self, n: int = 10, category: Optional[str] = None
    ) -> List[Product]:
        """Return the top *n* trending products, optionally filtered by category.

        Trending score combines recent view count (weight 1) and purchase
        count (weight 3) to favour items that users actually buy.

        Args:
            n: Number of trending products to return.
            category: Optional category filter (case-insensitive).

        Returns:
            Ranked list of trending products.
        """
        products = list(self._products.values())
        if category is not None:
            products = [p for p in products if p.category == category.lower()]

        def trending_score(product: Product) -> float:
            views = self._product_views.get(product.id, 0)
            purchases = self._product_purchases.get(product.id, 0)
            return views + purchases * 3

        ranked = sorted(products, key=trending_score, reverse=True)
        return ranked[:n]

    # ------------------------------------------------------------------
    # Similarity computation (internal helpers)
    # ------------------------------------------------------------------

    def _similarity_score(self, p1: Product, p2: Product) -> float:
        """Compute a [0, 1] similarity score between two products."""
        cat_sim = self._category_similarity(p1, p2)
        price_sim = self._price_similarity(p1, p2)
        text_sim = self._text_similarity(p1, p2)
        return (
            self._W_CATEGORY * cat_sim
            + self._W_PRICE * price_sim
            + self._W_TEXT * text_sim
        )

    def _category_similarity(self, p1: Product, p2: Product) -> float:
        """Return 1.0 if products share the same category, else 0.0."""
        return 1.0 if p1.category == p2.category else 0.0

    def _price_similarity(self, p1: Product, p2: Product) -> float:
        """Return a similarity score based on price-range bucket distance."""
        bucket1 = self._price_bucket(p1.price)
        bucket2 = self._price_bucket(p2.price)
        distance = abs(bucket1 - bucket2)
        n_buckets = len(self._PRICE_BUCKETS)
        return max(0.0, 1.0 - distance / (n_buckets - 1))

    def _price_bucket(self, price: float) -> int:
        for i, (low, high) in enumerate(self._PRICE_BUCKETS):
            if low <= price < high:
                return i
        return len(self._PRICE_BUCKETS) - 1

    def _text_similarity(self, p1: Product, p2: Product) -> float:
        """Compute Jaccard similarity on tokenised text (name + description + tags)."""
        tokens1 = self._tokenise(p1)
        tokens2 = self._tokenise(p2)
        if not tokens1 and not tokens2:
            return 0.0
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        return len(intersection) / len(union)

    @staticmethod
    def _tokenise(product: Product) -> set:
        """Return a set of lowercase word tokens for a product."""
        text = " ".join(
            [product.name, product.description, product.category]
            + product.tags
        )
        return {w for w in text.lower().split() if len(w) > 2}
