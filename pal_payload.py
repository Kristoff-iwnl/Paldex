"""Turn one Pal's data into a plain dictionary for the web page.

main.py gets the Pal from pal_data.py (unchanged) and hands it here. Nothing in
this file needs Qt, so it can be tested on its own.
"""
from map_utils import map_to_fraction, tree_to_fraction
from tree_spots import WORLD_TREE_SPOTS

# (label shown on the page, key in pals_combat.json)
STAT_FIELDS = [
    ("HP", "hp"),
    ("Melee Attack", "melee_attack"),
    ("Shot Attack", "shot_attack"),
    ("Defense", "defense"),
    ("Support", "support"),
    ("Stamina", "stamina"),
]


def compute_stat_max(combat_data):
    """Highest value of each stat across all Pals, so bars can be scaled."""
    return {
        key: max((pal.get(key) or 0) for pal in combat_data) or 1
        for _, key in STAT_FIELDS
    }


def parse_work(text):
    """Split '🔥 Kindling: Lv. 2' (made by pal_data.py) into its parts."""
    try:
        emoji, rest = text.split(" ", 1)
        name, level = rest.rsplit(": Lv. ", 1)
        return {"emoji": emoji, "name": name, "level": int(level)}
    except ValueError:
        return None


def tree_points_for(pal_name):
    """World Tree alpha spot for this Pal (from tree_spots.py), as a list of 0 or 1 points."""
    spot = WORLD_TREE_SPOTS.get(pal_name)
    if not spot:
        return []
    point = {
        "label": "Alpha " + pal_name + " (Lv. " + str(spot["level"]) + ") - " + spot["area"],
        "x": spot["x"], "y": spot["y"], "u": None, "v": None,
    }
    fraction = tree_to_fraction(spot["x"], spot["y"])
    if fraction:
        point["u"], point["v"] = fraction
    return [point]


def build_pal_payload(pal_data, image_to_data_url, stat_max):
    """Collect everything the page shows into one JSON-friendly dictionary.

    pal_data is the dictionary from Paldex.get_pal_data(). image_to_data_url is
    a function that turns an image URL into text the page can display.
    """
    location = pal_data.get("location") or {}

    # Only habitats with real coordinates can be pinned on the map.
    habitat = []
    unmapped = []
    for spot in location.get("habitat_coordinates", []):
        x, y = spot.get("x"), spot.get("y")
        if x is None or y is None:
            unmapped.append(spot["location"])
            continue
        u, v = map_to_fraction(x, y)
        habitat.append({"location": spot["location"], "x": x, "y": y, "u": u, "v": v})

    work = [parse_work(text) for text in pal_data.get("work", [])]

    return {
        "name": pal_data["name"],
        "number": pal_data.get("paldeck_number"),
        "rarity": pal_data.get("rarity"),
        "size": pal_data.get("size"),
        "nocturnal": bool(pal_data.get("nocturnal")),
        "mount": pal_data.get("mount_type") if pal_data.get("ride") else None,
        "elements": pal_data.get("elements", []),
        "image": image_to_data_url(pal_data.get("icon")),
        "skill": {
            "name": (pal_data.get("partner_skill") or {}).get("name", ""),
            "effect": (pal_data.get("partner_skill") or {}).get("effect", ""),
        },
        "stats": [
            {"label": label, "value": pal_data.get(key) or 0, "max": stat_max[key]}
            for label, key in STAT_FIELDS
        ],
        "work": [w for w in work if w],
        "drops": [
            {"name": drop["name"], "icon": image_to_data_url(drop["icon"])}
            for drop in pal_data.get("drop_icons", [])
        ],
        "day_night": location.get("day_night"),
        "alpha": location.get("locations", []),
        "eggs": location.get("egg_types", []),
        "sources": location.get("other_sources", []),
        "habitat": habitat,
        "unmapped": unmapped,
        "tree_points": tree_points_for(pal_data["name"]),
    }
