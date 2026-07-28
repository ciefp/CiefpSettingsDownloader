from __future__ import print_function
import sys
import os
import re
import requests
import shutil
import zipfile
from enigma import eDVBDB  # Import za eDVBDB
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox

PLUGIN_NAME = "CiefpSettingsDownloader"
PLUGIN_DESC = "Download and install Ciefp settings from GitHub"
PLUGIN_VERSION = "1.7"
PLUGIN_ICON = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSettingsDownloader/icon.png"

GITHUB_API_URL = "https://api.github.com/repos/ciefp/ciefpsettings-enigma2-zipped/contents/"
STATIC_NAMES = [
    "ciefp-E2-1sat-19E", "ciefp-E2-2satA-19E-13E", "ciefp-E2-2satB-19E-16E",
    "ciefp-E2-3satA-9E-10E-13E", "ciefp-E2-3satB-19E-16E-13E",
    "ciefp-E2-4satA-28E-19E-13E-30W", "ciefp-E2-4satB-19E-16E-13E-0.8W",
    "ciefp-E2-5sat-19E-16E-13E-1.9E-0.8W", "ciefp-E2-6sat-23E-19E-16E-13E-1.9E-0.8W",
    "ciefp-E2-7sat-23E-19E-16E-13E-4.8E-1.9E-0.8W", "ciefp-E2-8sat-28E-23E-19E-16E-13E-4.8E-1.9E-0.8W",
    "ciefp-E2-9sat-28E-23E-19E-16E-13E-9E-1.9E-0.8W-5W", "ciefp-E2-10sat-39E-28E-23E-19E-16E-13E-9E-4.8E-1.9E-0.8W",
    "ciefp-E2-13sat-42E-39E-28E-23E-19E-16E-13E-9E-7E-4.8E-1.9E-0.8w-5w",
    "ciefp-E2-16sat-42E-39E-28E-26E-23E-19E-16E-13E-10E-9E-7E-4.8E-1.9E-0.8w-4W-5w",
    "ciefp-E2-18sat-42E-39E-36E-33E-28E-26E-23E-19E-16E-13E-10E-9E-7E-4.8E-1.9E-0.8w-4W-5w",
    "ciefp-E2-75E-34W"
]

# Kompatibilnost za Python 2 i Python 3
try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO  # Python 3

def to_unicode(s):
    if sys.version_info[0] < 3:
        return s.decode('utf-8') if isinstance(s, str) else s
    return s


def to_unicode(s):
    if sys.version_info[0] < 3:
        return s.decode('utf-8') if isinstance(s, str) else s
    return s


