# -*- coding: utf-8 -*-
# generate_src_mapping_complete.py
import requests
import re
import zipfile
import io
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


def download_and_parse_vhannibal():
    """Download Vhannibal Motor and parse lamedb and .tv files"""
    vhannibal_url = "https://www.vhannibal.net/download_setting.php?id=3&action=download"
    
    print("\nDownloading Vhannibal Motor settings...")
    
    try:
        response = requests.get(vhannibal_url, timeout=60)
        
        if response.status_code != 200:
            print("Failed to download Vhannibal: HTTP " + str(response.status_code))
            return {}
        
        print("Downloaded " + str(len(response.content)) + " bytes")
        
        vhannibal_data = {}
        
        # Extract ZIP
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            # Parse lamedb if exists
            if 'lamedb' in zip_file.namelist():
                with zip_file.open('lamedb') as f:
                    content = f.read().decode('utf-8', errors='ignore')
                
                print("lamedb size: " + str(len(content)) + " bytes")
                vhannibal_data.update(parse_lamedb(content))
            
            # Parse all .tv files
            tv_files_count = 0
            for filename in zip_file.namelist():
                if filename.endswith('.tv') or filename.endswith('.radio'):
                    with zip_file.open(filename) as f:
                        file_content = f.read().decode('utf-8', errors='ignore')
                    
                    parsed_tv = parse_tv_file(file_content)
                    for src, name in parsed_tv.items():
                        if src not in vhannibal_data:
                            vhannibal_data[src] = name
                    tv_files_count += 1
            
            print("Parsed " + str(tv_files_count) + " .tv/.radio files")
        
        print("Total unique SRCs from Vhannibal: " + str(len(vhannibal_data)))
        
        # Convert to same format as XML data
        vhannibal_formatted = {}
        for src_png, channel_name in vhannibal_data.items():
            vhannibal_formatted[src_png] = {
                'name': channel_name,
                'satellites': set(),
                'channel_id': '',
                'source': 'vhannibal'
            }
        
        return vhannibal_formatted
        
    except Exception as e:
        print("Error downloading/parsing Vhannibal: " + str(e))
        return {}


def parse_lamedb(content):
    """Parse lamedb format to extract SRC -> channel name"""
    src_to_name = {}
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for Service Reference (format: 0317:0dde0000:0107:217c:1:0)
        if re.match(r'^[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9]:[0]$', line):
            src_enigma = line
            
            # Next line should be channel name
            if i + 1 < len(lines):
                channel_name = lines[i + 1].strip()
                
                # Skip lines until we find 'p:' (provider)
                j = i + 2
                while j < len(lines) and not lines[j].strip().startswith('p:'):
                    j += 1
                
                # Convert Enigma2 format to PNG
                src_png = convert_enigma_to_png(src_enigma)
                
                if src_png and channel_name and channel_name not in ['', 'p:']:
                    src_to_name[src_png] = channel_name
                
                i = j + 1 if j < len(lines) else j
            else:
                i += 1
        else:
            i += 1
    
    return src_to_name


def parse_tv_file(content):
    """Parse .tv file to extract SRC -> channel name"""
    src_to_name = {}
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for #SERVICE line
        if line.startswith('#SERVICE'):
            # Extract service reference
            match = re.search(r'#SERVICE\s+([0-9a-fA-F:]+)', line)
            if match:
                src_enigma = match.group(1)
                
                # Look for channel name in next lines
                j = i + 1
                while j < len(lines) and j < i + 5:  # Check next 5 lines
                    next_line = lines[j].strip()
                    if next_line.startswith('#DESCRIPTION'):
                        channel_name = next_line.replace('#DESCRIPTION', '').strip()
                        # Skip separator lines
                        if channel_name and not channel_name.startswith('---') and not channel_name.startswith('==='):
                            src_png = convert_enigma_to_png(src_enigma)
                            if src_png:
                                src_to_name[src_png] = channel_name
                            break
                    j += 1
                
                i += 1
            else:
                i += 1
        else:
            i += 1
    
    return src_to_name


