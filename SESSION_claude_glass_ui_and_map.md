# Session: Claude, glass interface and in-app map

New session, separate from the ChatGPT and Codex sessions. Project: Paldex (PySide6 desktop app for Palworld).

## Goal
Make the app look premium (black, glossy glass, animation, blur), add stat bars, add a habitat map inside the app, keep the existing Python code as intact as possible, and prepare for a portfolio.

## What was decided
- Keep PySide6 for the window. Replace the widget-based interface with a web page (HTML, CSS, JavaScript) shown inside the window with `QWebEngineView`.
- Python stays responsible for data and images. The page only displays.
- Glass look: frosted cards (`backdrop-filter`), a slow-moving blurred background, and colours that follow the Pal's first element.

## Files
| File | Status | What it is |
|---|---|---|
| `main.py` | Changed | Window now hosts the web page. Kept: image cache, `get_cached_image`, `get_pal_data`, `show_map`, the `pal_names` list. |
| `main_classic.py` | New (copy) | Your previous widget-based `main.py`, untouched, as a fallback. Run it with `python main_classic.py`. |
| `pal_payload.py` | New | Packs one Pal's data into a dictionary for the page. No Qt in it, so it can be tested alone. |
| `tree_spots.py` | New | Hand-entered World Tree alpha spots for the 8 Pals, in in-game coordinates. |
| `map_utils.py` | New | Converts map coordinates to a position on the map picture. Has `OFFSET_U` / `OFFSET_V` to nudge pins. |
| `web/index.html` | New | The whole interface: layout, glass styling, animation, search, map. |
| `web/landmask.js` | New | Coarse grid of the area drawn on the world map, used to mark pins that fall outside it. |
| `web/world_map.webp` | New | Web-sized copy of `maps/T_WorldMap.png` (4096 px, under 1 MB instead of 27 MB). |
| `web/tree_map.webp` | New | Web-sized copy of `maps/T_TreeMap.png` (3072 px, under 1 MB instead of 39 MB). |
| `assets/icon.ico`, `icon.png` | New | App icon. |
| `Paldex.spec` | Changed | Bundles `web` and `assets` instead of `maps`; adds the exe icon. |
| `requirements.txt` | New | `PySide6`, `requests`. |

## What did NOT change
`pal_data.py`, all JSON/CSV data files, the image download and cache logic, the PalDB link logic, and the data lookups. `pal_database.py`, `test.py`, `test_map_coords.py`, `HABITAT_TASK.md` and `habitat_validation.txt` were not touched or used.

## How it works
```
page (JavaScript)  --asks-->  PalBridge (Python slots)  -->  get_pal_data()  -->  pal_data.py
page  <--JSON text--  build_pal_payload()  <--  image_to_data_url()  <--  get_cached_image()
```
1. The page starts and connects to Python through `QWebChannel`.
2. It asks for all Pal names (`getPalNames`) for the suggestion list.
3. On search it calls `getPal(name)`. Python runs the same lookups as before, builds a dictionary, and returns it as JSON text.
4. Images travel as `data:` URLs (the picture encoded as text), read from the same `image_cache` folder.
5. "Open PalDB Map" calls `openPalDB`, which runs the existing `show_map()`.
6. Recent searches and favourites are saved by Python in `paldex_prefs.json`.

## Concepts worth knowing
- **QWebChannel and `@Slot`**: a Python method marked `@Slot` can be called from JavaScript.
- **JSON as the hand-over format**: both languages can read it.
- **QSS vs CSS**: the old interface used Qt stylesheets (QSS, limited). Web CSS can do blur, gradients and animation.
- **Fractions instead of pixels** for the map: 0 to 1 works at any image size.

## Behaviour differences from the old interface
- Pal name shows as stored in the data (`Chillet Ignis`), not `.capitalize()`d (`Chillet ignis`).
- A Pal with no location record no longer risks a `KeyError`; the sections show "No ... data available".
- Suggestions come from the page (all names, filtered as you type) instead of `QCompleter`.
- New: stat bars, Paldeck number, rarity, size, mount and nocturnal tags, recent searches, favourites, `/` to focus search.
- New: Habitat map with pan, zoom, and pins.

