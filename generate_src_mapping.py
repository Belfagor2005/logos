# -*- coding: utf-8 -*-
# generate_src_mapping_fixed.py
import io
import zipfile
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


# -*- coding: utf-8 -*-
# generate_src_mapping_fixed.py


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


def download_vhannibal():
    """Download Vhannibal and extract channel data"""
    vhannibal_url = "https://www.vhannibal.net/download_setting.php?id=3&action=download"

    print("\nDownloading Vhannibal Motor...")

    try:
        response = requests.get(vhannibal_url, timeout=60)

        if response.status_code != 200:
            print("Failed to download Vhannibal: HTTP " +
                  str(response.status_code))
            return {}

        print("Downloaded " + str(len(response.content)) + " bytes")

        vhannibal_data = {}

        # Try to parse as ZIP
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # Look for lamedb
                if 'lamedb' in zip_file.namelist():
                    with zip_file.open('lamedb') as f:
                        content = f.read().decode('utf-8', errors='ignore')

                    # Parse lamedb
                    lines = content.split('\n')
                    for i in range(len(lines)):
                        line = lines[i].strip()
                        # Look for service reference (format:
                        # 0317:0dde0000:0107:217c:1:0)
                        if ':' in line and len(line.split(':')) == 6:
                            parts = line.split(':')
                            if len(parts[0]) == 4 and len(parts[1]) == 8:
                                # Next line is channel name
                                if i + 1 < len(lines):
                                    channel_name = lines[i + 1].strip()
                                    if channel_name and not channel_name.startswith(
                                            'p:'):
                                        # Convert to PNG format
                                        try:
                                            # Hex to decimal
                                            service_id = str(int(parts[0], 16))
                                            transport_id = str(
                                                int(parts[2], 16))
                                            network_id = str(int(parts[3], 16))
                                            namespace = parts[1].upper()

                                            src_png = "1_0_" + service_id + "_" + transport_id + \
                                                "_" + network_id + "_" + namespace + "_0_0_0"

                                            vhannibal_data[src_png] = {
                                                'name': channel_name,
                                                'satellites': set(),
                                                'source': 'vhannibal'
                                            }
                                        except ValueError:
                                            pass

                # Also parse .tv files
                tv_count = 0
                for filename in zip_file.namelist():
                    if filename.endswith('.tv'):
                        with zip_file.open(filename) as f:
                            tv_content = f.read().decode('utf-8', errors='ignore')

                        # Parse #SERVICE lines
                        service_lines = re.findall(
                            r'#SERVICE\s+([0-9a-fA-F:]+)', tv_content)
                        for service in service_lines:
                            # Convert service reference
                            if service.count(':') == 5:
                                parts = service.split(':')
                                try:
                                    service_id = str(int(parts[0], 16))
                                    transport_id = str(int(parts[2], 16))
                                    network_id = str(int(parts[3], 16))
                                    namespace = parts[1].upper()

                                    src_png = "1_0_" + service_id + "_" + transport_id + \
                                        "_" + network_id + "_" + namespace + "_0_0_0"

                                    # Try to find channel name
                                    name_match = re.search(
                                        r'#DESCRIPTION\s+(.+)', tv_content)
                                    if name_match:
                                        channel_name = name_match.group(
                                            1).strip()
                                        if channel_name and not channel_name.startswith(
                                                '---'):
                                            vhannibal_data[src_png] = {
                                                'name': channel_name,
                                                'satellites': set(),
                                                'source': 'vhannibal_tv'
                                            }
                                            tv_count += 1
                                except (ValueError, IndexError):
                                    pass

                print("Parsed " + str(tv_count) + " channels from .tv files")

        except zipfile.BadZipFile:
            print("Not a valid ZIP file, trying to parse as raw text...")
            # Try to parse as raw lamedb
            content = response.content.decode('utf-8', errors='ignore')
            if 'p:' in content and len(content) > 10000:
                print("Detected lamedb format")
                # Simple parsing logic here

        print("Found " + str(len(vhannibal_data)) +
              " unique channels in Vhannibal")

        # Show samples
        if vhannibal_data:
            print("\nSample Vhannibal channels (first 5):")
            samples = list(vhannibal_data.items())[:5]
            for src, info in samples:
                print("  " + src[:40] + "... -> " + info['name'])

        return vhannibal_data

    except Exception as e:
        print("Error with Vhannibal: " + str(e))
        return {}