def convert_enigma_to_png(enigma_src):
    """Convert Enigma2 SRC format to PNG format"""
    # Format: 0317:0dde0000:0107:217c:1:0
    # PNG format: 1_0_1_9_1_1_A00000_0_0_0
    
    parts = enigma_src.split(':')
    if len(parts) != 6:
        return None
    
    try:
        # Hex to decimal conversion
        service_id_hex = parts[0]
        namespace_hex = parts[1]
        transport_stream_id_hex = parts[2]
        original_network_id_hex = parts[3]
        
        # Convert hex to decimal
        service_id = str(int(service_id_hex, 16))
        namespace = namespace_hex.upper()
        transport_stream_id = str(int(transport_stream_id_hex, 16))
        original_network_id = str(int(original_network_id_hex, 16))
        
        # Build PNG format (service type is always 1 for TV)
        src_png = "1_0_" + service_id + "_" + transport_stream_id + "_" + original_network_id + "_" + namespace + "_0_0_0"
        
        return src_png
        
    except ValueError:
        return None


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


def generate_complete_mapping():
    print("=" * 80)
    print("GENERATING COMPLETE SRC MAPPING - ALL SOURCES")
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

    # 3. Download and parse Vhannibal Motor
    vhannibal_data = download_and_parse_vhannibal()
    
    # 4. Combine ALL data sources
    print("\nCombining all data sources...")
    all_channel_data = {}
    
    # First: XML data (high priority)
    for src, info in xml_data.items():
        all_channel_data[src] = info
    
    # Second: Vhannibal data (override only if not present)
    for src, info in vhannibal_data.items():
        if src not in all_channel_data:
            all_channel_data[src] = info
        else:
            # Update name if Vhannibal has better name
            if len(info['name']) > len(all_channel_data[src]['name']):
                all_channel_data[src]['name'] = info['name']
                all_channel_data[src]['source'] = 'vhannibal'
    
    print("Total unique SRCs from all sources: " + str(len(all_channel_data)))
    
    # 5. Process PNG paths
    print("\nProcessing PNG paths...")
    png_srcs = {}
    
    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src and satellite:
            if src not in png_srcs:
                png_srcs[src] = set()
            png_srcs[src].add(satellite)
    
    print("Found " + str(len(png_srcs)) + " unique SRCs in PNG directories")
    
    # 6. Generate files
    print("\nGenerating output files...")
    
    # File 1: src_mapping.txt
    mapping_lines = []
    
    # File 2: picons_missing.txt (PNGs that don't exist but should)
    missing_picons = []
    
    # Counters
    xml_matches = 0
    vhannibal_matches = 0
    unknown_count = 0
    
    # For each SRC in PNGs
    for src_png in sorted(png_srcs.keys()):
        png_satellites = png_srcs[src_png]
        
        # Determine name and SNP
        snp_code = "UNKN"
        channel_name = ""
        all_satellites = set(png_satellites)
        source = "unknown"
        
        # Check in all sources
        if src_png in all_channel_data:
            info = all_channel_data[src_png]
            channel_name = info['name']
            snp_code = create_snp_code(channel_name)
            all_satellites.update(info['satellites'])
            source = info['source']
            
            if source == 'xml':
                xml_matches += 1
            elif source == 'vhannibal':
                vhannibal_matches += 1
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
        satellites_str = '|'.join(sorted_sats) if sorted_sats else 'Unknown'
        
        mapping_lines.append(src_png + " - " + snp_code + " - " + satellites_str)
    
    # Find channels that exist in sources but NOT in PNGs (missing picons)
    for src_png, info in all_channel_data.items():
        if src_png not in png_srcs:
            missing_picons.append({
                'src': src_png,
                'name': info['name'],
                'source': info['source']
            })
    
    # 7. Write files
    print("\nWriting files...")
    
    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
        f.write("# Total entries: " + str(len(mapping_lines)) + "\n")
        f.write("# XML matches: " + str(xml_matches) + "\n")
        f.write("# Vhannibal matches: " + str(vhannibal_matches) + "\n")
        f.write("# Unknown: " + str(unknown_count) + "\n")
        total_matches = xml_matches + vhannibal_matches
        coverage = (total_matches / len(png_srcs) * 100) if png_srcs else 0
        f.write("# Coverage: " + str(round(coverage, 1)) + "%\n")
        f.write("# Generated from: rytec.channels.xml + Vhannibal Motor + PNG directories\n")
        f.write("# Format example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")
        
        for line in mapping_lines:
            f.write(line + "\n")
    
    # File 2: picons_missing.txt (FINALLY!)
    with open('picons_missing.txt', 'w', encoding='utf-8') as f:
        f.write("# PICONS MISSING IN REPOSITORY\n")
        f.write("# =============================\n")
        f.write("# Total missing picons: " + str(len(missing_picons)) + "\n")
        f.write("# These channels exist in XML/Vhannibal but don't have PNG files in repository\n")
        f.write("# You should create PNG logos for these channels\n")
        f.write("# Generated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
        
        # Sort by name for easier reading
        missing_picons_sorted = sorted(missing_picons, key=lambda x: x['name'])
        
        for item in missing_picons_sorted:
            f.write("SRC: " + item['src'] + "\n")
            f.write("Channel: " + item['name'] + "\n")
            f.write("Source: " + item['source'] + "\n")
            f.write("Suggested PNG name: " + item['src'] + ".png\n")
            f.write("Suggested path: logos/E2LIST/Unknown/" + item['src'] + ".png\n")
            f.write("-" * 50 + "\n\n")
    
    # File 3: summary.txt
    with open('summary.txt', 'w', encoding='utf-8') as f:
        f.write("# SUMMARY REPORT\n")
        f.write("# ===============\n")
        f.write("Generated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
        f.write("Execution time: " + str(round(time.time() - start_time, 1)) + " seconds\n\n")
        
        f.write("PNG SRCs in repository: " + str(len(png_srcs)) + "\n")
        f.write("SRCs from XML: " + str(len([v for v in all_channel_data.values() if v['source'] == 'xml'])) + "\n")
        f.write("SRCs from Vhannibal: " + str(len([v for v in all_channel_data.values() if v['source'] == 'vhannibal'])) + "\n")
        f.write("Total unique SRCs from all sources: " + str(len(all_channel_data)) + "\n\n")
        
        f.write("XML matches: " + str(xml_matches) + " (" + str(round(xml_matches/len(png_srcs)*100, 1)) + "%)\n")
        f.write("Vhannibal matches: " + str(vhannibal_matches) + " (" + str(round(vhannibal_matches/len(png_srcs)*100, 1)) + "%)\n")
        f.write("Unknown SRCs: " + str(unknown_count) + " (" + str(round(unknown_count/len(png_srcs)*100, 1)) + "%)\n")
        f.write("TOTAL COVERAGE: " + str(round(coverage, 1)) + "%\n\n")
        
        f.write("PICONS MISSING: " + str(len(missing_picons)) + "\n")
        f.write("(Check picons_missing.txt for details)\n")
    
    # 8. Final statistics
    print("\n" + "=" * 80)
    print("FINAL RESULTS - ALL SOURCES")
    print("=" * 80)
    
    print("Processing completed in " + str(round(time.time() - start_time, 1)) + " seconds")
    print("Total PNG SRCs: " + str(len(png_srcs)))
    print("XML matches: " + str(xml_matches) + " (" + str(round(xml_matches/len(png_srcs)*100, 1)) + "%)")
    print("Vhannibal matches: " + str(vhannibal_matches) + " (" + str(round(vhannibal_matches/len(png_srcs)*100, 1)) + "%)")
    print("Unknown SRCs: " + str(unknown_count) + " (" + str(round(unknown_count/len(png_srcs)*100, 1)) + "%)")
    print("TOTAL COVERAGE: " + str(round(coverage, 1)) + "%")
    print("PICONS MISSING: " + str(len(missing_picons)) + " (check picons_missing.txt)")
    
    # Examples
    print("\nSample matches (first 3):")
    for line in mapping_lines[:3]:
        print("  " + line)
    
    if missing_picons:
        print("\nSample MISSING picons (first 3):")
        for item in missing_picons[:3]:
            print("  SRC: " + item['src'])
            print("  Channel: " + item['name'])
            print("  Source: " + item['source'])
    
    print("\nFiles created:")
    print("  1. src_mapping.txt - Main mapping file")
    print("  2. picons_missing.txt - PNGs to create for repository (FINALLY!)")
    print("  3. summary.txt - Complete statistics")
    
    print("\nSUCCESS! Now you have:")
    print("  - Complete mapping with Vhannibal data")
    print("  - Accurate list of missing PNGs")
    print("  - Much better coverage!")


if __name__ == "__main__":
    generate_complete_mapping()
