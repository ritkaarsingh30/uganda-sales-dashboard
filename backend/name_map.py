"""
Name normalisation for Uganda Dashboard.
EXACT-MATCH ONLY — data is system-generated, names are consistent.
Unknown values pass through as raw strings (never replaced with 'UNKNOWN').
"""

# ── Delegates / MRs ──────────────────────────────────────────────────────────
MR_CANONICAL: dict[str, str] = {
    "MBALANGU GEORGE": "MR_001",
    "GEORGE":          "MR_001",
    "AISHA S":         "MR_002",
    "AISHA":           "MR_002",
    "SIMON NDUGGU":    "MR_003",
    "SIMON":           "MR_003",
    "AKANKUNDA RACHELLE": "MR_004",
    "RACHEAL":         "MR_004",
    "RACHELLE":        "MR_004",
    "OKODI DANIEL":    "MR_005",
    "DANIEL":          "MR_005",
    "DENIAL":          "MR_005",
    "SARVESH MALLAH":  "MR_006",
    "SARVESH":         "MR_006",
}

MR_DISPLAY: dict[str, str] = {
    "MR_001": "MBALANGU GEORGE",
    "MR_002": "Aisha S",
    "MR_003": "Simon Nduggu",
    "MR_004": "AKANKUNDA Rachelle",
    "MR_005": "Okodi Daniel",
    "MR_006": "Sarvesh Mallah",
}

MR_SHORT: dict[str, str] = {
    "MR_001": "GEORGE",
    "MR_002": "AISHA",
    "MR_003": "SIMON",
    "MR_004": "RACHELLE",
    "MR_005": "DANIEL",
    "MR_006": "SARVESH",
}

MR_JOINT_MAP: dict[str, list[str]] = {}


def normalize_mr(raw: str) -> str:
    if not raw or (isinstance(raw, float)):
        return ""
    s = str(raw).strip().upper()
    for pattern, ids in MR_JOINT_MAP.items():
        if pattern.upper() in s or s in pattern.upper():
            return ",".join(ids)
    return MR_CANONICAL.get(s, raw)


def mr_display_name(mr_id: str) -> str:
    if "," in str(mr_id):
        return " + ".join(MR_DISPLAY.get(i.strip(), i.strip()) for i in mr_id.split(","))
    return MR_DISPLAY.get(mr_id, mr_id)


def mr_short_name(mr_id: str) -> str:
    return MR_SHORT.get(mr_id, mr_display_name(mr_id).split()[0] if mr_display_name(mr_id) else mr_id)


# ── Products ─────────────────────────────────────────────────────────────────
PRODUCT_CANONICAL: dict[str, str] = {
    "BIO C":          "P_001",
    "BIOC":           "P_001",
    "BIO CZN":        "P_002",
    "BIOCZN":         "P_002",
    "CALD-K2":        "P_003",
    "CALDK2":         "P_003",
    "CALD K2":        "P_003",
    "BIO RENO":       "P_004",
    "BIORENO":        "P_004",
    "BIO KETON":      "P_005",
    "BIOKETON":       "P_005",
    "BIO JOINTS":     "P_006",
    "BIOJOINTS":      "P_006",
    "BIO MAN":        "P_007",
    "BIOMAN":         "P_007",
    "BIO VISION":     "P_008",
    "BIOVISION":      "P_008",
    "BIO MEGA":       "P_009",
    "BIOMEGA":        "P_009",
    "BIO NEO":        "P_010",
    "BIONEO":         "P_010",
    "BIO TIC":        "P_011",
    "BIOTIC":         "P_011",
    "BIO MOBI":       "P_012",
    "BIOM":           "P_012",
    "BIO PROSTATE":   "P_013",
    "BIOPROSTATE":    "P_013",
    "BIO PEA FORTE":  "P_014",
    "BIOPEAFORT":     "P_014",
    "BIOPEA":         "P_014",
    "BIO PEA":        "P_014",
    "CURCUMIN 95":    "P_015",
    "CURCUMIN95":     "P_015",
    "COQ10":          "P_016",
    "COQ 10":         "P_016",
    "BIO NERV":       "P_017",
    "BIONERV":        "P_017",
    "BIO LIVER":      "P_018",
    "BIOLIVER":       "P_018",
    "BIOMAX HP":      "P_019",
    "BIO MAX HP":     "P_019",
    "LINAZEE-M 500":  "P_020",
    "LINAZEE M 500":  "P_020",
    "LINAZEE-5":      "P_021",
    "LINAZEE 5":      "P_021",
    "BIO MAX":        "P_019",
}