def create_snp_code(channel_name):
    """Create SNP code from channel name"""
    if not channel_name or channel_name.lower() in ['unknown', 'no_epg', '']:
        return "UNKN"

    # Remove common extensions
    clean = re.sub(r'\b(?:HD|FHD|UHD|4K|SD|HEVC|TV|CHANNEL)\b',
                   '', channel_name, flags=re.IGNORECASE)

    # Take only letters and numbers
    clean = re.sub(r'[^a-zA-Z0-9]', '', clean)

    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')

    return "CHNL"


def generate_complete_mapping():
    print("=" * 80)
    print("GENERATING COMPLETE MAPPING (XML + VHANNIBAL)")
    print("=" * 80)

    start_time = time.time()

    # 1. Get PNG paths
    print("Getting PNG paths from logos.txt...")
    png_paths = get_png_paths()

    if not png_paths:
        print("No PNG paths found!")
        return

    # 2. Parse XML
    print("\nParsing XML from rytec.channels.xml...")
    xml_data = parse_xml_for_channels()

    # 3. Download Vhannibal
    vhannibal_data = download_vhannibal()

    # 4. Combine data sources
    print("\nCombining data sources...")
    all_channels = {}

    # Add XML data first
    for src, info in xml_data.items():
        all_channels[src] = info

    # Add Vhannibal data (overwrite if better name)
    for src, info in vhannibal_data.items():
        if src not in all_channels:
            all_channels[src] = info
        else:
            # Keep XML data, but could update if needed
            pass

    print("Total unique channels from all sources: " + str(len(all_channels)))

    # 5. Process PNG paths
    print("\nProcessing PNG paths...")
    png_dict = {}

    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src and satellite:
            if src not in png_dict:
                png_dict[src] = set()
            png_dict[src].add(satellite)

    print("Found " + str(len(png_dict)) + " unique SRCs in PNG directories")

    # 6. Generate mapping
    print("\nGenerating mapping...")

    mapping_lines = []
    missing_picons = []

    xml_matches = 0
    vhannibal_matches = 0
    unknown_count = 0

    # Process each PNG SRC
    for src in sorted(png_dict.keys()):
        satellites = png_dict[src]

        # Check in all sources
        if src in all_channels:
            channel_info = all_channels[src]
            channel_name = channel_info['name']
            snp_code = create_snp_code(channel_name)

            # Update source counters
            if channel_info['source'] == 'xml':
                xml_matches += 1
            elif channel_info['source'] in ['vhannibal', 'vhannibal_tv']:
                vhannibal_matches += 1

            # Add satellites from XML if available
            if 'satellites' in channel_info:
                satellites.update(channel_info['satellites'])
        else:
            snp_code = "UNKN"
            unknown_count += 1

        # Format satellites
        if satellites:
            # Sort: W negative, E positive
            def sat_sort_key(s):
                match = re.match(r'(\d+\.?\d*)([EW])', s)
                if match:
                    num = float(match.group(1))
                    return -num if match.group(2) == 'W' else num
                return 999

            sorted_sats = sorted(satellites, key=sat_sort_key)
            satellites_str = '|'.join(sorted_sats)
        else:
            satellites_str = 'Unknown'

        mapping_lines.append(src + " - " + snp_code + " - " + satellites_str)

    # Find channels that exist in sources but NOT in PNGs
    for src, info in all_channels.items():
        if src not in png_dict:
            missing_picons.append({
                'src': src,
                'name': info['name'],
                'source': info['source'],
                'satellite': list(info['satellites'])[0] if info.get('satellites') else 'Unknown'
            })

    # 7. Write files
    print("\nWriting files...")

    # File 1: src_mapping.txt
    try:
        with open('src_mapping.txt', 'w', encoding='utf-8') as f:
            f.write("# SRC - SNP - Satellite Positions\n")
            f.write("# Total entries: " + str(len(mapping_lines)) + "\n")
            f.write("# XML matches: " + str(xml_matches) + "\n")
            f.write("# Vhannibal matches: " + str(vhannibal_matches) + "\n")
            f.write("# Unknown: " + str(unknown_count) + "\n")

            total_matches = xml_matches + vhannibal_matches
            if png_dict:
                coverage = (total_matches / len(png_dict)) * 100
                f.write("# Coverage: " + str(round(coverage, 1)) + "%\n")

            f.write(
                "# Generated: " +
                time.strftime('%Y-%m-%d %H:%M:%S') +
                "\n")
            f.write("# Sources: rytec.channels.xml + Vhannibal Motor\n\n")

            for line in mapping_lines:
                f.write(line + "\n")

        print("✓ Created: src_mapping.txt")
    except Exception as e:
        print("✗ Error creating src_mapping.txt: " + str(e))

    # File 2: missing_picons.txt
    try:
        if missing_picons:
            with open('missing_picons.txt', 'w', encoding='utf-8') as f:
                f.write("# MISSING PICONS FOR REPOSITORY\n")
                f.write("# =============================\n")
                f.write("# These channels need PNG files\n")
                f.write("# Total missing: " + str(len(missing_picons)) + "\n")
                f.write(
                    "# Generated: " +
                    time.strftime('%Y-%m-%d %H:%M:%S') +
                    "\n\n")

                # Sort by source for organization
                missing_by_source = defaultdict(list)
                for item in missing_picons:
                    missing_by_source[item['source']].append(item)

                for source in sorted(missing_by_source.keys()):
                    items = missing_by_source[source]
                    f.write("\n## " + source.upper() +
                            " (" + str(len(items)) + " channels)\n\n")

                    for item in sorted(items, key=lambda x: x['name']):
                        f.write("SRC: " + item['src'] + "\n")
                        f.write("NAME: " + item['name'] + "\n")
                        f.write("SATELLITE: " + item['satellite'] + "\n")
                        f.write("PNG: " + item['src'] + ".png\n")
                        f.write("---\n")

            print("✓ Created: missing_picons.txt (" +
                  str(len(missing_picons)) + " entries)")
        else:
            with open('missing_picons.txt', 'w', encoding='utf-8') as f:
                f.write("# NO MISSING PICONS FOUND!\n")
                f.write("# All channels have PNG files.\n")
                f.write(
                    "# Generated: " +
                    time.strftime('%Y-%m-%d %H:%M:%S') +
                    "\n")

            print("✓ Created: missing_picons.txt (empty - all good!)")
    except Exception as e:
        print("✗ Error creating missing_picons.txt: " + str(e))
        import traceback
        traceback.print_exc()

    # File 3: summary.txt
    try:
        with open('summary.txt', 'w', encoding='utf-8') as f:
            f.write("# SUMMARY\n")
            f.write("# =======\n")
            f.write("Generated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
            f.write(
                "Time: " + str(round(time.time() - start_time, 1)) + " seconds\n\n")

            f.write("PNG SRCs in repository: " + str(len(png_dict)) + "\n")
            f.write("Channels in XML: " +
                    str(len([v for v in all_channels.values() if v['source'] == 'xml'])) +
                    "\n")
            f.write("Channels in Vhannibal: " + str(len([v for v in all_channels.values(
            ) if v['source'] in ['vhannibal', 'vhannibal_tv']])) + "\n")
            f.write("Total unique channels: " +
                    str(len(all_channels)) + "\n\n")

            f.write("XML matches: " + str(xml_matches) + "\n")
            f.write("Vhannibal matches: " + str(vhannibal_matches) + "\n")
            f.write("Unknown SRCs: " + str(unknown_count) + "\n")
            f.write("Missing picons: " + str(len(missing_picons)) + "\n\n")

            if png_dict:
                total_matches = xml_matches + vhannibal_matches
                coverage = (total_matches / len(png_dict)) * 100
                f.write("COVERAGE: " + str(round(coverage, 1)) + "%\n")

        print("✓ Created: summary.txt")
    except Exception as e:
        print("✗ Error creating summary.txt: " + str(e))

    # 8. Final output
    print("\n" + "=" * 80)
    print("COMPLETED")
    print("=" * 80)

    print("Time: " + str(round(time.time() - start_time, 1)) + " seconds")
    print("PNG SRCs: " + str(len(png_dict)))
    print("XML matches: " + str(xml_matches))
    print("Vhannibal matches: " + str(vhannibal_matches))
    print("Unknown: " + str(unknown_count))

    if png_dict:
        total_matches = xml_matches + vhannibal_matches
        coverage = (total_matches / len(png_dict)) * 100
        print("Coverage: " + str(round(coverage, 1)) + "%")

    print("Missing picons: " + str(len(missing_picons)))

    print("\nFiles created:")
    print("  1. src_mapping.txt")
    print("  2. missing_picons.txt")
    print("  3. summary.txt")

    if missing_picons:
        print("\nNEXT: Create " +
              str(len(missing_picons)) +
              " missing PNG files")


if __name__ == "__main__":
    generate_complete_mapping()
