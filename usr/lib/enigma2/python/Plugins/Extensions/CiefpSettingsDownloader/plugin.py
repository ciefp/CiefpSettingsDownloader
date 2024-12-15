from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from enigma import eDVBDB  # Import za eDVBDB
import os
import requests
import shutil
import zipfile

PLUGIN_NAME = "CiefpSettingsDownloader"
PLUGIN_DESC = "Download and install Ciefp settings from GitHub"
PLUGIN_ICON = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSettingsDownloader/icon.png"

GITHUB_ZIP_LIST_URL = "https://github.com/ciefp/ciefpsettings-enigma2-zipped/archive/refs/heads/master.zip"

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

class CiefpSettingsDownloaderScreen(Screen):
    def __init__(self, session):
        self.skin = """
        <screen name="CiefpSettingsDownloaderScreen" position="center,center" size="900,540" title="Ciefp Settings Downloader">
            <widget name="menu" position="10,10" size="880,440" scrollbarMode="showOnDemand" />
            <widget name="status" position="10,460" size="880,60" font="Regular;24" halign="center" valign="center" />
        </screen>
        """
        Screen.__init__(self, session)
        self.session = session

        self["menu"] = MenuList([])  # Empty list initially
        self["status"] = Label("Fetching available channel lists...")
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok_pressed,
            "cancel": self.close,
            "up": self.move_up,
            "down": self.move_down
        }, -1)

        self.available_files = {}  # This will store the available files
        self.fetch_file_list()

    def fetch_file_list(self):
        """Fetches list of files from GitHub and filters by STATIC_NAMES."""
        try:
            self["status"].setText("Fetching available lists from GitHub...")
            # Download the zip file from GitHub
            response = requests.get(GITHUB_ZIP_LIST_URL, timeout=10)
            response.raise_for_status()  # If the response code is not 200, raise an error

            zip_path = '/tmp/ciefp_settings.zip'
            with open(zip_path, 'wb') as f:
                f.write(response.content)

            # Unzip the downloaded file
            self.extract_zip(zip_path)

        except requests.exceptions.RequestException as e:
            self["status"].setText(f"Network error: {str(e)}")
        except Exception as e:
            self["status"].setText(f"Error processing lists: {str(e)}")

    def extract_zip(self, zip_path):
        """Extracts the downloaded zip file."""
        try:
            self["status"].setText("Extracting files...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall('/tmp')

            # Get the folder that contains all lists
            extracted_folder = '/tmp/ciefpsettings-enigma2-zipped-master'
            self.populate_menu(extracted_folder)

        except Exception as e:
            self["status"].setText(f"Error extracting files: {str(e)}")

    def populate_menu(self, extracted_folder):
        """Populate the menu with available lists from the extracted folder."""
        list_items = []
        for static_name in STATIC_NAMES:
            list_items.append(static_name)

        # Update the menu with the list of available files
        self["menu"].setList(list_items)
        self["status"].setText("Select a channel list to download.")

    def ok_pressed(self):
        """Called when the 'OK' button is pressed."""
        selected_item = self["menu"].getCurrent()
        if selected_item:
            self.download_and_install(selected_item)

    def move_up(self):
        self["menu"].up()

    def move_down(self):
        self["menu"].down()

    def download_and_install(self, selected_item):
        """Download and install the selected list."""
        selected_file = f"{selected_item}-14.12.2024.zip"
        url = f"https://github.com/ciefp/ciefpsettings-enigma2-zipped/raw/refs/heads/master/{selected_file}"
        download_path = f"/tmp/{selected_file}"
        extract_path = f"/tmp/{selected_item}"

        try:
            self["status"].setText(f"Downloading {selected_file}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(download_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)

            self["status"].setText(f"Extracting {selected_file}...")
            with zipfile.ZipFile(download_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)

            self.copy_files(extract_path)
            self["status"].setText(f"{selected_item} installed successfully!")

            # Reload settings and display success message
            self.reload_settings()

        except requests.exceptions.RequestException as e:
            self["status"].setText(f"Download error: {str(e)}")
        except Exception as e:
            self["status"].setText(f"Installation error: {str(e)}")
        finally:
            # Clean up temporary files
            if os.path.exists(download_path):
                os.remove(download_path)
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)

    def copy_files(self, path):
        """Copy the extracted files to their respective directories."""
        dest_enigma2 = "/etc/enigma2/"
        dest_tuxbox = "/etc/tuxbox/"

        for root, dirs, files in os.walk(path):
            for file in files:
                if file == "satellites.xml":
                    shutil.move(os.path.join(root, file), os.path.join(dest_tuxbox, file))
                elif file.endswith(".tv") or file.endswith(".radio") or file == "lamedb":
                    shutil.move(os.path.join(root, file), os.path.join(dest_enigma2, file))

    def reload_settings(self):
        """Reload Enigma2 settings."""
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
            self.session.open(MessageBox, "Reload successful! New settings are now active.  .::ciefpsettings::.", MessageBox.TYPE_INFO, timeout=5)
        except Exception as e:
            self.session.open(MessageBox, f"Reload failed: {str(e)}", MessageBox.TYPE_ERROR, timeout=5)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name=PLUGIN_NAME,
            description=PLUGIN_DESC,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon=PLUGIN_ICON,
            fnc=lambda session: session.open(CiefpSettingsDownloaderScreen)
        )
    ]
