"""
Ingredient parsing and normalization.

This module handles parsing ingredient strings into structured data,
including quantities, units, names, and preparation notes.
"""

import re
from fractions import Fraction
from typing import Optional

from ..models import ParsedIngredient, Unit


class IngredientParser:
    """
    Parses ingredient strings into structured ParsedIngredient objects.
    """

    # Unicode fraction mappings
    UNICODE_FRACTIONS = {
        "½": "1/2",
        "⅓": "1/3",
        "⅔": "2/3",
        "¼": "1/4",
        "¾": "3/4",
        "⅕": "1/5",
        "⅖": "2/5",
        "⅗": "3/5",
        "⅘": "4/5",
        "⅙": "1/6",
        "⅚": "5/6",
        "⅛": "1/8",
        "⅜": "3/8",
        "⅝": "5/8",
        "⅞": "7/8",
    }

    # Unit mappings (various forms -> normalized)
    UNIT_MAPPINGS = {
        # Teaspoon
        "teaspoon": "tsp",
        "teaspoons": "tsp",
        "tsp": "tsp",
        "tsps": "tsp",
        "t": "tsp",
        # Tablespoon
        "tablespoon": "tbsp",
        "tablespoons": "tbsp",
        "tbsp": "tbsp",
        "tbsps": "tbsp",
        "tbs": "tbsp",
        "T": "tbsp",
        # Cup
        "cup": "cup",
        "cups": "cup",
        "c": "cup",
        # Fluid ounce
        "fluid ounce": "fl oz",
        "fluid ounces": "fl oz",
        "fl oz": "fl oz",
        "fl. oz.": "fl oz",
        "fl. oz": "fl oz",
        # Pint
        "pint": "pint",
        "pints": "pint",
        "pt": "pint",
        # Quart
        "quart": "quart",
        "quarts": "quart",
        "qt": "quart",
        # Gallon
        "gallon": "gallon",
        "gallons": "gallon",
        "gal": "gallon",
        # Milliliter
        "milliliter": "ml",
        "milliliters": "ml",
        "ml": "ml",
        "mL": "ml",
        # Liter
        "liter": "L",
        "liters": "L",
        "litre": "L",
        "litres": "L",
        "l": "L",
        "L": "L",
        # Ounce
        "ounce": "oz",
        "ounces": "oz",
        "oz": "oz",
        "oz.": "oz",
        # Pound
        "pound": "lb",
        "pounds": "lb",
        "lb": "lb",
        "lbs": "lb",
        "lb.": "lb",
        "lbs.": "lb",
        # Gram
        "gram": "g",
        "grams": "g",
        "g": "g",
        "gr": "g",
        # Kilogram
        "kilogram": "kg",
        "kilograms": "kg",
        "kg": "kg",
        "kilo": "kg",
        "kilos": "kg",
        # Count items
        "piece": "piece",
        "pieces": "piece",
        "pc": "piece",
        "pcs": "piece",
        "whole": "whole",
        "clove": "clove",
        "cloves": "clove",
        "slice": "slice",
        "slices": "slice",
        "pinch": "pinch",
        "pinches": "pinch",
        "dash": "dash",
        "dashes": "dash",
        "bunch": "bunch",
        "bunches": "bunch",
        "sprig": "sprig",
        "sprigs": "sprig",
        "can": "can",
        "cans": "can",
        "package": "package",
        "packages": "package",
        "pkg": "package",
        "pkgs": "package",
        "jar": "jar",
        "jars": "jar",
        "bottle": "bottle",
        "bottles": "bottle",
        "stick": "stick",
        "sticks": "stick",
        "head": "head",
        "heads": "head",
        "stalk": "stalk",
        "stalks": "stalk",
        "rib": "rib",
        "ribs": "rib",
        "ear": "ear",
        "ears": "ear",
        "large": "large",
        "medium": "medium",
        "small": "small",
    }

    # Unit to Unit enum mapping
    UNIT_TO_ENUM = {
        "tsp": Unit.TEASPOON,
        "tbsp": Unit.TABLESPOON,
        "cup": Unit.CUP,
        "fl oz": Unit.FLUID_OUNCE,
        "pint": Unit.PINT,
        "quart": Unit.QUART,
        "gallon": Unit.GALLON,
        "ml": Unit.MILLILITER,
        "L": Unit.LITER,
        "oz": Unit.OUNCE,
        "lb": Unit.POUND,
        "g": Unit.GRAM,
        "kg": Unit.KILOGRAM,
        "piece": Unit.PIECE,
        "whole": Unit.WHOLE,
        "clove": Unit.CLOVE,
        "slice": Unit.SLICE,
        "pinch": Unit.PINCH,
        "dash": Unit.DASH,
        "bunch": Unit.BUNCH,
        "sprig": Unit.SPRIG,
        "can": Unit.CAN,
        "package": Unit.PACKAGE,
    }

    # Preparation words (things done to ingredients)
    PREPARATION_WORDS = {
        "chopped",
        "minced",
        "diced",
        "sliced",
        "grated",
        "crushed",
        "mashed",
        "peeled",
        "cored",
        "seeded",
        "deveined",
        "julienned",
        "cubed",
        "halved",
        "quartered",
        "beaten",
        "whisked",
        "melted",
        "softened",
        "toasted",
        "roasted",
        "sautéed",
        "sauteed",
        "browned",
        "caramelized",
        "blanched",
        "steamed",
        "boiled",
        "cooked",
        "uncooked",
        "raw",
        "fresh",
        "dried",
        "frozen",
        "thawed",
        "chilled",
        "cold",
        "warm",
        "hot",
        "room temperature",
        "at room temperature",
        "finely chopped",
        "coarsely chopped",
        "roughly chopped",
        "thinly sliced",
        "divided",
        "separated",
        "plus more for garnish",
        "for garnish",
        "for serving",
        "to taste",
        "as needed",
        "packed",
        "lightly packed",
        "firmly packed",
        "sifted",
        "zested",
    }

    # Form factors (physical form of ingredient)
    FORM_FACTORS = {
        "shredded",
        "grated",
        "crumbled",
        "block",
        "sliced",
        "cubed",
        "diced",
        "whole",
        "ground",
        "powdered",
        "crushed",
        "flaked",
        "chunk",
        "chunks",
        "strips",
        "rings",
        "wedges",
        "spears",
        "florets",
        "leaves",
        "stalks",
        "kernels",
        "segments",
        "zest",
        "juice",
        "puree",
        "paste",
        "sauce",
        "canned",
        "jarred",
        "fresh",
        "dried",
        "frozen",
        "boneless",
        "bone-in",
        "skinless",
        "skin-on",
        "thick-cut",
        "thin-cut",
    }

    # Common ingredient name normalizations
    INGREDIENT_NORMALIZATIONS = {
        "all-purpose flour": "flour",
        "all purpose flour": "flour",
        "ap flour": "flour",
        "plain flour": "flour",
        "white flour": "flour",
        "granulated sugar": "sugar",
        "white sugar": "sugar",
        "caster sugar": "sugar",
        "kosher salt": "salt",
        "sea salt": "salt",
        "table salt": "salt",
        "fine salt": "salt",
        "coarse salt": "salt",
        "black pepper": "pepper",
        "ground black pepper": "pepper",
        "freshly ground black pepper": "pepper",
        "freshly ground pepper": "pepper",
        "unsalted butter": "butter",
        "salted butter": "butter",
        "olive oil": "olive oil",
        "extra virgin olive oil": "olive oil",
        "extra-virgin olive oil": "olive oil",
        "evoo": "olive oil",
        "vegetable oil": "vegetable oil",
        "canola oil": "canola oil",
        "garlic clove": "garlic",
        "garlic cloves": "garlic",
        "clove garlic": "garlic",
        "cloves garlic": "garlic",
        "yellow onion": "onion",
        "white onion": "onion",
        "red onion": "red onion",
        "green onion": "green onion",
        "green onions": "green onion",
        "scallion": "green onion",
        "scallions": "green onion",
        "spring onion": "green onion",
        "spring onions": "green onion",
    }

    def __init__(self):
        """Initialize the parser."""
        # Build regex patterns
        self._build_patterns()

    def _build_patterns(self):
        """Build regex patterns for parsing."""
        # Quantity pattern (handles fractions, decimals, ranges)
        # Matches: 1, 1/2, 1.5, 1 1/2, 1-2, 1 to 2, etc.
        fraction = r"(?:\d+\s+)?\d+/\d+"  # 1/2 or 1 1/2
        decimal = r"\d+\.?\d*"  # 1 or 1.5
        qty_single = f"(?:{fraction}|{decimal})"
        self.quantity_pattern = re.compile(
            rf"^({qty_single})(?:\s*[-–—to]\s*({qty_single}))?",
            re.IGNORECASE,
        )

        # Build unit pattern from mappings
        unit_words = sorted(self.UNIT_MAPPINGS.keys(), key=len, reverse=True)
        unit_pattern_str = "|".join(re.escape(u) for u in unit_words)
        self.unit_pattern = re.compile(
            rf"\b({unit_pattern_str})\.?\b",
            re.IGNORECASE,
        )

        # Parenthetical pattern for things like (15 oz), (about 2 cups)
        self.paren_pattern = re.compile(r"\(([^)]+)\)")

        # Optional indicator
        self.optional_pattern = re.compile(r"\boptional\b", re.IGNORECASE)

    def parse(self, text: str) -> ParsedIngredient:
        """
        Parse an ingredient string into components.

        Args:
            text: The ingredient string (e.g., "2 cups flour, sifted")

        Returns:
            A ParsedIngredient object with parsed components
        """
        original = text.strip()
        working = original

        # Replace unicode fractions
        for uf, ascii_f in self.UNICODE_FRACTIONS.items():
            working = working.replace(uf, ascii_f)

        # Check for optional
        optional = bool(self.optional_pattern.search(working))
        working = self.optional_pattern.sub("", working)

        # Extract parenthetical info (might contain size info)
        paren_contents = []
        for match in self.paren_pattern.finditer(working):
            paren_contents.append(match.group(1))
        working = self.paren_pattern.sub(" ", working)

        # Extract quantity
        quantity = None
        quantity_max = None
        qty_match = self.quantity_pattern.match(working.strip())
        if qty_match:
            quantity = self._parse_quantity(qty_match.group(1))
            if qty_match.group(2):
                quantity_max = self._parse_quantity(qty_match.group(2))
            working = working[qty_match.end() :].strip()

        # Extract unit
        unit = None
        unit_normalized = None
        unit_match = self.unit_pattern.match(working.strip())
        if unit_match:
            unit_raw = unit_match.group(1)
            unit = self.UNIT_MAPPINGS.get(unit_raw.lower(), unit_raw)
            unit_normalized = self.UNIT_TO_ENUM.get(unit)
            working = working[unit_match.end() :].strip()

        # Check parenthetical for additional size info
        for paren in paren_contents:
            # Look for quantity and unit in parentheses
            paren_qty_match = self.quantity_pattern.match(paren.strip())
            if paren_qty_match:
                paren_unit_match = self.unit_pattern.search(paren)
                if paren_unit_match:
                    # This is size info like "(15 oz)"
                    if unit is None:
                        unit_raw = paren_unit_match.group(1)
                        unit = self.UNIT_MAPPINGS.get(unit_raw.lower(), unit_raw)
                        unit_normalized = self.UNIT_TO_ENUM.get(unit)

        # Clean up working text
        working = re.sub(r"\s+", " ", working).strip()
        working = working.strip(",").strip()

        # Split on comma to separate name from preparation
        parts = working.split(",", 1)
        name_part = parts[0].strip()
        prep_part = parts[1].strip() if len(parts) > 1 else ""

        # Extract form factor and preparation from name and prep parts
        form_factor = None
        preparation = None

        # Check for form factors in name
        name_words = name_part.split()
        form_words = []
        remaining_words = []

        for word in name_words:
            word_lower = word.lower()
            if word_lower in self.FORM_FACTORS:
                form_words.append(word_lower)
            else:
                remaining_words.append(word)

        if form_words:
            form_factor = " ".join(form_words)
            name_part = " ".join(remaining_words)

        # Check prep part for preparation instructions
        if prep_part:
            prep_lower = prep_part.lower()
            # Check if it's primarily preparation
            prep_words_found = []
            for prep_word in self.PREPARATION_WORDS:
                if prep_word in prep_lower:
                    prep_words_found.append(prep_word)

            if prep_words_found:
                preparation = prep_part
            else:
                # Might be additional ingredient info
                name_part = f"{name_part}, {prep_part}"

        # Also check if any form factors are in the prep
        if preparation:
            for ff in self.FORM_FACTORS:
                if ff in preparation.lower() and not form_factor:
                    form_factor = ff
                    break

        # Normalize ingredient name
        name = name_part.strip()
        name_normalized = self._normalize_ingredient_name(name)

        # Build notes from parenthetical content that wasn't used
        notes = None
        unused_parens = [p for p in paren_contents if not any(c.isdigit() for c in p)]
        if unused_parens:
            notes = "; ".join(unused_parens)

        return ParsedIngredient(
            original_text=original,
            quantity=quantity,
            quantity_max=quantity_max,
            unit=unit,
            unit_normalized=unit_normalized,
            name=name,
            name_normalized=name_normalized,
            preparation=preparation,
            form_factor=form_factor,
            notes=notes,
            optional=optional,
        )

    def _parse_quantity(self, text: str) -> Optional[float]:
        """Parse a quantity string into a float."""
        if not text:
            return None

        text = text.strip()

        try:
            # Handle mixed numbers like "1 1/2"
            parts = text.split()
            if len(parts) == 2 and "/" in parts[1]:
                whole = float(parts[0])
                frac = float(Fraction(parts[1]))
                return whole + frac

            # Handle fractions like "1/2"
            if "/" in text:
                return float(Fraction(text))

            # Handle decimals and integers
            return float(text)
        except (ValueError, ZeroDivisionError):
            return None

    def _normalize_ingredient_name(self, name: str) -> str:
        """Normalize an ingredient name for matching."""
        # Lowercase
        normalized = name.lower().strip()

        # Remove leading "of" (e.g., "of butter" -> "butter")
        if normalized.startswith("of "):
            normalized = normalized[3:]

        # Check for known normalizations
        if normalized in self.INGREDIENT_NORMALIZATIONS:
            return self.INGREDIENT_NORMALIZATIONS[normalized]

        # Basic cleanup
        # Remove trailing 's' for basic plurals (but be careful)
        # This is a simple heuristic; a proper solution would use a lemmatizer

        return normalized


def parse_ingredient(text: str) -> ParsedIngredient:
    """
    Convenience function to parse a single ingredient.

    Args:
        text: The ingredient string

    Returns:
        A ParsedIngredient object
    """
    parser = IngredientParser()
    return parser.parse(text)
