MAP_SIZE = 8192

MIN_X = -1099401
MAX_X = 349385
MIN_Y = -724397
MAX_Y = 724389


locations = {
    "No. 1 Wildlife Sanctuary": (-344, 270),
    "Twilight Dunes": (-124, -100),
    "Foot of the Astral Mountains": (-96, 197),
}


def map_to_pixel(map_x, map_y):

    # Convert PalDB map coordinates back into world coordinates
    world_y = map_x * 459 + 158000
    world_x = map_y * 459 - 123888

    # Convert world coordinates to normalized map position
    u = (world_y - MIN_Y) / (MAX_Y - MIN_Y)
    v = 1 - (world_x - MIN_X) / (MAX_X - MIN_X)

    # Convert normalized position to pixels
    pixel_x = (1 - v) * MAP_SIZE
    pixel_y = u * MAP_SIZE

    return round(pixel_x), round(pixel_y)


for name, (map_x, map_y) in locations.items():

    pixel_x, pixel_y = map_to_pixel(map_x, map_y)

    print(
        f"{name}: "
        f"map=({map_x}, {map_y}) "
        f"pixel=({pixel_x}, {pixel_y})"
    )