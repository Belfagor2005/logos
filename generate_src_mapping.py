# -*- coding: utf-8 -*-
# generate_src_mapping_fixed.py
import requests
import re
from collections import defaultdict
import time


def get_png_paths():
    """Get all PNG paths from txt/logos.txt"""
    txt_url = "https://raw.githubusercontent.com/Belfagor2005/logos/refs/heads/main/txt/logos.txt"

    try:
        response = requests.get(txt_url, timeout=30)
        lines = response.text.strip().split('\n')

        # Filter only lines ending with .png and containing E2LIST
        png_paths = []
        for line in lines:
            if line.strip().endswith('.png') and 'E2LIST' in line:
                png_paths.append(line.strip())

        print("Found " + str(len(png_paths)) + " PNG paths in logos.txt")
        return png_paths

    except Exception as e:
        print("Error getting logos.txt: " + str(e))
        return []


def extract_src_and_satellite_from_path(path):
    """Extract SRC and satellite position from PNG path"""
    parts = path.split('/')
    
    # Extract satellite from directory structure
    satellite = ""
    if len(parts) >= 3:
        for part in parts:
            if re.search(r'\d+\.\d+[EW]', part):
                satellite = part
                break
    
    # Extract SRC from filename
    filename = parts[-1]
    if filename.endswith('.png'):
        src = filename[:-4]
    else:
        src = filename
    
    return src, satellite


