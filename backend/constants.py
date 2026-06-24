"""Shared constants for Uganda Pharma Dashboard."""

# Uganda Shillings to EUR conversion rate
UGX_TO_EUR = 3800.0

# US Dollar to EUR conversion rate (fixed, matches UGX_TO_EUR approach)
USD_TO_EUR = 0.85


def ugx_to_eur(amount: float) -> float:
    return amount / UGX_TO_EUR


def usd_to_eur(amount: float) -> float:
    return amount * USD_TO_EUR

# Uganda sales file has no distributor columns — single source per product
DISTRIBUTORS = []

# IDs excluded from field-MR performance tables
_NON_MR_IDS: set = set()

CLR_GREEN  = "#00C49A"
CLR_RED    = "#FF4C61"
CLR_BLUE   = "#4C9FFF"
CLR_ORANGE = "#FF9F40"
CLR_PURPLE = "#B57BFF"
CLR_TEAL   = "#26C6DA"
CLR_YELLOW = "#FFD166"

DIST_COLORS: dict = {}