PRODUCT_DISPLAY: dict[str, str] = {
    "P_001": "Bio C",
    "P_002": "Bio CZN",
    "P_003": "CALD-K2",
    "P_004": "Bio Reno",
    "P_005": "Bio Keton",
    "P_006": "Bio Joints",
    "P_007": "Bio Man",
    "P_008": "Bio Vision",
    "P_009": "Bio Mega",
    "P_010": "Bio Neo",
    "P_011": "Bio Tic",
    "P_012": "Bio Mobi",
    "P_013": "Bio Prostate",
    "P_014": "Bio PEA Forte",
    "P_015": "Curcumin 95",
    "P_016": "CoQ10",
    "P_017": "Bio Nerv",
    "P_018": "Bio Liver",
    "P_019": "BioMax HP",
    "P_020": "Linazee-M 500",
    "P_021": "Linazee-5",
}

# All products are tablets
PRODUCT_CATEGORIES: dict[str, str] = {pid: "TABLET" for pid in PRODUCT_DISPLAY}


def normalize_product(raw: str) -> str:
    if not raw or (isinstance(raw, float)):
        return ""
    s = str(raw).strip().upper()
    return PRODUCT_CANONICAL.get(s, raw)


def product_display_name(product_id: str) -> str:
    return PRODUCT_DISPLAY.get(product_id, product_id)


def product_category(product_id: str) -> str:
    return PRODUCT_CATEGORIES.get(product_id, "TABLET")


def parse_multi_products(raw_str: str) -> str:
    if not raw_str:
        return ""
    parts = [p.strip() for p in str(raw_str).replace(",", "/").split("/") if p.strip()]
    names = [product_display_name(normalize_product(p)) for p in parts]
    return " / ".join(n for n in names if n)


# ── Activities ────────────────────────────────────────────────────────────────
# Raw "Activity Type" values are already clean (CME, Campaign, Motivation, Non CASH);
# only casing varies, which normalize_activity's upper() handles. No remap needed yet.
ACTIVITY_CANONICAL: dict[str, str] = {}
ACTIVITY_DISPLAY: dict[str, str] = {}


def normalize_activity(raw: str) -> str:
    if not raw or (isinstance(raw, float)):
        return ""
    s = str(raw).strip().upper()
    return ACTIVITY_CANONICAL.get(s, raw)


def activity_display_name(act_id: str) -> str:
    return ACTIVITY_DISPLAY.get(act_id, act_id)


# ── Territories ───────────────────────────────────────────────────────────────
TERRITORY_CANONICAL: dict[str, str] = {
    "KAMPALA":  "ZONE_KAMPALA",
    "KRIDDU":   "ZONE_KIRUDDU",
    "KIRUDDU":  "ZONE_KIRUDDU",
    "MENGO":    "ZONE_MENGO",
    "MBARARA":  "ZONE_MBARARA",
    "MABRARA":  "ZONE_MBARARA",
}

TERRITORY_DISPLAY: dict[str, str] = {
    "ZONE_KAMPALA":  "Kampala",
    "ZONE_KIRUDDU":  "Kiruddu",
    "ZONE_MENGO":    "Mengo",
    "ZONE_MBARARA":  "Mbarara",
}


def normalize_territory(raw: str) -> str:
    if not raw or (isinstance(raw, float)):
        return ""
    s = str(raw).strip().upper()
    return TERRITORY_CANONICAL.get(s, str(raw).strip().title())


def territory_display_name(zone_id: str) -> str:
    return TERRITORY_DISPLAY.get(zone_id, zone_id)


# ── Doctors ───────────────────────────────────────────────────────────────────
def normalize_doctor(raw: str) -> str:
    if not raw or (isinstance(raw, float)):
        return ""
    return str(raw).strip().title()
