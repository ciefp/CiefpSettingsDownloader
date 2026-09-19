from __future__ import print_function
import sys
import os
import re
import requests
import shutil
import zipfile
from enigma import eDVBDB
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox

PLUGIN_NAME = "CiefpSettingsDownloader"
PLUGIN_DESC = "Download and install Ciefp settings from GitHub"
PLUGIN_VERSION = "1.9"
PLUGIN_ICON = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSettingsDownloader/icon.png"
PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSettingsDownloader/"

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

DAB_API_URL = "https://api.github.com/repos/ciefp/CiefpVibesFiles/contents/DAB_RADIO"
DAB_RAW_URL = "https://github.com/ciefp/CiefpVibesFiles/raw/main/DAB_RADIO/"

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def to_unicode(s):
    if sys.version_info[0] < 3:
        return s.decode('utf-8') if isinstance(s, str) else s
    return s


# =====================================================================
# HELPERS - lepa imena
# =====================================================================
def pretty_name(filename):
    """
    userbouquet.dab_bundesmux2_235e.radio  ->  Bundesmux 23.5E
    userbouquet.dab_allgaeu_donau_iller_7e_12567.radio -> Allgaeu Donau Iller 7.0E
    userbouquet.dab_hr_radio_7e.radio -> Hr Radio 7.0E
    """
    name = filename
    # skini prefiks i sufiks
    for p in ("userbouquet.", "userbouquet.dab_", "userbouquet."):
        if name.startswith(p):
            name = name[len(p):]
    if name.endswith(".radio"):
        name = name[:-6]
    if name.endswith(".tv"):
        name = name[:-3]

    # Zameni _ sa razmakom
    parts = name.split("_")

    # Specijalno: ako je zadnji deo tipa 12567 ostavi ga, ali preuredi E oznake
    out_parts = []
    for p in parts:
        # Prepoznaj koordinate tipa "7e", "235e", "19e", "5w", "08w", "13e"
        m = re.match(r'^(\d+)(e|w)$', p.lower())
        if m:
            num = m.group(1)
            direction = m.group(2).upper()
            if len(num) > 2:
                # 235 -> 23.5
                num = num[:-1] + "." + num[-1]
            else:
                num = num + ".0"
            out_parts.append(num + direction)
        else:
            out_parts.append(p.capitalize())
    return " ".join(out_parts)


def is_valid_bouquet_filename(fn):
    return fn.startswith("userbouquet.") and (fn.endswith(".radio") or fn.endswith(".tv"))


