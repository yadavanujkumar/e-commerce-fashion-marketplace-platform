"""AI-powered fashion styling assistant.

Provides outfit recommendations by suggesting complementary fashion items
based on outfit-composition rules (which garment categories go together),
style-attribute compatibility (casual, formal, sporty, etc.), and
colour-family compatibility.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class Product:
    """Lightweight product data class for the styling engine."""

    def __init__(
        self,
        id: int,
        name: str,
        category: str,
        price: float,
        description: str = "",
        tags: Optional[List[str]] = None,
        color: str = "",
        style: str = "",
        stock: int = 0,
    ) -> None:
        self.id = id
        self.name = name
        self.category = category.lower()
        self.price = price
        self.description = description
        self.tags = [t.lower() for t in (tags or [])]
        self.color = color.lower()
        self.style = style.lower()
        self.stock = stock

    def __repr__(self) -> str:  # pragma: no cover
        return f"Product(id={self.id}, name={self.name!r}, category={self.category!r})"


class StylingService:
    """AI fashion styling assistant providing outfit suggestions.

    Outfit compatibility is scored using three signals:

    1. **Outfit-composition rules** – which garment categories naturally pair
       together (e.g. tops + bottoms + footwear).
    2. **Style-attribute compatibility** – items that share or complement style
       labels (casual, formal, sporty, bohemian, …) score higher.
    3. **Colour-family compatibility** – colours within the same family or that
       form classic pairings (neutrals with anything, complementary pairs)
       receive a compatibility bonus.
    """

    # Maps outfit_category -> keywords that indicate membership
    OUTFIT_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        "top": [
            "shirt", "blouse", "t-shirt", "tshirt", "tee", "top", "sweater",
            "pullover", "hoodie", "crop", "tank", "tube",
        ],
        "bottom": [
            "pants", "jeans", "trousers", "shorts", "skirt", "leggings",
            "jogger", "chinos", "culottes",
        ],
        "dress": ["dress", "gown", "frock", "jumpsuit", "romper", "playsuit"],
        "footwear": [
            "shoes", "boots", "sneakers", "sandals", "heels", "loafers",
            "flats", "pumps", "mules", "slides", "trainers",
        ],
        "outerwear": [
            "coat", "jacket", "blazer", "cardigan", "parka", "trench",
            "windbreaker", "anorak", "vest",
        ],
        "accessory": [
            "bag", "purse", "belt", "hat", "cap", "scarf", "gloves",
            "jewelry", "jewellery", "necklace", "bracelet", "ring",
            "earrings", "watch", "sunglasses", "socks", "tights",
        ],
    }

    # Which outfit categories naturally complement each other
    OUTFIT_RULES: Dict[str, List[str]] = {
        "top": ["bottom", "footwear", "accessory", "outerwear"],
        "bottom": ["top", "footwear", "outerwear", "accessory"],
        "dress": ["footwear", "accessory", "outerwear"],
        "footwear": ["top", "bottom", "dress", "outerwear"],
        "outerwear": ["top", "bottom", "dress", "footwear", "accessory"],
        "accessory": ["top", "bottom", "dress", "outerwear"],
    }

    # Style compatibility: pairs of styles that work together well
    _COMPATIBLE_STYLES: List[Tuple[str, str]] = [
        ("casual", "casual"),
        ("formal", "formal"),
        ("sporty", "sporty"),
        ("bohemian", "bohemian"),
        ("streetwear", "streetwear"),
        ("casual", "sporty"),
        ("formal", "classic"),
        ("classic", "formal"),
        ("bohemian", "casual"),
    ]

    # Colour family groups – items within the same group are compatible
    _COLOR_FAMILIES: List[List[str]] = [
        ["black", "white", "grey", "gray", "charcoal", "ivory", "cream"],  # neutrals
        ["navy", "blue", "cobalt", "indigo", "royal blue"],
        ["red", "burgundy", "crimson", "wine", "maroon"],
        ["green", "olive", "forest", "sage", "khaki"],
        ["pink", "rose", "blush", "fuchsia", "magenta"],
        ["brown", "tan", "camel", "beige", "nude", "taupe"],
        ["yellow", "mustard", "gold", "amber"],
        ["orange", "coral", "terracotta", "rust"],
        ["purple", "lavender", "lilac", "violet", "plum"],
    ]

    # Neutrals (black / white / grey / beige) go with almost anything
    _NEUTRAL_COLORS = {"black", "white", "grey", "gray", "beige", "nude", "cream", "ivory"}

    def categorise_item(self, product: Product) -> str:
        """Determine the outfit category of a product.

        The category is inferred by searching the product's name, category
        field, description and tags for recognised keywords.  Returns
        ``"other"`` when no match is found.
        """
        # First try the explicit category field
        for outfit_cat, keywords in self.OUTFIT_CATEGORY_KEYWORDS.items():
            if product.category in keywords or product.category == outfit_cat:
                return outfit_cat

        # Fall back to searching all text fields
        text = " ".join(
            [product.name, product.description, product.category] + product.tags
        ).lower()
        for outfit_cat, keywords in self.OUTFIT_CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return outfit_cat

        return "other"

    def suggest_outfit(
        self,
        base_product: Product,
        available_products: List[Product],
        max_items: int = 4,
    ) -> List[Product]:
        """Suggest complementary items to complete an outfit.

        Args:
            base_product: The anchor garment for which to build an outfit.
            available_products: Pool of candidate products.
            max_items: Maximum number of additional items to include.

        Returns:
            A ranked list of complementary products (excluding the base item
            itself).  One product per complementary outfit category is
            selected, up to *max_items*.
        """
        base_cat = self.categorise_item(base_product)
        allowed_cats = self.OUTFIT_RULES.get(base_cat, list(self.OUTFIT_RULES.keys()))

        # Score every candidate and group by outfit category
        scored: Dict[str, List[Tuple[float, Product]]] = {}
        for product in available_products:
            if product.id == base_product.id:
                continue
            candidate_cat = self.categorise_item(product)
            if candidate_cat not in allowed_cats:
                continue
            score = self.score_outfit_compatibility(base_product, product)
            scored.setdefault(candidate_cat, []).append((score, product))

        # Pick the best item per complementary category, up to max_items
        outfit: List[Product] = []
        for cat in allowed_cats:
            if len(outfit) >= max_items:
                break
            candidates = scored.get(cat, [])
            if not candidates:
                continue
            best = max(candidates, key=lambda x: x[0])
            outfit.append(best[1])

        logger.info(
            "Outfit suggested for product %d (%s): %d items",
            base_product.id,
            base_cat,
            len(outfit),
        )
        return outfit

    def score_outfit_compatibility(
        self, product1: Product, product2: Product
    ) -> float:
        """Compute a [0, 1] compatibility score for two fashion items.

        The score combines:
        - Category rule score (are these categories meant to be worn together?)
        - Style compatibility (do their style labels match or complement?)
        - Colour compatibility (do their colours work together?)
        """
        cat_score = self._category_rule_score(product1, product2)
        style_score = self._style_compatibility(product1, product2)
        colour_score = self._colour_compatibility(product1, product2)
        return 0.5 * cat_score + 0.3 * style_score + 0.2 * colour_score

    def get_style_profile(
        self,
        purchase_history: List[Product],
    ) -> Dict[str, object]:
        """Analyse a user's style profile from their purchase history.

        Args:
            purchase_history: List of products the user has bought.

        Returns:
            A dict with keys:
            - ``preferred_categories``: Most-bought outfit categories.
            - ``preferred_styles``: Most-common style labels.
            - ``preferred_colors``: Most-common colour values.
            - ``avg_price``: Average spend per item.
        """
        if not purchase_history:
            return {
                "preferred_categories": [],
                "preferred_styles": [],
                "preferred_colors": [],
                "avg_price": 0.0,
            }

        cat_counter: Counter = Counter(
            self.categorise_item(p) for p in purchase_history
        )
        style_counter: Counter = Counter(
            p.style for p in purchase_history if p.style
        )
        color_counter: Counter = Counter(
            p.color for p in purchase_history if p.color
        )
        avg_price = sum(p.price for p in purchase_history) / len(purchase_history)

        return {
            "preferred_categories": [cat for cat, _ in cat_counter.most_common(3)],
            "preferred_styles": [s for s, _ in style_counter.most_common(3)],
            "preferred_colors": [c for c, _ in color_counter.most_common(3)],
            "avg_price": round(avg_price, 2),
        }

    # ------------------------------------------------------------------
    # Internal scoring helpers
    # ------------------------------------------------------------------

    def _category_rule_score(self, p1: Product, p2: Product) -> float:
        """Return 1.0 if the two outfit categories complement each other."""
        cat1 = self.categorise_item(p1)
        cat2 = self.categorise_item(p2)
        allowed = self.OUTFIT_RULES.get(cat1, [])
        return 1.0 if cat2 in allowed else 0.0

    def _style_compatibility(self, p1: Product, p2: Product) -> float:
        """Return a [0, 1] style compatibility score."""
        if not p1.style or not p2.style:
            return 0.5  # neutral when style information is missing
        if p1.style == p2.style:
            return 1.0
        for s1, s2 in self._COMPATIBLE_STYLES:
            if (p1.style == s1 and p2.style == s2) or (
                p1.style == s2 and p2.style == s1
            ):
                return 0.8
        return 0.2

    def _colour_compatibility(self, p1: Product, p2: Product) -> float:
        """Return a [0, 1] colour compatibility score."""
        if not p1.color or not p2.color:
            return 0.5  # neutral when colour information is missing
        if p1.color == p2.color:
            return 0.9  # same colour – possible, but not always ideal
        # Neutral colours pair with everything
        if p1.color in self._NEUTRAL_COLORS or p2.color in self._NEUTRAL_COLORS:
            return 1.0
        # Colours in the same family
        for family in self._COLOR_FAMILIES:
            if p1.color in family and p2.color in family:
                return 0.8
        return 0.3