def parse_xml_for_channels():
    """Parse rytec.channels.xml"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print("XML size: " + str(len(content)) + " bytes")
        
        # Pattern: <!-- sat --><channel id="id">src</channel><!-- name -->
        pattern = r'<!--\s*([^>]+?)\s*-->\s*<channel id="([^"]+)">([^<]+)</channel>\s*(?:<!--\s*([^>]+?)\s*-->)?'
        matches = re.findall(pattern, content)
        
        print("Found " + str(len(matches)) + " channel entries in XML")
        
        src_to_info = {}
        
        for before_comment, channel_id, service_ref, after_comment in matches:
            # Extract satellite
            satellite = ""
            sat_match = re.search(r'(\d+(?:\.\d+)?[EW])', before_comment)
            if sat_match:
                satellite = sat_match.group(1)
            
            # Extract name
            channel_name = after_comment.strip() if after_comment else channel_id
            
            # Convert SRC
            service_ref = service_ref.strip().rstrip(':')
            src_png = service_ref.replace(':', '_')
            
            # Save info
            if src_png not in src_to_info:
                src_to_info[src_png] = {
                    'name': channel_name,
                    'satellites': set(),
                    'channel_id': channel_id,
                    'source': 'xml'
                }
            
            if satellite:
                src_to_info[src_png]['satellites'].add(satellite)
        
        print("Parsed " + str(len(src_to_info)) + " unique SRCs from XML")
        return src_to_info

    except Exception as e:
        print("Error parsing XML: " + str(e))
        return {}


def create_snp_code(channel_name):
    """Create SNP code from channel name"""
    if not channel_name or channel_name.lower() in ['unknown', 'no_epg', '']:
        return "UNKN"
    
    # Remove HD, TV, etc. extensions
    clean = re.sub(r'\b(?:HD|FHD|UHD|4K|SD|HEVC|TV|CHANNEL|LIVE)\b', '', channel_name, flags=re.IGNORECASE)
    
    # Take only letters
    letters = re.findall(r'[a-zA-Z]', clean)
    clean = ''.join(letters)
    
    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')
    
    return "CHNL"


def generate_mapping():
    print("=" * 80)
    print("GENERATING SRC MAPPING WITH MISSING PICONS")
    print("=" * 80)
    
    start_time = time.time()

    # 1. Get PNG paths
    print("Getting PNG paths from logos.txt...")
    png_paths = get_png_paths()

    if not png_paths:
        print("No PNG paths found!")
        return

    # 2. Parse XML (rytec)
    print("\nParsing XML from rytec.channels.xml...")
    xml_data = parse_xml_for_channels()

    if not xml_data:
        print("ERROR: Failed to parse XML!")
        return

    # 3. Process PNG paths
    print("\nProcessing PNG paths...")
    png_srcs = {}
    
    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src and satellite:
            if src not in png_srcs:
                png_srcs[src] = set()
            png_srcs[src].add(satellite)
    
    print("Found " + str(len(png_srcs)) + " unique SRCs in PNG directories")
    
    # 4. Generate files
    print("\nGenerating output files...")
    
    # File 1: src_mapping.txt
    mapping_lines = []
    
    # File 2: picons_missing.txt (PNGs that don't exist but should)
    missing_picons = []
    
    # Counters
    xml_matches = 0
    unknown_count = 0
    
    # For each SRC in PNGs
    for src_png in sorted(png_srcs.keys()):
        png_satellites = png_srcs[src_png]
        
        # Determine name and SNP
        snp_code = "UNKN"
        channel_name = ""
        all_satellites = set(png_satellites)
        
        # Check in XML
        if src_png in xml_data:
            info = xml_data[src_png]
            channel_name = info['name']
            snp_code = create_snp_code(channel_name)
            all_satellites.update(info['satellites'])
            xml_matches += 1
        else:
            unknown_count += 1
        
        # Sort satellites: W negative, E positive
        def sat_sort_key(s):
            match = re.match(r'(\d+\.?\d*)([EW])', s)
            if match:
                num = float(match.group(1))
                return -num if match.group(2) == 'W' else num
            return 999
        
        sorted_sats = sorted(all_satellites, key=sat_sort_key)
        satellites_str = '|'.join(sorted(sats)) if sorted_sats else 'Unknown'
        
        mapping_lines.append(src_png + " - " + snp_code + " - " + satellites_str)
    
    # Find channels that exist in XML but NOT in PNGs (missing picons)
    for src_png, info in xml_data.items():
        if src_png not in png_srcs:
            missing_picons.append({
                'src': src_png,
                'name': info['name'],
                'satellites': list(info['satellites'])[0] if info['satellites'] else 'Unknown'
            })
    
    print("\nStatistics:")
    print("  Total PNG SRCs: " + str(len(png_srcs)))
    print("  XML matches: " + str(xml_matches))
    print("  Unknown: " + str(unknown_count))
    print("  Missing picons found: " + str(len(missing_picons)))
    
    # 5. Write files
    print("\nWriting files...")
    
    # File 1: src_mapping.txt
    try:
        with open('src_mapping.txt', 'w', encoding='utf-8') as f:
            f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
            f.write("# Total entries: " + str(len(mapping_lines)) + "\n")
            f.write("# XML matches: " + str(xml_matches) + "\n")
            f.write("# Unknown: " + str(unknown_count) + "\n")
            coverage = (xml_matches / len(png_srcs) * 100) if png_srcs else 0
            f.write("# Coverage: " + str(round(coverage, 1)) + "%\n")
            f.write("# Generated from: rytec.channels.xml + PNG directories\n")
            f.write("# Format example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")
            
            for line in mapping_lines:
                f.write(line + "\n")
        print("✓ Created: src_mapping.txt")
    except Exception as e:
        print("✗ Error creating src_mapping.txt: " + str(e))
    
    # File 2: picons_missing.txt
    try:
        with open('picons_missing.txt', 'w', encoding='utf-8') as f:
            f.write("# PICONS MISSING IN REPOSITORY\n")
            f.write("# =============================\n")
            f.write("# Total missing picons: " + str(len(missing_picons)) + "\n")
            f.write("# These channels exist in XML but don't have PNG files in repository\n")
            f.write("# You should create PNG logos for these channels\n")
            f.write("# Generated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
            
            # Group by first letter for better organization
            missing_by_letter = defaultdict(list)
            for item in missing_picons:
                first_letter = item['name'][0].upper() if item['name'] else '?'
                missing_by_letter[first_letter].append(item)
            
            # Write organized by letter
            for letter in sorted(missing_by_letter.keys()):
                f.write("\n## LETTER " + letter + " (" + str(len(missing_by_letter[letter])) + " channels)\n\n")
                
                for item in sorted(missing_by_letter[letter], key=lambda x: x['name']):
                    f.write("SRC: " + item['src'] + "\n")
                    f.write("Channel: " + item['name'] + "\n")
                    f.write("Satellite: " + item['satellites'] + "\n")
                    f.write("Suggested PNG: " + item['src'] + ".png\n")
                    f.write("---\n")
        
        print("✓ Created: picons_missing.txt")
        print("  Contains " + str(len(missing_picons)) + " missing picons")
        
        # Show sample
        if missing_picons:
            print("\nSample missing picons (first 5):")
            for item in missing_picons[:5]:
                print("  " + item['src'] + " - " + item['name'])
    except Exception as e:
        print("✗ Error creating picons_missing.txt: " + str(e))
        import traceback
        traceback.print_exc()
    
    # File 3: simple_missing_list.txt (just SRCs for easy copy)
    try:
        with open('simple_missing_list.txt', 'w', encoding='utf-8') as f:
            f.write("# Simple list of missing PNG SRCs\n")
            f.write("# Total: " + str(len(missing_picons)) + "\n\n")
            
            for item in missing_picons:
                f.write(item['src'] + "\n")
        
        print("✓ Created: simple_missing_list.txt")
    except Exception as e:
        print("✗ Error creating simple_missing_list.txt: " + str(e))
    
    # 6. Final statistics
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    print("Processing completed in " + str(round(time.time() - start_time, 1)) + " seconds")
    print("Total PNG SRCs: " + str(len(png_srcs)))
    print("XML matches: " + str(xml_matches) + " (" + str(round(xml_matches/len(png_srcs)*100, 1)) + "%)")
    print("Unknown SRCs: " + str(unknown_count) + " (" + str(round(unknown_count/len(png_srcs)*100, 1)) + "%)")
    print("TOTAL COVERAGE: " + str(round(coverage, 1)) + "%")
    print("MISSING PICONS: " + str(len(missing_picons)) + " (check picons_missing.txt)")
    
    print("\nFiles created:")
    print("  1. src_mapping.txt")
    print("  2. picons_missing.txt")
    print("  3. simple_missing_list.txt")
    
    print("\nNEXT STEPS:")
    print("  1. Review picons_missing.txt for channels to create")
    print("  2. Create missing PNG files")
    print("  3. Add them to appropriate E2LIST/satellite directories")


if __name__ == "__main__":
    generate_mapping()
