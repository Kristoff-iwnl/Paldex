import sys
import os
import hashlib
import webbrowser

from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QCompleter, QLineEdit, QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import requests
from pal_data import combat_data, find_pal, find_work_data, get_work_suitability, find_location_data, get_location_info, find_pal_icon, get_drop_icons


# Colours for the element badges: (badge background, text colour).
ELEMENT_COLORS = {
    "neutral": ("#C9C9C9", "#000000"),
    "grass": ("#6BCB3C", "#000000"),
    "fire": ("#FF5A3C", "#000000"),
    "water": ("#3C9DFF", "#000000"),
    "electric": ("#FFD21F", "#000000"),
    "ice": ("#7DE3F4", "#000000"),
    "ground": ("#C08A4B", "#000000"),
    "dark": ("#8B5CF6", "#FFFFFF"),
    "dragon": ("#E0457B", "#FFFFFF"),
}


class Paldex(QMainWindow):
    def __init__(self):
        super().__init__()
        # Keep downloaded PalDB images locally so repeated searches do not need
        # another network request.
        self.image_cache_dir = "image_cache"
        os.makedirs(self.image_cache_dir, exist_ok=True)

        self.setWindowTitle("Paldex")
        self.resize(760, 720)
        self.setMinimumSize(560, 500)
        self.label = QLabel("PALDEX", self)
        self.info_pal = QLabel("Search for a Pal to view its details.", self)
        self.partner_skill = QLabel("—", self)
        self.pal_type = QLabel("—", self)
        self.pal_drops_widget = QWidget()
        self.pal_drops_widget.setObjectName("dropsContainer")
        self.pal_drops_layout = QHBoxLayout(self.pal_drops_widget)
        self.pal_drops_layout.setContentsMargins(0, 0, 0, 0)
        self.pal_drops_layout.setSpacing(12)
        self.pal_drops_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.pal_work = QLabel("—", self)
        self.pal_alpha = QLabel("—", self)
        self.pal_eggs = QLabel("—", self)
        self.pal_sources = QLabel("—", self)
        self.pal_habitat = QLabel("—", self)
        self.pal_image = QLabel(self)
        self.pal_image.setFixedSize(200, 200)
        self.pal_image.setScaledContents(True)
        self.pal_image.setAlignment(Qt.AlignCenter)
        self.pal_name_label = QLabel("No Pal selected", self)
        self.pal_name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search a Pal, for example Chillet Ignis")
        self.search_input.setClearButtonEnabled(True)

        # QCompleter provides dropdown suggestions from the Pal names already
        # loaded in pal_data.py, without loading the combat data again.

        pal_names = sorted({pal["name"] for pal in combat_data}, key=str.casefold)
        self.search_completer = QCompleter(pal_names, self)
        self.search_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.search_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.search_completer.setMaxVisibleItems(9)
        self.search_completer.popup().setMinimumWidth(330)
        self.search_input.setCompleter(self.search_completer)
        self.button = QPushButton("Search", self)
        self.clear_button = QPushButton("Clear", self)
        self.map_button = QPushButton("Open PalDB Map", self)
        self.current_pal = None
        self.set_image_placeholder("No Pal selected")
        self.initUI()

    def element_badges(self, elements):
        """Return the elements as coloured badges (rich text for a QLabel)."""
        badges = []
        for element in elements:
            background, text_color = ELEMENT_COLORS.get(
                str(element).strip().lower(), ("#3A3A3A", "#FFFFFF"))
            badges.append(
                f'<span style="background-color:{background}; color:{text_color}; '
                f'font-weight:600;">&nbsp;&nbsp;{element}&nbsp;&nbsp;</span>'
            )
        return "&nbsp;&nbsp;".join(badges) if badges else "—"

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

    def set_image_placeholder(self, message):
        """Show a useful, styled message when an image is not available."""
        self.pal_image.clear()
        self.pal_image.setText(message)

    def create_section(self, title, content):
        """Build one consistent information card around an existing widget."""
        section = QGroupBox(title)
        section.setObjectName("infoSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.addWidget(content)
        return section

    def clear_drop_widgets(self):
        # Drop icons are rebuilt for every result, so remove old widgets before
        # showing a new Pal or clearing the screen.

        while self.pal_drops_layout.count():
            item = self.pal_drops_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def clear_pal_details(self):
        # Reset every result widget together so a previous Pal cannot leave
        # stale information or a stale Map-button target behind.

        self.current_pal = None
        self.pal_name_label.setText("No Pal selected")
        for label in (self.partner_skill, self.pal_type, self.pal_work,
                      self.pal_alpha, self.pal_eggs, self.pal_sources,
                      self.pal_habitat):
            label.setText("—")
        self.set_image_placeholder("No Pal selected")
        self.clear_drop_widgets()

    def show_map(self):
        if not self.current_pal:
            return

        # PalDB uses underscores rather than spaces in its Pal page URLs.

        pal_name = self.current_pal["name"]
        webbrowser.open(f"https://paldb.cc/en/{pal_name.replace(' ', '_')}")

    def search_pal(self):
        pal_name = self.search_input.text().strip().lower()
        if not pal_name:
            self.info_pal.setText("Please enter a Pal name.")
            self.clear_pal_details()
            return
        # This combines the Pal's combat entry with related work, location,
        # icon, and drop data from pal_data.py for the UI sections below.

        pal_data = self.get_pal_data(pal_name)
        if not pal_data:
            self.info_pal.setText("Pal not found. Check the spelling and try again.")
            self.clear_pal_details()
            return

        self.current_pal = pal_data
        self.info_pal.clear()
        self.pal_name_label.setText(f"Pal Name: {pal_name.capitalize()}")
        self.partner_skill.setText(pal_data["partner_skill"]["effect"])
        self.pal_type.setText(self.element_badges(pal_data["elements"]))
        self.pal_work.setText("\n".join(pal_data["work"]))

        # pal_data.py pairs every notable drop name with its icon URL. The
        # name stays visible even when an item has no icon available.

        self.clear_drop_widgets()
        for drop in pal_data["drop_icons"]:
            drop_widget = QWidget()
            drop_widget.setObjectName("dropItem")
            drop_layout = QVBoxLayout(drop_widget)
            drop_layout.setContentsMargins(8, 8, 8, 8)
            drop_layout.setSpacing(5)
            drop_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            if drop["icon"]:
                pixmap = self.get_cached_image(drop["icon"])
                if pixmap:
                    icon_label = QLabel()
                    icon_label.setAlignment(Qt.AlignCenter)
                    icon_label.setPixmap(pixmap.scaled(
                        50, 50, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ))
                    drop_layout.addWidget(icon_label)
            name_label = QLabel(drop["name"])
            name_label.setObjectName("dropName")
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setMaximumWidth(100)
            drop_layout.addWidget(name_label)
            self.pal_drops_layout.addWidget(drop_widget)

        locations = pal_data["location"]["locations"]
        alpha_text = "\n".join(locations) if locations else "No Alpha location data available."
        self.pal_alpha.setText(f"Day/Night: {pal_data['location']['day_night']}\n{alpha_text}")

        # pal_data.py normalizes location names, removes source-only level
        # and coordinate text, then looks up matching habitat coordinates.

        habitat_text = []
        for habitat in pal_data["location"].get("habitat_coordinates", []):
            location = habitat["location"]
            x = habitat.get("x")
            y = habitat.get("y")
            if x is not None and y is not None:
                habitat_text.append(f"{location} (X: {x}, Y: {y})")
        self.pal_habitat.setText("\n".join(habitat_text) if habitat_text else "No habitat coordinates available.")
        egg_types = pal_data["location"]["egg_types"]
        self.pal_eggs.setText("\n".join(egg_types) if egg_types else "No egg data available.")
        other_sources = pal_data["location"]["other_sources"]
        self.pal_sources.setText("\n".join(other_sources) if other_sources else "No other sources available.")

        pixmap = self.get_cached_image(pal_data.get("icon"))
        if pixmap:
            self.pal_image.setPixmap(pixmap)
        else:
            self.set_image_placeholder("Image unavailable")

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

    def initUI(self):
        self.setStyleSheet("""
            QMainWindow { background: #000000; }
            QWidget { color: #F5F5F5; font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }
            QWidget#centralWidget, QWidget#scrollContent, QWidget#scrollViewport { background: #000000; }
            QLabel#appTitle { color: #00E0FF; font-size: 27px; font-weight: 700; }
            QLabel#subtitle { color: #6B6B6B; font-size: 12px; }
            QLabel#palName { color: #FFFFFF; font-size: 20px; font-weight: 700; }
            QLabel#imageCaption { color: #00E0FF; font-size: 10px; font-weight: 600; }
            QLabel#statusMessage { color: #A0A0A0; font-size: 12px; }
            QLabel#detailValue { color: #F5F5F5; line-height: 1.35; }
            QLabel#imagePlaceholder { color: #6B6B6B; font-size: 12px; }
            QLineEdit { background: #070709; border: 1px solid #222222; border-radius: 6px; padding: 9px 11px; color: #F5F5F5; selection-background-color: #00E0FF; selection-color: #000000; }
            QLineEdit::placeholder { color: #6B6B6B; }
            QLineEdit:focus { border: 2px solid #00E0FF; padding: 8px 10px; }
            QCompleter QAbstractItemView { background: #070709; border: 1px solid #222222; color: #F5F5F5; outline: none; selection-background-color: #00E0FF; selection-color: #000000; }
            QPushButton { background: #0D0D10; border: 1px solid #222222; border-radius: 6px; padding: 9px 14px; font-weight: 600; color: #F5F5F5; }
            QPushButton:hover { background: #141414; border-color: #3A3A3A; }
            QPushButton:pressed { background: #070709; }
            QPushButton#searchButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3DE8FF, stop:1 #00C4E0); border-color: #00E0FF; color: #000000; }
            QPushButton#searchButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7FF0FF, stop:1 #19D2EE); border-color: #4DEAFF; }
            QPushButton#searchButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00B8D4, stop:1 #009BB5); border-color: #00B8D4; }
            QPushButton#mapButton { background: #000000; border-color: #00E0FF; color: #00E0FF; }
            QPushButton#mapButton:hover { background: #00232A; border-color: #4DEAFF; color: #4DEAFF; }
            QFrame#profileCard { background: #0D0D10; border: 1px solid #2A2A2A; border-radius: 8px; }
            QFrame#imageCard { background: #070709; border: 1px solid #222222; border-radius: 6px; }
            QWidget#dropsContainer { background: #0D0D10; }
            QGroupBox#infoSection { background: #0D0D10; border: 1px solid #222222; border-radius: 7px; margin-top: 10px; padding-top: 8px; font-weight: 600; color: #00E0FF; }
            QGroupBox#infoSection:hover { border-color: #2F5A63; }
            QGroupBox#infoSection::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 5px; color: #00E0FF; background: #0D0D10; }
            QWidget#dropItem { background: #070709; border: 1px solid #222222; border-radius: 6px; }
            QLabel#dropName { color: #F5F5F5; font-size: 11px; font-weight: 600; }
            QScrollArea#mainScrollArea { border: none; background: #000000; }
            QScrollArea#mainScrollArea::viewport { background: #000000; }
            QScrollBar:vertical { background: #070709; width: 9px; margin: 4px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #2A2A2A; min-height: 28px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #00E0FF; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(22, 18, 22, 18)
        root_layout.setSpacing(14)
        self.label.setObjectName("appTitle")
        self.label.setAlignment(Qt.AlignHCenter)
        subtitle = QLabel("A companion guide for your Palworld adventures")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignHCenter)
        root_layout.addWidget(self.label)
        root_layout.addWidget(subtitle)

        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.button.setObjectName("searchButton")
        self.map_button.setObjectName("mapButton")
        for button in (self.button, self.map_button, self.clear_button):
            button.setMinimumHeight(38)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.button)
        search_layout.addWidget(self.map_button)
        search_layout.addWidget(self.clear_button)
        root_layout.addLayout(search_layout)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainScrollArea")
        scroll_area.viewport().setObjectName("scrollViewport")
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(2, 2, 8, 2)
        content_layout.setSpacing(12)
        profile_card = QFrame()
        profile_card.setObjectName("profileCard")
        profile_layout = QHBoxLayout(profile_card)
        profile_layout.setContentsMargins(16, 16, 16, 16)
        profile_layout.setSpacing(18)
        image_card = QFrame()
        image_card.setObjectName("imageCard")
        image_layout = QVBoxLayout(image_card)
        image_layout.setContentsMargins(8, 8, 8, 8)
        image_caption = QLabel("PAL IMAGE")
        image_caption.setObjectName("imageCaption")
        image_caption.setAlignment(Qt.AlignHCenter)
        self.pal_image.setObjectName("imagePlaceholder")
        image_layout.addWidget(image_caption)
        image_layout.addWidget(self.pal_image)
        profile_layout.addWidget(image_card, 0, Qt.AlignTop)
        identity_layout = QVBoxLayout()
        identity_layout.setSpacing(7)
        self.pal_name_label.setObjectName("palName")
        self.info_pal.setObjectName("statusMessage")
        self.info_pal.setWordWrap(True)
        identity_layout.addWidget(self.pal_name_label)
        identity_layout.addWidget(self.info_pal)
        identity_layout.addStretch()
        profile_layout.addLayout(identity_layout, 1)
        content_layout.addWidget(profile_card)

        # All text values share wrapping so longer location and source data
        # remains readable.

        for detail_label in (self.partner_skill, self.pal_type, self.pal_work,
                             self.pal_alpha, self.pal_eggs, self.pal_sources,
                             self.pal_habitat):
            detail_label.setObjectName("detailValue")
            detail_label.setWordWrap(True)
            detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        sections = QGridLayout()
        sections.setContentsMargins(0, 0, 0, 0)
        sections.setHorizontalSpacing(12)
        sections.setVerticalSpacing(12)
        sections.setColumnStretch(0, 1)
        sections.setColumnStretch(1, 1)
        sections.addWidget(self.create_section("🤝 Partner Skill", self.partner_skill), 0, 0, 1, 2)
        sections.addWidget(self.create_section("⚔️ Elements", self.pal_type), 1, 0)
        sections.addWidget(self.create_section("🛠️ Work Suitability", self.pal_work), 1, 1)
        sections.addWidget(self.create_section("💎 Notable Drops", self.pal_drops_widget), 2, 0, 1, 2)
        sections.addWidget(self.create_section("👑 Alpha Location", self.pal_alpha), 3, 0)
        sections.addWidget(self.create_section("🥚 Egg Types", self.pal_eggs), 3, 1)
        sections.addWidget(self.create_section("📍 How to Obtain", self.pal_sources), 4, 0)
        sections.addWidget(self.create_section("🗺️ Habitat", self.pal_habitat), 4, 1)
        content_layout.addLayout(sections)
        content_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, 1)

        # Both search actions use the same method; Map uses the successful
        # result stored in current_pal rather than whatever is in the input box.

        self.button.clicked.connect(self.search_pal)

        # Enter accepts a visible suggestion first; otherwise it keeps the
        # existing Enter-to-search behavior.

        self.search_input.returnPressed.connect(
            lambda: None if self.search_completer.popup().isVisible() else self.search_pal()
        )
        self.clear_button.clicked.connect(self.clear_input)
        self.map_button.clicked.connect(self.show_map)
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        central_widget.setLayout(root_layout)
        self.setCentralWidget(central_widget)

    def clear_input(self):
        self.search_input.clear()
        self.info_pal.clear()
        self.clear_pal_details()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pal_dex = Paldex()
    pal_dex.show()
    sys.exit(app.exec())
