"""
taxonomy.py
-----------
The single source of truth for your coding scheme.

Every other script imports from here. If you change a bucket name,
change it ONCE in this file and the whole pipeline stays consistent.

This is the v0 map from your metric decomposition. After you read
~100 raw comments, come back and edit this file - that edit IS the
"v0 -> v1" revision you will show in your deck.
"""

# ---------------------------------------------------------------
# The 11 buckets. Keys are machine-readable, values are for display.
# ---------------------------------------------------------------
BUCKETS = {
    "price_waiting":              "Waiting for price drop / sale",
    "fit_size_uncertainty":       "Unsure about fit or size",
    "in_app_comparison":          "Comparing items within the app",
    "cross_platform_comparison":  "Comparing against other websites",
    "occasion_pending":           "Saving for a future occasion",
    "gifting":                    "Buying for someone else",
    "styling_uncertainty":        "Unsure what to pair it with",
    "quality_authenticity_doubt": "Doubts about quality / authenticity",
    "out_of_stock":               "Item or size unavailable",
    "window_shopping":            "Browsing with no purchase intent",
    "other":                      "Other / does not fit a bucket",
}

# Buckets your no-monetary-incentive constraint puts OUT OF SCOPE.
# You still MEASURE these - you just cannot solve them.
# This lets you say: "price is X% of blockers but out of scope,
# so the addressable pool is the remaining Y%."
OUT_OF_SCOPE = []

# Buckets that represent no real intent - not convertible, by design.
NO_INTENT = ["window_shopping"]

# ---------------------------------------------------------------
# Secondary fields
# ---------------------------------------------------------------
UNCERTAINTY_TYPES = [
    "fit", "quality", "styling", "price", "availability", "delivery_returns", "none",
]

EXTERNAL_CHANNELS = [
    "amazon", "flipkart", "ajio", "brand_website", "friend_family",
    "youtube", "instagram", "google_search", "none",
]

CONFIDENCE_LEVELS = ["high", "medium", "low"]


ALIASES = {
    "price": "Waiting for price drop / sale",
    "quality": "Doubts about quality / authenticity",
    "fit": "Unsure about fit or size",
    "styling": "Unsure what to pair it with",
    "availability": "Item or size unavailable",
    "delivery_returns": "Delivery & return friction",
    "none": "No explicit blocker",
    "uncertainty_type": "General uncertainty",
    "uncertainty": "General uncertainty",
}


def bucket_label(key: str) -> str:
    """Turn a machine key into a human label for charts."""
    if not key or key == "nan":
        return "Unspecified"
    if key in BUCKETS:
        return BUCKETS[key]
    if key in ALIASES:
        return ALIASES[key]
    return str(key).replace("_", " ").title()


def is_addressable(key: str) -> bool:
    """True if this blocker is something we are allowed to solve."""
    return key not in OUT_OF_SCOPE and key not in NO_INTENT and key != "other"
