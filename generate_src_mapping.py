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

        png_paths = []
        for line in lines:
            if line.strip().endswith('.png') and 'E2LIST' in line:
                png_paths.append(line.strip())

        print("Found {} PNG paths in logos.txt".format(len(png_paths)))
        return png_paths

    except Exception as e:
        print("Error getting logos.txt: {}".format(e))
        return []


def extract_src_and_satellite_from_path(path):
    parts = path.split('/')

    satellite = ""
    for part in parts:
        if re.search(r'\d+\.\d+[EW]', part):
            satellite = part
            break

    filename = parts[-1]
    src = filename[:-4] if filename.endswith('.png') else filename
    return src, satellite


def parse_xml_for_channels():
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print("XML size: {:,} bytes".format(len(content)))

        pattern = r'<!--\s*([^>]+?)\s*-->\s*<channel id="([^"]+)">([^<]+)</channel>\s*(?:<!--\s*([^>]+?)\s*-->)?'
        matches = re.findall(pattern, content)

        print("Found {} channel entries in XML".format(len(matches)))

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

        print("Parsed {} unique SRCs from XML".format(len(src_to_info)))
        print("Found {} unique channel IDs".format(len(channel_id_to_srcs)))

        for channel_id, names in channel_id_to_names.items():
            if len(names) > 1:
                main_name = max(names, key=len)
                for src_png in channel_id_to_srcs[channel_id]:
                    src_to_info[src_png]['name'] = main_name

        return src_to_info, channel_id_to_srcs

    except Exception as e:
        print("Error parsing XML: {}".format(e))
        return {}, {}


def create_snp_code(channel_name):
    if not channel_name or channel_name.lower() in ['unknown', 'no_epg', '']:
        return "UNKN"

    clean = re.sub(r'\b(?:HD|FHD|UHD|4K|SD|HEVC|TV|CHANNEL|LIVE)\b', '', channel_name, flags=re.IGNORECASE)
    letters = re.findall(r'[a-zA-Z]', clean)
    clean = ''.join(letters)

    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')
    return "CHNL"


def generate_final_mapping():
    print("=" * 80)
    print("GENERATING SRC MAPPING - FINAL WORKING VERSION")
    print("=" * 80)

    start_time = time.time()

    png_paths = get_png_paths()
    if not png_paths:
        return

    src_to_info, channel_id_to_srcs = parse_xml_for_channels()

    png_srcs = defaultdict(set)
    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src and satellite:
            png_srcs[src].add(satellite)

    mapping_lines = []

    for src_png in sorted(png_srcs.keys()):
        satellites = sorted(png_srcs[src_png])
        satellites_str = "|".join(satellites)

        if src_png in src_to_info:
            name = src_to_info[src_png]['name']
            snp = create_snp_code(name)
        else:
            snp = "UNKN"

        mapping_lines.append("{} - {} - {}".format(src_png, snp, satellites_str))

    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - SNP - SATELLITES\n")
        f.write("# Total entries: {}\n\n".format(len(mapping_lines)))
        for line in mapping_lines:
            f.write(line + "\n")

    print("Completed in {:.1f} seconds".format(time.time() - start_time))
    print("Generated src_mapping.txt successfully")


if __name__ == "__main__":
    generate_final_mapping()


if __name__ == "__main__":
    generate_final_mapping()
