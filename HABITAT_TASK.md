# Paldex Habitat Location Mapping Task

## Goal
Create a reliable dataset mapping every unique Palworld habitat/location name found in
`pal_locations.json` to a useful position on a Palworld world map.

The dataset will later be used by the PySide6 Paldex application.

## Source
- Inspect the ENTIRE `pal_locations.json` before generating anything.
- Do NOT modify existing application/source files.

## Output
Create `habitat_locations.json`.

Use this structure:

{
    "Volcanic Cavern": {
        "x": 123,
        "y": 456,
        "confidence": "high",
        "source": "...",
        "notes": "..."
    }
}

## Requirements

1. Extract every unique location/habitat name appearing in `pal_locations.json`.
2. Split combined locations into separate entries.
   Example: `Hillside Cavern, Isolated Island Cavern` -> two locations.
3. Ignore level ranges when identifying locations.
   `Hillside Cavern (Lv. 5-10)` and `Hillside Cavern (Lv. 10-13)` are one location.
4. Remove Pal/Alpha names and level information from location names.
5. Normalize names consistently while preserving the recognizable location name.
6. Find the corresponding position for each location on a Palworld map.
7. Prefer authoritative or well-established Palworld map/location data.
8. DO NOT invent or guess coordinates.
9. If a coordinate cannot be reliably determined, use `"confidence": "unknown"` and
   do not fabricate x/y values.
10. Record the source used to determine coordinates whenever possible.
11. Merge duplicate locations.
12. Validate that every location referenced by the source has an entry in the output.

## Accuracy Rules

Accuracy is more important than completeness.

If multiple credible sources disagree, do not silently choose one. Record the ambiguity
in `notes` and lower the confidence.

For large locations where only a representative point is available, use the most useful
representative point and explain that in `notes`.

## Validation

Also create `habitat_validation.txt` containing:

- Total unique locations found
- Total successfully mapped
- Total with unknown coordinates
- Duplicate locations merged
- Ambiguous locations
- Unresolved locations
- Locations whose names required normalization

List every unresolved or ambiguous location explicitly.

## Application Safety

Do NOT modify:
- `main.py`
- `pal_data.py`
- UI files
- `pals_combat.json`
- `pal_locations.json`
- `icons.json`
- any existing application code

This task is ONLY for generating and validating the habitat dataset.

## Final Deliverables

1. `habitat_locations.json`
2. `habitat_validation.txt`

Before finishing, verify the JSON is valid and every source location has either a
mapped entry or an explicit unknown/unresolved entry.
