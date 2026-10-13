import sys
import os
import json
import base64
import ctypes
import hashlib
import webbrowser

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QObject, QUrl, Qt, Slot
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
import requests
from pal_data import combat_data, find_pal, find_work_data, get_work_suitability, find_location_data, get_location_info, find_pal_icon, get_drop_icons
from pal_data import habitat_data
from pal_payload import build_pal_payload, compute_stat_max
from map_utils import MAP_DEBUG, map_to_fraction

# Small file that remembers recent searches and favourites between sessions.
PREFS_FILE = "paldex_prefs.json"


def resource_path(relative_path):
    """Find a bundled file both when running as a script and as a built .exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


def style_title_bar(window):
    """Windows only: make the title bar dark with a cyan border.

    Fails silently on other systems or older Windows versions, where the
    normal title bar is used instead.
    """
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        dwm = ctypes.windll.dwmapi

        def set_attribute(attribute, value):
            data = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))

        set_attribute(20, 1)              # dark title bar (Windows 10 2004+ / 11)
        set_attribute(19, 1)              # same, for older Windows 10 builds
        set_attribute(35, 0x00000000)     # caption colour: black (Windows 11)
        set_attribute(36, 0x00FFFFFF)     # caption text: white (Windows 11)
        set_attribute(34, 0x00FFE000)     # window border: cyan, BGR order (Windows 11)
    except Exception:
        pass


class PalBridge(QObject):
    """The page (JavaScript) calls these methods to talk to Python.

    Each @Slot below is a function the web page is allowed to call. The page
    asks for a Pal, and Python answers with text (JSON) that the page can read.
    """

    def __init__(self, window):
        super().__init__(window)
        self.window = window

    @Slot(result=str)
    def getPalNames(self):
        return json.dumps(self.window.pal_names)

    @Slot(str, result=str)
    def getPal(self, name):
        return json.dumps(self.window.get_pal_payload(name))

    @Slot()
    def openPalDB(self):
        self.window.show_map()

    @Slot()
    def clearPal(self):
        self.window.current_pal = None

    @Slot(result=str)
    def loadPrefs(self):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as file:
                return file.read()
        except OSError:
            return "{}"

    @Slot(str)
    def savePrefs(self, text):
        try:
            json.loads(text)  # only save text that really is JSON
            with open(PREFS_FILE, "w", encoding="utf-8") as file:
                file.write(text)
        except (ValueError, OSError):
            pass


class Paldex(QMainWindow):
    def __init__(self):
        super().__init__()
        # Keep downloaded PalDB images locally so repeated searches do not need
        # another network request.
        self.image_cache_dir = "image_cache"
        os.makedirs(self.image_cache_dir, exist_ok=True)

        self.setWindowTitle("Paldex")
        self.resize(900, 780)
        self.setMinimumSize(560, 500)
        self.current_pal = None

        # Names for the page's suggestion list, and the highest value of each
        # stat so the stat bars can be drawn to scale.
        self.pal_names = sorted({pal["name"] for pal in combat_data}, key=str.casefold)
        self.stat_max = compute_stat_max(combat_data)

        # The interface is now a web page (web/index.html) shown inside the
        # window. QWebChannel is the link that lets the page call PalBridge.
        self.web_view = QWebEngineView(self)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web_view.page().setBackgroundColor(QColor("#000000"))
        self.bridge = PalBridge(self)
        self.channel = QWebChannel(self)
        self.channel.registerObject("paldex", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.load(QUrl.fromLocalFile(resource_path(os.path.join("web", "index.html"))))
        self.setCentralWidget(self.web_view)

    def get_cached_image(self, image_url):
        if not image_url:
            return None

        # A URL can contain filename-unfriendly characters. Hashing gives each
        # URL a safe, repeatable cache filename without changing the URL itself.

        filename = hashlib.md5(image_url.encode("utf-8")).hexdigest() + ".webp"
        cache_path = os.path.join(self.image_cache_dir, filename)

        # A cache hit avoids downloading the same image again. Verify that Qt
        # can read the file in case an earlier download was incomplete.

        if os.path.exists(cache_path):
            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                return pixmap

        # A cache miss downloads the image and saves it for future searches.
        # PalDB's CDN expects browser-like headers for image requests.

        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://paldb.cc/"}
        try:
            response = requests.get(image_url, headers=headers, timeout=5)
            if response.status_code == 200:
                with open(cache_path, "wb") as file:
                    file.write(response.content)
                pixmap = QPixmap()
                if pixmap.loadFromData(response.content):
                    return pixmap
        except requests.RequestException:
            pass
        return None

    def image_to_data_url(self, image_url):
        """Give the page an image as text it can display (a data: URL).

        This reuses get_cached_image() above, so downloading and caching work
        exactly as before. The page only receives the finished picture.
        """
        if self.get_cached_image(image_url) is None:
            return None
        filename = hashlib.md5(image_url.encode("utf-8")).hexdigest() + ".webp"
        try:
            with open(os.path.join(self.image_cache_dir, filename), "rb") as file:
                encoded = base64.b64encode(file.read()).decode("ascii")
        except OSError:
            return None
        return "data:image/webp;base64," + encoded

    def show_map(self):
        if not self.current_pal:
            return

        # PalDB uses underscores rather than spaces in its Pal page URLs.

        pal_name = self.current_pal["name"]
        webbrowser.open(f"https://paldb.cc/en/{pal_name.replace(' ', '_')}")

    def get_pal_data(self, pal_name):
        pal_data = find_pal(pal_name)
        if pal_data is None:
            return None
        # Add the related data that each UI row needs to the combat-data entry.

        pal_data["work"] = get_work_suitability(find_work_data(pal_name))
        pal_data["location"] = get_location_info(find_location_data(pal_name))
        pal_data["icon"] = find_pal_icon(pal_name)
        pal_data["drop_icons"] = get_drop_icons(pal_data.get("notable_drops", []))
        return pal_data

    def get_pal_payload(self, pal_name):
        """Look up one Pal and package it for the page (None if not found)."""
        pal_data = self.get_pal_data(pal_name)
        if pal_data is None:
            self.current_pal = None
            return None
        # Map button uses the successful result stored in current_pal.
        self.current_pal = pal_data
        payload = build_pal_payload(pal_data, self.image_to_data_url, self.stat_max)
        if MAP_DEBUG:
            payload["debug_points"] = self.debug_points()
        return payload

    def debug_points(self):
        # Every known habitat as a pin, to check the map lines up.
        points = []
        for name, spot in habitat_data.items():
            if spot.get("x") is None or spot.get("y") is None:
                continue
            u, v = map_to_fraction(spot["x"], spot["y"])
            points.append({"location": name, "x": spot["x"], "y": spot["y"], "u": u, "v": v})
        return points


if __name__ == "__main__":
    # Give the app its own identity so Windows shows our icon in the taskbar
    # instead of the generic Python one.
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("paldex.companion.app")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("Paldex")
    app.setWindowIcon(QIcon(resource_path(os.path.join("assets", "icon.ico"))))
    pal_dex = Paldex()
    pal_dex.show()
    style_title_bar(pal_dex)
    sys.exit(app.exec())