## Map: two maps
Palworld has two separate maps: the world map and the World Tree map. The first version of this session used only `T_TreeMap.png`, which is why pins looked wrong. After adding `T_WorldMap.png`:
- World map: confirmed. The conversion constants from `test_map_coords.py` fit the picture. Mount Obsidian lands on the lava island, the Astral Mountains on the snow island, Dancing Sakura Shrine and Sakurajima - Northern Rock Field on Sakurajima, and 62 of the 67 mapped habitats sit on island terrain. The only real fix to your old maths was the axes: east-west runs across the picture and north-south runs up it.
- World Tree map: its own coordinate range, and its picture limits are not known. Only 8 Pals have World Tree coordinates in the data (their alpha spots). Pins stay off until `TREE_MIN_X`, `TREE_MAX_X`, `TREE_MIN_Y`, `TREE_MAX_Y` in `map_utils.py` are filled in. Until then the page shows the picture and lists the coordinates.
- "The World Tree" as a habitat has no coordinates in the data at all, so it appears as a note under the map.
- Habitat pins are representative points of regions, not exact spawn spots.
- To check alignment yourself: run with `PALDEX_MAP_DEBUG=1` (PowerShell: `$env:PALDEX_MAP_DEBUG=1; python main.py`) to see every known habitat as a small grey pin.

## World Tree alpha spots (added by hand)
Eight Pals have a World Tree spot: Aegidron, Celesdir, Celesdir Noct, Dualith, Moldron Cryst, Mycora, Renjishi and Whalaska Ignis. `pal_locations.json` stores their coordinates in an older frame (for example Aegidron at (-59, 756)). `tree_spots.py` holds the in-game numbers instead (Aegidron at (-1925, 1341), Lacrymal Shoal).
- Source: PinDrop's alpha list, which publishes marker data from paldb.cc. paldb.cc itself could not be opened from here.
- Check: a straight-line conversion of your file's numbers (about 2.91 times larger, then shifted) matches all seven published spots to within 1.2 units, so the two sources agree.
- Celesdir is the exception. No source gives it a spot, but your file gives it the same coordinates as Celesdir Noct, so it uses Noct's spot. That is an inference.
- The page lists these spots in the World Tree tab. Pins still need the map's edges in `map_utils.py` (not known yet).

## Verification
- Done: payloads built for all 299 Pals from the real data files without errors; the page was run in headless Chromium with a stand-in for Python, covering search, suggestions, theme colours, stat bars, drops, favourites, recents, not-found message, clear, zoom and pan, and window resize.
- Done for the map: pins checked against the world map picture by eye and by measuring how many land on island terrain.
- Not done: running the real PySide6 window, `QWebChannel`, real image downloads, building the .exe, and calibrating the World Tree map.

## If something goes wrong
- Page says "Preview mode": the Qt script did not load. Check that `PySide6` is installed (it includes WebEngine) and that you started `main.py`.
- Blank window: set `QTWEBENGINE_REMOTE_DEBUGGING=9222`, run the app, and open `http://localhost:9222` in Chrome to see the page's console.
- Want the old look back: run `main_classic.py`.

## Polish after the first run
You ran the app and sent screenshots. Findings and fixes:
- The search suggestion list was covered by the "No Pal selected" card. Cause: each glass card has its own stacking layer (from `backdrop-filter`), so the dropdown could not rise above the next card. Fix: the search card now sits above the results (`.searchcard`).
- Knocklem Ignis showed odd map positions. Its data has Bicornis Islet (far south), Foot of the World Tree (north edge), and The World Tree (no coordinates at all). The map picture was the wrong one (World Tree map instead of the world map), which is fixed above. Changes kept: the map can zoom out to show the whole picture; pins outside the drawn area are dashed with a note; locations with no coordinates are listed under the map.
- The map view is taller on bigger windows.

## Before publishing
- The Clear button now also empties the recent searches (favourites are kept). Normal searches still add to the recents list.
- Until the World Tree map is calibrated, there is no World Tree tab or picture. Its spots are listed as text.
- `.gitignore` leaves out `image_cache/`, `paldex_prefs.json`, `maps/` (the big originals), `build/`, `dist/` and `.claude/`.
- `README.md` expects a screenshot at `docs/screenshot.png`.

## Next steps (not done)
- Calibrate the World Tree map (needs 2 or 3 of the spots in `tree_spots.py` and where they sit on `T_TreeMap.png`). Then fill in the four `TREE_` numbers in `map_utils.py` and the tab and pins return.
- Rebuild the .exe: `pyinstaller Paldex.spec` (the WebEngine will make it much larger).
- Put the project on GitHub (set aside for now).
- Add earlier ChatGPT/Codex session notes to the same folder so the history stays together.
