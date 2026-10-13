"""World Tree alpha spots, added by hand.

The World Tree is a separate map with its own coordinates. Eight Pals have an
alpha (boss) spot there, and pal_locations.json only stores them in an older
frame, for example Aegidron at (-59, 756). These are the in-game numbers instead.

Source: PinDrop's alpha list, which publishes marker data taken from paldb.cc.
Check: a straight-line conversion of the pal_locations.json numbers (about 2.91
times larger, then shifted) lands within 1.2 game units of every spot below, so
both sources describe the same places.

Celesdir has no spot of its own in the sources. In pal_locations.json it has the
same coordinates as Celesdir Noct (-60, 778), so it is given Noct's spot here.
That is an inference from your data, not something PalDB states.

To add or fix a spot, edit this table. x and y are the in-game map coordinates.
"""

WORLD_TREE_SPOTS = {
    "Whalaska Ignis": {"area": "Whimsical Wisteria Grove", "x": -1611, "y": 1417, "level": 74},
    "Dualith":        {"area": "Alluvion Lakefront",       "x": -1710, "y": 1397, "level": 75},
    "Moldron Cryst":  {"area": "Abandoned Laboratory",     "x": -1942, "y": 1515, "level": 78},
    "Renjishi":       {"area": "Corroded Hollow",          "x": -1590, "y": 1579, "level": 78},
    "Mycora":         {"area": "Spore Cloister",           "x": -1857, "y": 1268, "level": 78},
    "Aegidron":       {"area": "Lacrymal Shoal",           "x": -1925, "y": 1341, "level": 79},
    "Celesdir Noct":  {"area": "Within the Seal",          "x": -1928, "y": 1403, "level": 79},
    "Celesdir":       {"area": "Within the Seal",          "x": -1928, "y": 1403, "level": 79},
}
