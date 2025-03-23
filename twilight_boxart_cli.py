import os
import sys
import hashlib
import requests
import argparse
import re
from pathlib import Path
from io import BytesIO
from PIL import Image
import urllib.parse

SUPPORTED_SYSTEMS = {
    'nds': ['.nds'],
    'snes': ['.smc', '.sfc'],
    'nes': ['.nes'],
    'gb': ['.gb'],
    'gbc': ['.gbc'],
    'gba': ['.gba'],
    'gg': ['.gg'],
    'sms': ['.sms'],
    'md': ['.gen', '.smd', '.bin', '.md']
}

LIBRETRO_THUMBNAIL_MAP = {
    'gba': 'Nintendo_-_Game_Boy_Advance',
    'gb': 'Nintendo_-_Game_Boy',
    'gbc': 'Nintendo_-_Game_Boy_Color',
    'nes': 'Nintendo_-_Nintendo_Entertainment_System',
    'snes': 'Nintendo_-_Super_Nintendo_Entertainment_System',
    'nds': 'Nintendo_-_Nintendo_DS',
    'md': 'Sega_-_Mega_Drive_-_Genesis',
    'sms': 'Sega_-_Master_System',
    'gg': 'Sega_-_Game_Gear'
}

LIBRETRO_DATABASE_REPO = "https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro"

def sha1_hash(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def find_roms(rom_dir):
    roms = []
    for root, _, files in os.walk(rom_dir):
        for file in files:
            ext = Path(file).suffix.lower()
            for system, extensions in SUPPORTED_SYSTEMS.items():
                if ext in extensions:
                    roms.append((Path(root) / file, system))
    return roms

def download_with_progress(url, dest_path):
    with requests.get(url, stream=True) as r:
        total = int(r.headers.get('content-length', 0))
        with open(dest_path, 'wb') as file:
            downloaded = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded += len(chunk)
                    percent = int(downloaded * 100 / total) if total else 0
                    sys.stdout.write(f"\rDownloading {os.path.basename(dest_path)}: {percent}%")
                    sys.stdout.flush()
    print("\nDownload complete.")

def get_console_dat(console, dat_dir):
    DAT_MAP = {
        'nds': 'Nintendo - Nintendo DS',
        'gba': 'Nintendo - Game Boy Advance',
        'gb': 'Nintendo - Game Boy',
        'gbc': 'Nintendo - Game Boy Color',
        'snes': 'Nintendo - Super Nintendo Entertainment System',
        'nes': 'Nintendo - Nintendo Entertainment System',
        'md': 'Sega - Mega Drive - Genesis',
        'sms': 'Sega - Master System',
        'gg': 'Sega - Game Gear'
    }
    name = DAT_MAP.get(console)
    if not name:
        print(f"No known DAT mapping for {console}")
        return None
    local_path = Path(dat_dir) / f"{name}.dat"
    if not local_path.exists():
        url = f"{LIBRETRO_DATABASE_REPO}/{urllib.parse.quote(name)}.dat"
        print(f"Downloading DAT for {console}...")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        download_with_progress(url, local_path)
    return local_path

def load_dat_file(dat_path):
    print(f"Loading DAT file: {dat_path}")
    hash_name_map = {}
    try:
        with open(dat_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('rom') and 'sha1' in line:
                    parts = line.split('sha1')
                    sha1 = parts[1].split()[0].strip(')"').lower()
                    name_part = line.split('name')[1].split('size')[0].strip()
                    name = name_part.strip('="')
                    hash_name_map[sha1] = name
        print(f"Loaded {len(hash_name_map)} hashes.")
    except Exception as e:
        print(f"Failed to parse {dat_path}: {e}")
    return hash_name_map

def try_fetch_image(url, output_path):
    try:
        r = requests.get(url)
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            img = img.resize((128, 115))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)
            print(f"Saved: {output_path}")
            return True
        else:
            print(f"Invalid image or not found at {url}")
    except Exception as e:
        print(f"Error fetching image from {url}: {e}")
    return False

def fetch_boxart(name, repo_list, boxart_dir, sha1, rom_path, error_log=None):
    output_path = boxart_dir / (rom_path.name + '.png')
    if output_path.exists() and output_path.stat().st_size > 20000:
        print(f"Boxart already exists: {output_path}")
        return

    base_name = Path(name).with_suffix('').name.replace('&', '_')
    original_name = base_name
    attempts = [base_name]

    simplified = re.sub(r'\(([^)]+?),.*?\)', r'(\1)', base_name)
    if simplified != base_name:
        attempts.append(simplified)

    rev_stripped = re.sub(r'\s*\(Rev[^)]+\)', '', base_name).strip()
    if rev_stripped != base_name:
        attempts.append(rev_stripped)

    variant_stripped = re.sub(r'\s*\((Rev|Beta|Proto)[^)]+\)', '', base_name).strip()
    if variant_stripped != base_name and variant_stripped not in attempts:
        attempts.append(variant_stripped)

    for attempt in attempts:
        encoded = urllib.parse.quote(attempt + '.png')
        for repo in repo_list:
            url = f"https://github.com/libretro-thumbnails/{repo}/raw/master/Named_Boxarts/{encoded}"
            print(f"Trying: {url}")
            if try_fetch_image(url, output_path):
                return

    print("Could not find box art using any known fallback")
    if error_log:
        error_log.write(f"{rom_path.name} | {sha1} | {original_name}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom-dir", required=True)
    parser.add_argument("--sdcard-dir", required=True)
    parser.add_argument("--rename", action="store_true")
    parser.add_argument("--errors", action="store_true")
    args = parser.parse_args()

    roms = find_roms(args.rom_dir)
    if not roms:
        print("No ROMs found.")
        return

    dat_dir = Path(args.sdcard_dir).expanduser() / 'no-intro'
    boxart_dir = Path(args.sdcard_dir).expanduser() / '_nds/TWiLightMenu/boxart'
    hash_maps = {}
    error_log = open("errors.txt", "w") if args.errors else None

    for rom_path, system in roms:
        print(f"Processing {rom_path}")
        rom_sha1 = sha1_hash(rom_path)
        if system not in hash_maps:
            dat_path = get_console_dat(system, dat_dir)
            if dat_path:
                hash_maps[system] = load_dat_file(dat_path)
            else:
                print(f"Skipping {system}: No DAT")
                continue

        name = hash_maps[system].get(rom_sha1)
        if not name:
            print(f"No match in DAT: {rom_path.name}")
            continue

        if args.rename:
            new_path = rom_path.with_name(name + rom_path.suffix)
            if new_path != rom_path:
                print(f"Renaming {rom_path.name} → {new_path.name}")
                rom_path.rename(new_path)
                rom_path = new_path

        repo_list = [LIBRETRO_THUMBNAIL_MAP.get(system)]
        if system == 'gbc':
            repo_list.append(LIBRETRO_THUMBNAIL_MAP.get('gb'))

        fetch_boxart(name, repo_list, boxart_dir, rom_sha1, rom_path, error_log)

    if error_log:
        error_log.close()

if __name__ == "__main__":
    main()
