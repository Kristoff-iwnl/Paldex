"""Turn PalDB map coordinates into positions on the map pictures.

The Pal data stores habitat spots as PalDB "map coordinates" (x, y). Those come
from the game's world coordinates with two flipped axes:

    map_x = (world_y - 158000) / 459
    map_y = (world_x + 123888) / 459

test_map_coords.py already did this maths in reverse. The function below keeps
the same constants but returns fractions (0 to 1) instead of pixels, so the same
answer works for any size of picture: 0 is the left/top edge, 1 is the
right/bottom edge.

Palworld has two maps. This file handles both:
  - the world map (web/world_map.webp, from maps/T_WorldMap.png): checked
    against the picture. Mount Obsidian lands on the lava island, the Astral
    Mountains on the snow island, and 62 of the 67 mapped habitats sit on land.
  - the World Tree map (web/tree_map.webp, from maps/T_TreeMap.png): its own
    separate map with its own coordinate range. Its limits are not known yet,
    so World Tree pins stay off until the four TREE_ numbers below are filled in.
"""
import os

# Set the environment variable PALDEX_MAP_DEBUG=1 to also show every known
# habitat as a small grey pin. Handy for lining the map up.
MAP_DEBUG = os.environ.get("PALDEX_MAP_DEBUG") == "1"

# ---------------- world map ----------------
# World limits covered by the world map picture (same numbers as test_map_coords.py).
WORLD_MIN_X = -1099401
WORLD_MAX_X = 349385
WORLD_MIN_Y = -724397
WORLD_MAX_Y = 724389

# Fine-tuning. Positive U moves every pin right, positive V moves every pin
# down. Values are fractions of the picture, so 0.01 is 1% of its width/height.
OFFSET_U = 0.0
OFFSET_V = 0.0


def map_to_fraction(map_x, map_y):
    """Return (u, v): the position on the world map as fractions from 0 to 1."""
    # Convert map coordinates back into world coordinates.
    world_y = map_x * 459 + 158000
    world_x = map_y * 459 - 123888

    # East-west (world_y) runs left to right on the picture, and north-south
    # (world_x) runs bottom to top, so the vertical value is flipped.
    u = (world_y - WORLD_MIN_Y) / (WORLD_MAX_Y - WORLD_MIN_Y)
    v = 1 - (world_x - WORLD_MIN_X) / (WORLD_MAX_X - WORLD_MIN_X)

    return u + OFFSET_U, v + OFFSET_V


# ---------------- World Tree map ----------------
# The picture's left/right/bottom/top edges, written in the same map
# coordinates the data uses (for example x -1900 to 100, y 700 to 1500).
# Leave as None until they are known; the page then shows the picture without pins.
TREE_MIN_X = None
TREE_MAX_X = None
TREE_MIN_Y = None
TREE_MAX_Y = None


def tree_to_fraction(map_x, map_y):
    """Return (u, v) on the World Tree map, or None while it is not calibrated."""
    if None in (TREE_MIN_X, TREE_MAX_X, TREE_MIN_Y, TREE_MAX_Y):
        return None
    u = (map_x - TREE_MIN_X) / (TREE_MAX_X - TREE_MIN_X)
    v = 1 - (map_y - TREE_MIN_Y) / (TREE_MAX_Y - TREE_MIN_Y)
    return u, v