# =====================================================================
# SAT SETTINGS SCREEN
# =====================================================================
class CiefpSettingsDownloaderScreen(Screen):
    skin = """
        <screen name="CiefpSettingsDownloaderScreen" position="center,center" size="1920,1080" backgroundColor="#011a2e">
            <widget name="separator0" position="0,10" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="background" position="1300,100" size="600,800" zPosition="0" />
            <widget name="plugin_title" position="0,20" size="1920,60" font="Bold;32" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" zPosition="1" />
            <widget name="separator1" position="0,80" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="menu" position="60,100" size="1200,800" scrollbarMode="showOnDemand" itemHeight="40" font="Regular;28" backgroundColor="#011a2e" zPosition="1" />
            <widget name="status" position="60,920" size="1800,50" font="Regular;26" halign="center" valign="center" foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1" zPosition="1" />
            <widget name="separator2" position="0,910" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="separator3" position="0,990" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="red_button" position="20,1000" size="620,40" font="Bold;28" halign="center" backgroundColor="#9F1313" foregroundColor="#FFFFFF" text="Back" zPosition="1" />
            <widget name="green_button" position="650,1000" size="620,40" font="Bold;28" halign="center" backgroundColor="#1F771F" foregroundColor="#FFFFFF" text="Download &amp; Install" zPosition="1" />
            <widget name="blue_button" position="1280,1000" size="620,40" font="Bold;28" halign="center" backgroundColor="#1313A0" foregroundColor="#FFFFFF" text="DAB+ Radio" zPosition="1" />
        </screen>
    """

    def __init__(self, session):
        super(CiefpSettingsDownloaderScreen, self).__init__(session)
        self.session = session

        self["plugin_title"] = Label("..:: Ciefp Settings Downloader ::.. (v1.9)")
        self["menu"] = MenuList([])
        self["status"] = Label("Connecting to GitHub...")
        self["red_button"] = Label("Back")
        self["green_button"] = Label("Download & Install")
        self["blue_button"] = Label("DAB+ Radio")
        self["background"] = Pixmap()
        self["separator0"] = Label()
        self["separator1"] = Label()
        self["separator2"] = Label()
        self["separator3"] = Label()

        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "ok": self.ok_pressed,
            "green": self.ok_pressed,
            "cancel": self.close,
            "red": self.close,
            "blue": self.open_dab_screen,
            "up": self["menu"].up,
            "down": self["menu"].down
        }, -1)

        self.available_files = {}
        self.onLayoutFinish.append(self.init_screen_data)

    def init_screen_data(self):
        img_path = PLUGIN_DIR + "settingsdownloader.png"
        if os.path.exists(img_path):
            self["background"].instance.setPixmapFromFile(img_path)
        else:
            self["background"].hide()
        self.fetch_file_list()

    def open_dab_screen(self):
        self.session.open(CiefpDabRadioScreen)

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
        except Exception as e:
            self["status"].setText("Error: " + to_unicode(str(e)))

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
            self["status"].setText("Downloading {0}...".format(file_name))
            r = requests.get(url, stream=True, timeout=15)
            r.raise_for_status()
            with open(download_path, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            self["status"].setText("Extracting...")
            with zipfile.ZipFile(download_path, "r") as z:
                z.extractall(extract_path)
            self.clean_old_bouquets()
            self.copy_files(extract_path)
            self.reload_settings()
            self["status"].setText("{0} installed!".format(selected_item))
        except Exception as e:
            self["status"].setText("Error: " + to_unicode(str(e)))
        finally:
            if os.path.exists(download_path):
                os.remove(download_path)
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)

    def clean_old_bouquets(self):
        try:
            for item in os.listdir("/etc/enigma2/"):
                if item.startswith("userbouquet.") and (item.endswith(".tv") or item.endswith(".radio")):
                    os.remove("/etc/enigma2/" + item)
        except:
            pass

    def copy_files(self, path):
        for root, dirs, files in os.walk(path):
            for file in files:
                src = os.path.join(root, file)
                if file == "satellites.xml":
                    shutil.move(src, "/etc/tuxbox/" + file)
                elif file.endswith((".tv", ".radio")) or file == "lamedb" or file.endswith(".xml"):
                    shutil.move(src, "/etc/enigma2/" + file)

    def reload_settings(self):
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
            self.session.open(MessageBox, "Reload successful!",
                              MessageBox.TYPE_INFO, timeout=5)
        except Exception as e:
            self.session.open(MessageBox, "Reload failed: " + to_unicode(str(e)),
                              MessageBox.TYPE_ERROR, timeout=5)


