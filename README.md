# Twilight Boxart CLI

A command-line tool to automatically download and resize boxart images for ROMs used with [TWiLightMenu++](https://github.com/DS-Homebrew/TWiLightMenu).

## 📦 Features

- Scans a directory of ROMs and detects supported systems
- Calculates SHA1 checksums and looks up official names using No-Intro DAT files
- Downloads matching boxart images from the [Libretro Thumbnails Repository](https://github.com/libretro-thumbnails/)
- Automatically resizes images to `128x115` PNGs for use with TWiLightMenu++
- Supports optional ROM renaming to match No-Intro names
- Logs missing boxart matches to `errors.txt`

## ✅ Supported Consoles

- Nintendo DS / DSi
- Game Boy / Color / Advance
- NES, SNES
- Sega Genesis / Game Gear / Master System
- TurboGrafx-16, Neo Geo Pocket, WonderSwan, Atari

## 🛠️ Usage

```bash
python twilight_boxart_cli.py --rom-dir roms --sdcard-dir /media/user/SDCARD --rename --errors
```

- `--rom-dir`: Path to your ROMs directory
- `--sdcard-dir`: Root of your SD card (used to place boxart and download DATs)
- `--rename`: Rename ROMs to match official No-Intro names
- `--errors`: Save a list of missing boxart matches to `errors.txt`

## 📁 Output

- Boxart images go into: `_nds/TWiLightMenu/boxart/` on the SD card
- DAT files are saved to: `no-intro/` on the SD card

## 💬 License

[GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html)
