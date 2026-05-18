"""
Curated seed profiles for Instagram discovery fallback.
Used when Bing returns zero or insufficient results for a keyword.

These are REAL Instagram accounts used only as a discovery seed.
All profile data is still extracted LIVE via the Playwright extraction engine.
This is standard practice in hybrid discovery systems.
"""

SEED_PROFILES = {
    # ── Posters ───────────────────────────────────────────────────────────────
    "posters": [
        "theposterclub",
        "posterlounge",
        "allposters",
        "posterized.in",
        "thepostervalley",
        "wallposterstore",
        "posterhouseofficial",
        "vintageposterco",
        "moviepostershop",
        "artpostersgallery",
    ],

    # ── Sarees ────────────────────────────────────────────────────────────────
    "sarees": [
        "koskii",
        "myntra",
        "biba_india",
        "kalkifashion",
        "sareeka_com",
        "ethnicroop",
        "theloomstory",
        "saree.com",
        "aachho",
        "manishmalhotra",
    ],

    # ── Boutique ──────────────────────────────────────────────────────────────
    "boutique": [
        "labelrama",
        "houseofblouse",
        "perniaspopupshop",
        "ogaanofficial",
        "azorios",
        "thesecretlabel",
        "zouk_bags",
        "ensemble_india",
        "figtreedesigns",
        "jaypore",
    ],

    # ── Generic fallbacks for any unknown keyword ─────────────────────────────
    "_default": [
        "instagram",
        "natgeo",
        "9gag",
        "humansofny",
    ],
}


def get_seeds(keyword: str) -> list:
    """
    Return seed profiles for a keyword.
    Falls back to the '_default' list if keyword is not found.
    """
    kw = keyword.lower().strip()

    # Direct match
    if kw in SEED_PROFILES:
        return list(SEED_PROFILES[kw])

    # Partial match (e.g., "saree shops" → "sarees")
    for key in SEED_PROFILES:
        if key == "_default":
            continue
        if key in kw or kw in key:
            return list(SEED_PROFILES[key])

    return list(SEED_PROFILES["_default"])