# =====================================================================
# DAB+ RADIO SCREEN  (v1.9 - multi-select, pretty names, correct registration)
# =====================================================================
class CiefpDabRadioScreen(Screen):
    skin = """
        <screen name="CiefpDabRadioScreen" position="center,center" size="1920,1080" backgroundColor="#011a2e">
            <widget name="separator0" position="0,10" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="background" position="1300,100" size="600,800" zPosition="0" />
            <widget name="plugin_title" position="0,20" size="1920,60" font="Bold;32" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" zPosition="1" />
            <widget name="separator1" position="0,80" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="menu" position="60,100" size="1200,800" scrollbarMode="showOnDemand" itemHeight="40" font="Regular;28" backgroundColor="#011a2e" zPosition="1" />
            <widget name="status" position="60,920" size="1800,50" font="Regular;26" halign="center" valign="center" foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1" zPosition="1" />
            <widget name="separator2" position="0,910" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="separator3" position="0,990" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="red_button" position="20,1000" size="460,40" font="Bold;24" halign="center" backgroundColor="#9F1313" foregroundColor="#FFFFFF" text="Back" zPosition="1" />
            <widget name="green_button" position="490,1000" size="460,40" font="Bold;24" halign="center" backgroundColor="#1F771F" foregroundColor="#FFFFFF" text="Install Selected" zPosition="1" />
            <widget name="yellow_button" position="960,1000" size="460,40" font="Bold;24" halign="center" backgroundColor="#A0A000" foregroundColor="#FFFFFF" text="Mark / Unmark" zPosition="1" />
            <widget name="blue_button" position="1430,1000" size="470,40" font="Bold;24" halign="center" backgroundColor="#1313A0" foregroundColor="#FFFFFF" text="Select All / Install All" zPosition="1" />
        </screen>
    """

    def __init__(self, session):
        super(CiefpDabRadioScreen, self).__init__(session)
        self.session = session

        self["plugin_title"] = Label("..:: Ciefp DAB+ Radio Bouquets ::.. (v1.9)")
        self["menu"] = MenuList([])
        self["status"] = Label("Connecting to GitHub...")
        self["red_button"] = Label("Back")
        self["green_button"] = Label("Install Selected")
        self["yellow_button"] = Label("Mark / Unmark")
        self["blue_button"] = Label("Select All / Install All")
        self["background"] = Pixmap()
        self["separator0"] = Label()
        self["separator1"] = Label()
        self["separator2"] = Label()
        self["separator3"] = Label()

        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "ok": self.toggle_mark,
            "green": self.install_marked,
            "cancel": self.close,
            "red": self.close,
            "yellow": self.toggle_mark,
            "blue": self.blue_action,
            "up": self["menu"].up,
            "down": self["menu"].down
        }, -1)

        # filename -> True/False (označen)
        self.available_files = {}      # filename -> filename
        self.marked = set()            # skup označenih filename-ova
        self.onLayoutFinish.append(self.init_screen_data)

    def init_screen_data(self):
        img_path = PLUGIN_DIR + "dabradio.png"
        if os.path.exists(img_path):
            self["background"].instance.setPixmapFromFile(img_path)
        else:
            self["background"].hide()
        self.fetch_file_list()

    # ---------- FETCH ----------
    def fetch_file_list(self):
        try:
            self["status"].setText("Fetching DAB+ Radio bouquets from GitHub...")
            r = requests.get(DAB_API_URL, timeout=10)
            r.raise_for_status()
            files = r.json()
            for f in files:
                fn = f.get("name", "")
                if is_valid_bouquet_filename(fn):
                    self.available_files[fn] = fn

            if not self.available_files:
                self["status"].setText("No DAB+ Radio bouquets found on GitHub.")
                return

            self.refresh_menu()
            self["status"].setText("OK/Yellow = mark, Green = install marked, Blue = select all / install all.")
        except Exception as e:
            self["status"].setText("Error: " + to_unicode(str(e)))

    def refresh_menu(self):
        """Prikaz: [X] Lepo Ime    ili    [ ] Lepo Ime"""
        items = []
        for fn in sorted(self.available_files.keys()):
            mark = "[X]" if fn in self.marked else "[ ]"
            items.append("{0} {1}".format(mark, pretty_name(fn)))
        self["menu"].setList(items)

    def filename_from_display(self, display):
        """Iz prikazanog '  [X] Bundesmux 23.5E' vrati originalni filename."""
        # skini mark prefix
        s = display.strip()
        if s.startswith("[X]") or s.startswith("[ ]"):
            s = s[3:].strip()
        # Nadji filename kome pretty_name odgovara
        for fn in self.available_files:
            if pretty_name(fn) == s:
                return fn
        return None

    # ---------- MARK ----------
    def toggle_mark(self):
        cur = self["menu"].getCurrent()
        if not cur:
            return
        fn = self.filename_from_display(cur)
        if not fn:
            return
        if fn in self.marked:
            self.marked.discard(fn)
        else:
            self.marked.add(fn)
        self.refresh_menu()
        self["status"].setText("Marked: {0} file(s)".format(len(self.marked)))

    # ---------- BLUE ----------
    def blue_action(self):
        """Ako ništa nije označeno -> označi sve.
           Ako je nešto označeno -> pitaj korisnika šta želi (Select All vs Install All)."""
        if not self.marked:
            # označi sve
            self.marked = set(self.available_files.keys())
            self.refresh_menu()
            self["status"].setText("All {0} bouquets marked. Press Green to install.".format(len(self.marked)))
        else:
            # pitaj: označi sve ili instaliraj sve
            self.session.openWithCallback(
                self.blue_choice_cb,
                MessageBox,
                "Šta želiš?\n\nDA = označi SVE\nNE = instaliraj SVE označene",
                MessageBox.TYPE_YESNO,
                timeout=15
            )

    def blue_choice_cb(self, answer):
        if answer is True:
            # označi sve
            self.marked = set(self.available_files.keys())
            self.refresh_menu()
            self["status"].setText("All {0} bouquets marked.".format(len(self.marked)))
        elif answer is False:
            # instaliraj sve
            if not self.marked:
                self.marked = set(self.available_files.keys())
                self.refresh_menu()
            self.install_marked()

    # ---------- INSTALL ----------
    def install_marked(self):
        if not self.marked:
            self["status"].setText("Nothing marked. Press Yellow to mark files first.")
            return
        self.install_list(sorted(self.marked))

    def install_list(self, filenames):
        ok_count = 0
        errors = []
        for i, fn in enumerate(filenames):
            self["status"].setText("Installing {0}/{1}: {2}".format(i+1, len(filenames), fn))
            try:
                self.download_one(fn)
                ok_count += 1
            except Exception as e:
                errors.append("{0}: {1}".format(fn, to_unicode(str(e))))

        # registracija u bouquets.radio (za .radio fajlove)
        try:
            self.register_bouquets(filenames)
        except Exception as e:
            errors.append("register: " + to_unicode(str(e)))

        # reload
        self.reload_settings()

        msg = "Installed {0}/{1} bouquets.".format(ok_count, len(filenames))
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors[:5])
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=6)
        self["status"].setText(msg.replace("\n", " "))

    def download_one(self, filename):
        url = DAB_RAW_URL + filename
        dst = "/etc/enigma2/" + filename
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        with open(dst, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

    # ---------- REGISTER ----------
    def register_bouquets(self, filenames):
        """
        Za svaki .radio fajl dodaje liniju u /etc/enigma2/bouquets.radio:
          #SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.xxx.radio" ORDER BY bouquet
        Ako linija već postoji, preskače.
        """
        radio_files = [fn for fn in filenames if fn.endswith(".radio")]
        tv_files    = [fn for fn in filenames if fn.endswith(".tv")]

        if radio_files:
            self._append_bouquet_lines("/etc/enigma2/bouquets.radio", radio_files, "radio")
        if tv_files:
            self._append_bouquet_lines("/etc/enigma2/bouquets.tv", tv_files, "tv")

    def _append_bouquet_lines(self, path, filenames, kind):
        # Učitaj postojeći sadržaj
        if os.path.exists(path):
            with open(path, "r") as f:
                content = f.read()
        else:
            if kind == "radio":
                content = '#NAME User - bouquets (Radio)\n'
            else:
                content = '#NAME User - bouquets (TV)\n'

        # Osiguraj da fajl završava novim redom
        if content and not content.endswith("\n"):
            content += "\n"

        added = 0
        for fn in filenames:
            line = '#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "{0}" ORDER BY bouquet'.format(fn)
            if line not in content:
                content += line + "\n"
                added += 1

        if added:
            with open(path, "w") as f:
                f.write(content)

    # ---------- RELOAD ----------
    def reload_settings(self):
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
        except Exception as e:
            print("[CiefpDAB] reload error:", e)


# =====================================================================
# PLUGIN REGISTRATION
# =====================================================================
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