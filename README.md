

# CiefpSettingsDownloader

![Bouquet](https://github.com/ciefp/CiefpSettingsDownloader/blob/main/ciefpsettingsdownloader-1.jpg) 
![Bouquet](https://github.com/ciefp/CiefpSettingsDownloader/blob/main/ciefpsettingsdownloader-2.jpg) 
 
 
## ..:: Ciefp Settings Downloader v1.9 ::..

# NEW FEATURE: DAB+ Radio Bouquets

This version adds a "DAB+ Radio" button that opens a new screen
for downloading and installing DAB+ radio bouquets directly from
GitHub (ciefp/CiefpVibesFiles → DAB_RADIO).

# The new screen offers:
  - Multi-select of bouquets (OK / Yellow = mark/unmark)
  - "Install Selected" (Green) — installs only marked bouquets
  - "Mark / Unmark" (Yellow) — quick toggle for current row
  - "Select All / Install All" (Blue) — mark all or install all
  - Pretty display names instead of raw filenames
    (e.g. "Dab Bundesmux2 23.5E" instead of "userbouquet.dab_bundesmux2_235e.radio")
  - Automatic bouquet registration in /etc/enigma2/bouquets.radio
    (#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "..." ORDER BY bouquet)
  - Automatic settings reload after installation

═══════════════════════════════════════════════════════════
⚠️  IMPORTANT WARNING — READ BEFORE INSTALLING DAB+ BOUQUETS
═══════════════════════════════════════════════════════════

DAB+ support is currently available ONLY on:

    ➤  OpenATV DEVELOP image

This feature is NOT yet available on official stable OpenATV
releases, nor on other images (OpenPLi, Egami, PurE2, OpenBH, etc.).

If you install DAB+ bouquets on an image that does NOT support DAB+:

    • the bouquets WILL be installed in /etc/enigma2/
    • they WILL appear in the radio list
    • but the bouquet content will show "N/A"
      (stations will not be playable)

Therefore, DAB+ bouquets are currently usable only on
OpenATV DEVELOP. Once official stable versions receive
DAB+ support, this warning will be removed.

If you are not sure which image version you are running:
    Menu → Information → About → Image version

═══════════════════════════════════════════════════════════

# Other changes in v1.9:
  - Plugin version bumped to 1.9
  - Redesigned bottom bar — 3 equal-width buttons on main
    screen (Back / Download & Install / DAB+ Radio))
  - Added new "settingsdownloader.png" logo for the Settings screen
  - Added new "dabradio.png" logo for the DAB+ screen
  - Improved stability and error handling

# .:: Ciefp Settings ::.
 