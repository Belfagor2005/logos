# -*- coding: utf-8 -*-
# generate_src_mapping.py

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

        # Keep only lines ending with .png and containing E2LIST
        png_paths = []
        for line in lines:
            if line.strip().endswith('.png') and 'E2LIST' in line:
                png_paths.append(line.strip())

        print("Found %d PNG paths in logos.txt" % len(png_paths))
        return png_paths

    except Exception as e:
        print("Error reading logos.txt: %s" % e)
        return []


def extract_src_and_satellite_from_path(path):
    """Extract SRC and satellite position from PNG path"""
    parts = path.split('/')

    # Extract satellite position from directory structure
    satellite = ""
    for part in parts:
        if re.search(r'\d+\.\d+[EW]', part):
            satellite = part
            break

    # Extract SRC from filename
    filename = parts[-1]
    src = filename[:-4] if filename.endswith('.png') else filename

    return src, satellite


def parse_xml_for_channels():
    """Parse rytec.channels.xml and organize channel data"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print("XML size: %d bytes" % len(content))

        # Pattern: <!-- sat --><channel id="ID">SRC</channel><!-- name -->
        pattern = (
            r'<!--\s*([^>]+?)\s*-->\s*'
            r'<channel id="([^"]+)">([^<]+)</channel>\s*'
            r'(?:<!--\s*([^>]+?)\s*-->)?'
        )

        matches = re.findall(pattern, content)
        print("Found %d channel entries in XML" % len(matches))

        src_to_info = {}
        channel_id_to_srcs = defaultdict(list)
        channel_id_to_names = defaultdict(set)

        for before_comment, channel_id, service_ref, after_comment in matches:
            satellite = ""
            sat_match = re.search(r'(\d+(?:\.\d+)?[EW])', before_comment)
            if sat_match:
                satellite = sat_match.group(1)

            channel_name = after_comment.strip() if after_comment else channel_id

            service_ref = service_ref.strip().rstrip(':')
            src_png = service_ref.replace(':', '_')

            if src_png not in src_to_info:
                src_to_info[src_png] = {
                    'name': channel_name,
                    'satellites': set(),
                    'channel_id': channel_id
                }

            if satellite:
                src_to_info[src_png]['satellites'].add(satellite)

            channel_id_to_srcs[channel_id].append(src_png)
            channel_id_to_names[channel_id].add(channel_name)

        print("Parsed %d unique SRCs from XML" % len(src_to_info))
        print("Found %d unique channel IDs" % len(channel_id_to_srcs))

        # Normalize channel names per channel_id
        for channel_id, names in channel_id_to_names.items():
            if len(names) > 1:
                main_name = max(names, key=len)
                for src_png in channel_id_to_srcs[channel_id]:
                    if src_png in src_to_info:
                        src_to_info[src_png]['name'] = main_name

        return src_to_info, channel_id_to_srcs

    except Exception as e:
        print("Error parsing XML: %s" % e)
        return {}, {}


def create_snp_code(channel_name):
    """Generate a 4-letter SNP code from channel name"""
    if not channel_name or channel_name.lower() in ('unknown', 'no_epg'):
        return "UNKN"

    clean = re.sub(
        r'\b(?:HD|FHD|UHD|4K|SD|HEVC|TV|CHANNEL|LIVE)\b',
        '',
        channel_name,
        flags=re.IGNORECASE
    )

    letters = re.findall(r'[a-zA-Z]', clean)
    clean = ''.join(letters)

    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')

    return "CHNL"


def find_similar_channels_in_xml(src_png, src_to_info):
    """Find similar SRCs in XML based on structural similarity"""
    suggestions = []
    src_parts = src_png.split('_')

    if len(src_parts) < 7:
        return suggestions

    for xml_src, xml_info in src_to_info.items():
        xml_parts = xml_src.split('_')
        if len(xml_parts) < 7:
            continue

        similarity = 0

        if src_parts[5] == xml_parts[5]:
            similarity += 3
        if src_parts[4] == xml_parts[4]:
            similarity += 2
        if src_parts[3] == xml_parts[3]:
            similarity += 1
        if src_parts[2] == xml_parts[2]:
            similarity += 1

        if similarity >= 2:
            suggestions.append({
                'src': xml_src,
                'name': xml_info['name'],
                'similarity': similarity,
                'satellites': xml_info['satellites']
            })

    return sorted(suggestions, key=lambda x: x['similarity'], reverse=True)[:5]


def generate_final_mapping():
    print("=" * 80)
    print("GENERATING SRC MAPPING")
    print("=" * 80)

    start_time = time.time()

    print("Reading PNG paths...")
    png_paths = get_png_paths()
    if not png_paths:
        print("No PNG paths found")
        return

    print("Parsing XML...")
    src_to_info, _ = parse_xml_for_channels()

    png_srcs = defaultdict(set)
    png_file_to_satellites = defaultdict(set)

    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src and satellite:
            png_srcs[src].add(satellite)
            png_file_to_satellites[path.split('/')[-1]].add(satellite)

    print("Unique SRCs found in PNGs: %d" % len(png_srcs))

    mapping_lines = []
    exact_matches = 0
    similarity_matches = 0
    unknown_count = 0

    for src_png in sorted(png_srcs):
        satellites = set(png_srcs[src_png])
        snp = "UNKN"

        if src_png in src_to_info:
            info = src_to_info[src_png]
            snp = create_snp_code(info['name'])
            satellites.update(info['satellites'])
            exact_matches += 1
            mapping_lines.append(
                "%s - %s - %s" % (src_png, snp, "|".join(sorted(satellites)))
            )
        else:
            similar = find_similar_channels_in_xml(src_png, src_to_info)
            if similar and similar[0]['similarity'] >= 3:
                best = similar[0]
                snp = create_snp_code(best['name'])
                satellites.update(best['satellites'])
                similarity_matches += 1
                mapping_lines.append(
                    "%s - %s - %s # SIMILAR"
                    % (src_png, snp, "|".join(sorted(satellites)))
                )
            else:
                unknown_count += 1
                mapping_lines.append(
                    "%s - UNKN - %s" % (src_png, "|".join(sorted(satellites)))
                )

    with open("src_mapping.txt", "w", encoding="utf-8") as f:
        f.write("# SRC - SNP - satellite positions\n")
        f.write("# Total entries: %d\n" % len(mapping_lines))
        f.write("# Exact matches: %d\n" % exact_matches)
        f.write("# Similar matches: %d\n" % similarity_matches)
        f.write("# Unknown: %d\n\n" % unknown_count)
        for line in mapping_lines:
            f.write(line + "\n")

    print("Completed in %.1f seconds" % (time.time() - start_time))
    print("Exact matches:", exact_matches)
    print("Similarity matches:", similarity_matches)
    print("Unknown:", unknown_count)
    print("File created: src_mapping.txt")


if __name__ == "__main__":
    generate_final_mapping()