class CiefpSettingsDownloaderScreen(Screen):
    """Full HD Module for downloading settings integrated into CiefpE2editor"""

    skin = """
        <screen name="CiefpSettingsDownloaderScreen" position="center,center" size="1920,1080"  backgroundColor="#011a2e">
            <!-- Background Image Component -->
            <widget name="separator0" position="0,10" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
            <widget name="background" position="1300,100" size="600,800" zPosition="0" />
            <widget name="plugin_title" position="0,20" size="1920,60" font="Bold;32" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" zPosition="1" />
            <widget name="separator1" position="0,80" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="menu" position="60,100" size="1200,800" scrollbarMode="showOnDemand" itemHeight="40" font="Regular;28" backgroundColor="#011a2e" zPosition="1" />
            <widget name="status" position="60,920" size="1800,50" font="Regular;26" halign="center" valign="center" foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1" zPosition="1" />
            <widget name="separator2" position="0,910" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <!-- Bottom Buttons -->
            <widget name="separator3" position="0,990" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="red_button" position="20,1000" size="920,40" font="Bold;28" halign="center" backgroundColor="#9F1313" foregroundColor="#FFFFFF" text="Back" zPosition="1" />
            <widget name="green_button" position="1000,1000" size="900,40" font="Bold;28" halign="center" backgroundColor="#1F771F" foregroundColor="#FFFFFF" text="Download &amp; Install" zPosition="1" />
        </screen>
    """

    def __init__(self, session):
        super(CiefpSettingsDownloaderScreen, self).__init__(session)
        self.session = session

        self["plugin_title"] = Label("..:: Ciefp Settings Downloader ::.. (v1.7)")
        self["menu"] = MenuList([])
        self["status"] = Label("Connecting to GitHub...")
        self["red_button"] = Label("Back")
        self["green_button"] = Label("Download & Install")

        # Ispravna inicijalizacija Pixmap-a
        self["background"] = Pixmap()

        # Separatori
        self["separator0"] = Label()
        self["separator1"] = Label()
        self["separator2"] = Label()
        self["separator3"] = Label()

        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "ok": self.ok_pressed,
            "green": self.ok_pressed,
            "cancel": self.close,
            "red": self.close,
            "up": self["menu"].up,
            "down": self["menu"].down
        }, -1)

        self.available_files = {}
        self.onLayoutFinish.append(self.init_screen_data)

    def init_screen_data(self):
        # Ispravan način za postavljanje slike
        img_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSettingsDownloader/settingsdownloader.png"

        # Provjeri postoji li slika
        if os.path.exists(img_path):
            # Za Pixmap widget koristi ovaj način
            from enigma import ePixmap
            self["background"].instance.setPixmapFromFile(img_path)
        else:
            # Ako slika ne postoji, postavi je na transparentnu
            self["background"].hide()
            self["status"].setText("Image not found, continuing without background")

        self.fetch_file_list()

    def fetch_file_list(self):
        try:
            self["status"].setText("Fetching available channel lists from GitHub...")
            response = requests.get(GITHUB_API_URL, timeout=10)
            response.raise_for_status()

            files = response.json()
            for file in files:
                file_name = file.get("name", "")
                for static_name in STATIC_NAMES:
                    if file_name.startswith(static_name):
                        self.available_files[static_name] = file_name

            sorted_files = sorted(self.available_files.keys(), key=lambda x: STATIC_NAMES.index(x))
            if sorted_files:
                self["menu"].setList(sorted_files)
                self["status"].setText("Select a channel list and press OK or Green button to install.")
            else:
                self["status"].setText("No valid lists found on GitHub repository.")
        except requests.exceptions.RequestException as e:
            self["status"].setText("Network error: " + to_unicode(str(e)))
        except Exception as e:
            self["status"].setText("Processing error: " + to_unicode(str(e)))

    def ok_pressed(self):
        selected_item = self["menu"].getCurrent()
        if selected_item:
            self.download_and_install(selected_item)

    def download_and_install(self, selected_item):
        file_name = self.available_files.get(selected_item)
        if not file_name:
            self["status"].setText("Error: File not found.")
            return

        url = "https://github.com/ciefp/ciefpsettings-enigma2-zipped/raw/refs/heads/master/" + file_name
        download_path = "/tmp/" + file_name
        extract_path = "/tmp/" + selected_item

        try:
            self["status"].setText("Downloading file {0}...".format(file_name))
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            with open(download_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)

            self["status"].setText("Extracting {0}...".format(file_name))
            with zipfile.ZipFile(download_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)

            # Safely clear old bouquets before copying new ones
            self.clean_old_bouquets()

            self["status"].setText("Copying new settings files to the system...")
            self.copy_files(extract_path)

            self.reload_settings()
            self["status"].setText("{0} installed successfully!".format(selected_item))
        except requests.exceptions.RequestException as e:
            self["status"].setText("Download error: " + to_unicode(str(e)))
        except Exception as e:
            self["status"].setText("Installation error: " + to_unicode(str(e)))
        finally:
            if os.path.exists(download_path):
                os.remove(download_path)
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)

    def clean_old_bouquets(self):
        dest_enigma2 = "/etc/enigma2/"
        try:
            for item in os.listdir(dest_enigma2):
                if item.startswith("userbouquet.") and (item.endswith(".tv") or item.endswith(".radio")):
                    os.remove(os.path.join(dest_enigma2, item))
        except:
            pass

    def copy_files(self, path):
        dest_enigma2 = "/etc/enigma2/"
        dest_tuxbox = "/etc/tuxbox/"

        for root, dirs, files in os.walk(path):
            for file in files:
                if file == "satellites.xml":
                    shutil.move(os.path.join(root, file), os.path.join(dest_tuxbox, file))
                elif file.endswith(".tv") or file.endswith(".radio") or file == "lamedb" or file.endswith(".xml"):
                    shutil.move(os.path.join(root, file), os.path.join(dest_enigma2, file))

    def reload_settings(self):
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
            self.session.open(MessageBox, "Reload successful! New settings are now active.\n.:: ciefpsettings ::.",
                              MessageBox.TYPE_INFO, timeout=5)
        except Exception as e:
            self.session.open(MessageBox, "Reload failed: " + to_unicode(str(e)), MessageBox.TYPE_ERROR, timeout=5)
def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="{0} v{1}".format(PLUGIN_NAME, PLUGIN_VERSION),
            description=PLUGIN_DESC,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon=PLUGIN_ICON,
            fnc=lambda session: session.open(CiefpSettingsDownloaderScreen)
        )
    ]
