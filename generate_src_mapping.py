# -*- coding: utf-8 -*-
import re
import requests
import sys
import io

# from lululla for test @s3no


def extract_info_from_filename(filename):
    """Extract SRC and other info from PNG filename"""
    pattern = r'(\d+_\d+_\d+_\d+_[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+_\d+_\d+_\d+)_small\.png'
    match = re.match(pattern, filename)
    if match:
        return match.group(1)
    return None


def get_satellite_positions(src_code):
    """Map SRC codes to satellite positions"""
    satellite_map = {
        'F01': '23.5E|16.0E|13.0E|0.8W',
        'F02': '13.0E|0.8W',
        'F03': '23.5E|13.0E',
    }
    parts = src_code.split('_')
    if len(parts) >= 5:
        provider_code = parts[4]
        for code, positions in satellite_map.items():
            if code in provider_code:
                return positions
    return "Satellite not found"


def get_channel_name(src_code):
    """Retrieve channel name from repository or mapping"""
    channel_map = {
        '1_0_16_105_F01_20CB_EEEE0000_0_0_0': 'Filmbox Premium',
        '1_0_1_2C85_F01_20CB_EEEE0000_0_0_0': 'RAI 1',
        '1_0_1_2C89_F01_20CB_EEEE0000_0_0_0': 'RAI 2',
    }
    return channel_map.get(src_code, "Channel %s" % src_code)


def scrape_srf_files():
    """Download list of files from GitHub folder"""
    url = "https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF"
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'SRC-Mapping-Generator'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        files = response.json()
        png_files = [file['name']
                     for file in files if file['name'].endswith('.png')]
        return png_files
    except Exception as e:
        print("Error retrieving files: %s" % str(e))
        return []


def generate_mapping_file():
    """Generate the final mapping file"""
    print("Retrieving list of PNG files from SRF folder...")
    png_files = scrape_srf_files()
    if not png_files:
        print("No PNG files found")
        return
    print("Found %d PNG files" % len(png_files))

    mappings = []
    for png_file in png_files:
        src_code = extract_info_from_filename(png_file)
        if src_code:
            channel_name = get_channel_name(src_code)
            satellite_positions = get_satellite_positions(src_code)
            mapping_line = "%s - %s - %s" % (src_code,
                                             channel_name, satellite_positions)
            mappings.append(mapping_line)
            print("Processed: %s" % src_code)

    # Sort alphabetically by channel name
    mappings.sort(key=lambda x: x.split(' - ')[1].lower())

    # Write to file compatible with Python 2 and 3
    with io.open('src_mapping.txt', 'w', encoding='utf-8') as f:
        for line in mappings:
            f.write(line + '\n')

    print("\nFile generated with %d entries" % len(mappings))


if __name__ == "__main__":
    generate_mapping_file()
