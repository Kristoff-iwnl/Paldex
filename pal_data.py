import json
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

work_emojis = {
    "Kindling": "🔥",
    "Watering": "💧",
    "Planting": "🌱",
    "Generating Electricity": "⚡",
    "Handiwork": "🔨",
    "Gathering": "🧺",
    "Lumbering": "🌲",
    "Mining": "⛏️",
    "Medicine Production": "💊",
    "Cooling": "❄️",
    "Transporting": "📦",
    "Farming": "🌾"
}

# The data files are loaded once when main.py imports this module. The lookup
# functions below then supply related pieces of data for the searched Pal.

with open(BASE_DIR / "pals_combat.json", "r", encoding="utf-8") as file:
    combat_data = json.load(file)

with open(BASE_DIR / "habitat_locations.json", "r", encoding="utf-8") as file:
    habitat_data = json.load(file)


def find_pal(pal_name):
    for pal in combat_data:
        if pal['name'].lower() == pal_name.lower():
            return pal
    return None 

with open(BASE_DIR / "palworld_pals.csv", "r", encoding="utf-8") as file:
    work_data = list(csv.DictReader(file))

with open(BASE_DIR / "icons.json", "r", encoding="utf-8") as file:
    icon_data = json.load(file)


def find_pal_icon(pal_name):
    pals = icon_data.get("pals", icon_data)

    for name, image_url in pals.items():
        if name.lower() == pal_name.lower():
            return image_url

    return None


def find_item_icon(item_name):
    items = icon_data.get("items", {})
    return items.get(item_name)

def get_drop_icons(drops):
    # main.py uses this paired data to display each drop name and, when one is
    # available, its matching icon from icons.json.

    return [
        {
            "name": drop,
            "icon": find_item_icon(drop),
        }
        for drop in drops
    ]

def find_work_data(pal_name):
    for pal in work_data:
        if pal['Name'].lower() == pal_name.lower():
            return pal
        
    return None

def get_work_suitability(work_data):
    if work_data is None:
        return []

    suitability = []

    for key, value in work_data.items():
        if key not in ["Name", "Number"] and value.isdigit() and int(value) > 0:
            emoji = work_emojis.get(key, "⚙️")
            suitability.append(f"{emoji} {key}: Lv. {value}")

    return suitability

with open(BASE_DIR / "pal_locations.json", "r", encoding="utf-8") as file:
    location_data = json.load(file)


def find_location_data(pal_name):
    for name in location_data["pals"]:
        if name.lower() == pal_name.lower():
            return location_data["pals"][name]

    return None

def find_habitat_coordinates(location_name):
    for name, data in habitat_data.items():
        if name.lower() == location_name.lower():
            return data

    return None

def format_other_sources(other_sources):
    formatted_sources = []

    for source in other_sources:
        source_lower = source.lower()

        if source_lower.startswith("dungeon:"):
            category = "🏰 Dungeon"
            details = source.split(":", 1)[1].strip()

        elif source_lower.startswith("dungeon ("):
            category = "🏰 Dungeon"
            details = source

        elif source_lower.startswith("dungeon loot egg"):
            category = "🥚 Dungeon Egg"
            details = source.replace("dungeon loot egg", "").strip()

        elif source_lower.startswith("caged pal"):
            category = "🔒 Captive Pal"
            details = source

        elif source_lower.startswith("enemy camps"):
            category = "⚔️ Enemy Camp"
            details = source

        elif source_lower.startswith("fishing"):
            category = "🎣 Fishing"
            details = source

        elif source_lower.startswith("incident/outbreak events"):
            category = "⚠️ Outbreak"
            details = source

        elif source_lower.startswith("pal recruiter"):
            category = "🚶 Pal Recruiter"
            details = source

        elif source_lower in ["breeding", "breeding combo", "obtainable via breeding"]:
            category = "🥚 Breeding"
            details = source

        elif source_lower == "raid-boss reward":
            category = "👑 Raid Reward"
            details = source

        elif source_lower.startswith("story final boss"):
            category = "👑 Story Boss"
            details = source

        elif source_lower.startswith("roams all areas"):
            category = "🌎 Rare Wandering"
            details = source

        elif source_lower.startswith("no regular wild spawn"):
            category = "ℹ️ Special"
            details = source

        elif source_lower.startswith("not obtainable"):
            category = "🚫 Unobtainable"
            details = source

        else:
            category = "ℹ️ Other"
            details = source

        formatted_sources.append(f"{category}: {details}")

    return formatted_sources

def normalize_location_name(location):
    # Region names come from more than one data file. This makes known spelling
    # differences match before habitat coordinates are looked up.

    location = location.strip()

    replacements = {
        "TwilightDunes": "Twilight Dunes",
    }

    return replacements.get(location, location)

def get_location_info(location_data):

    if location_data is None:
        return {}

    day_night = location_data.get("day_night")

    if day_night == "both":
        day_night = "Both"
    elif day_night == "day":
        day_night = "Day"
    elif day_night == "night":
        day_night = "Night"

    regions = location_data.get("regions", [])
    locations = location_data.get("alpha_locations", [])
    egg_types = location_data.get("egg_types", [])
    other_sources = location_data.get("other_sources", [])

    clean_locations = []
    habitat_coordinates = []

    # Region values can include level text that is not part of the habitat
    # name. Remove it before looking up habitat coordinates.

    for region in regions:
        region = normalize_location_name(region)

        # Remove level information such as [Lv. 80].

        if "[" in region:
            region = region.split("[", 1)[0].strip()

        if region and region not in clean_locations:
            clean_locations.append(region)

        habitat = find_habitat_coordinates(region)

        if habitat:
            habitat_coordinates.append({
                "location": region,
                "x": habitat.get("x"),
                "y": habitat.get("y"),
                "confidence": habitat.get("confidence")
            })


    for location_entry in locations:

        if " - " in location_entry:
            alpha_info, location_part = location_entry.split(" - ", 1)

            if "(Lv. " in alpha_info:
                level = alpha_info.split("(Lv. ", 1)[1].replace(")", "")
            else:
                level = "Unknown"
        else:
            location_part = location_entry
            level = "Unknown"

        # Alpha entries can list places with commas, but coordinates also use
        # commas. Track parentheses so coordinate commas do not split locations.

        individual_locations = []
        current_location = ""
        parentheses_depth = 0

        for character in location_part:
            if character == "(":
                parentheses_depth += 1

            elif character == ")":
                parentheses_depth -= 1

            if character == "," and parentheses_depth == 0:
                if current_location.strip():
                    individual_locations.append(current_location.strip())
                current_location = ""
            else:
                current_location += character

        if current_location.strip():
            individual_locations.append(current_location.strip())

        for location in individual_locations:

            # The source coordinates identify the encounter, while the habitat
            # data file supplies the coordinates displayed in the UI.

            if "(" in location and ")" in location:
                location = location.split("(", 1)[0].strip()

            location = normalize_location_name(location)

            # Avoid showing the same location more than once.

            display_location = f"{location} - Lv. {level}"

            if display_location not in clean_locations:
                clean_locations.append(display_location)

            # Look up habitat coordinates for this individual location.

            habitat = find_habitat_coordinates(location)

            if habitat:
                habitat_coordinates.append({
                    "location": location,
                    "x": habitat.get("x"),
                    "y": habitat.get("y"),
                    "confidence": habitat.get("confidence")
                })

    other_sources = format_other_sources(other_sources)

    return {
        "day_night": day_night,
        "locations": clean_locations,
        "egg_types": egg_types,
        "other_sources": other_sources,
        "habitat_coordinates": habitat_coordinates
    }

