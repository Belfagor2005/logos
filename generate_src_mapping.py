# -*- coding: utf-8 -*-
import re
import json
from pathlib import Path
import io

def load_channel_mappings():
    """Load channel mappings from a JSON file"""
    mapping_file = Path("channel_mappings.json")
    
    if mapping_file.exists():
        with io.open(mapping_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Default mappings if file does not exist
    return {
        "filmbox premium": {
            "src_pattern": r".*F01.*",
            "snp": "FBOX",
            "satellites": ["23.5E", "16.0E", "13.0E", "0.8W"]
        }
    }

def scan_srf_directory():
    """Scan the local SRF directory"""
    srf_path = Path("logos/SRF")
    
    if not srf_path.exists():
        print("Directory {} not found".format(srf_path))
        return []
    
    png_files = list(srf_path.glob("*_small.png"))
    print("Found {} PNG files in {}".format(len(png_files), srf_path))
    return png_files

def extract_src_from_filename(filename):
    """Extract SRC code from the file name"""
    # Example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0_small.png
    match = re.match(r'(.+)_small\.png$', filename)
    if match:
        return match.group(1)
    return None

def match_channel_info(src_code, channel_mappings):
    """Find channel info based on SRC code"""
    for channel_name, info in channel_mappings.items():
        if re.match(info["src_pattern"], src_code):
            return {
                "name": channel_name,
                "snp": info["snp"],
                "satellites": "|".join(info["satellites"])
            }
    
    # Default if no match found
    return {
        "name": "Unknown Channel ({})".format(src_code),
        "snp": "UNKN",
        "satellites": "Satellite not found"
    }

def generate_mapping():
    """Main function to generate the mapping file"""
    # Load configurations
    channel_mappings = load_channel_mappings()
    
    # Scan files
    png_files = scan_srf_directory()
    
    if not png_files:
        print("No files found. Creating empty mapping file.")
        with io.open("src_mapping.txt", "w", encoding="utf-8") as f:
            f.write("# SRC - SNP - Satellites mapping file\n")
        return
    
    # Process each file
    mappings = []
    for png_file in png_files:
        src_code = extract_src_from_filename(png_file.name)
        if src_code:
            channel_info = match_channel_info(src_code, channel_mappings)
            line = "{} - {} - {}".format(src_code, channel_info['name'], channel_info['satellites'])
            mappings.append(line)
    
    # Sort mappings alphabetically
    mappings.sort()
    
    # Write to file
    with io.open("src_mapping.txt", "w", encoding="utf-8") as f:
        f.write("# SRC - Channel Name - Satellite Positions mapping file\n")
        f.write("# Automatically generated\n\n")
        for line in mappings:
            f.write(line + "\n")
    
    print("Mapping file generated with {} entries".format(len(mappings)))

if __name__ == "__main__":
    generate_mapping()
