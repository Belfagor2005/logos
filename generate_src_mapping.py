# -*- coding: utf-8 -*-
# generate_src_mapping.py
import requests
import re
from collections import defaultdict


def get_png_files():
    """Get all PNG files from SRF folder"""
    print("Getting PNG files from GitHub...")

    all_files = []
    page = 1

    while True:
        url = f"https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF?page={page}"

        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SRC-Mapping-Generator'
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                print(f"API returned status {response.status_code}")
                break

            data = response.json()

            if not data:
                break

            for item in data:
                if isinstance(item, dict):
                    filename = item.get('name', '')
                    if filename.endswith('.png'):
                        all_files.append(filename)

            # Se abbiamo meno di 1000 item, siamo all'ultima pagina
            if len(data) < 1000:
                break

            page += 1
            if page % 10 == 0:
                print(
                    f"  Fetched page {page}, total files so far: {
                        len(all_files)}")

        except Exception as e:
            print(f"Error on page {page}: {e}")
            break

    print(f"Found {len(all_files)} PNG files")
    return all_files


def parse_xml():
    """Parse XML and create dictionary of SRC -> (channel_name, [satellites])"""
    print("Parsing XML file...")

    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=30)
        xml_data = response.text

        # Dizionario per accumulare satelliti per ogni SRC
        # SRC -> {'name': channel_name, 'satellites': set()}
        xml_mappings = defaultdict(lambda: {'name': '', 'satellites': set()})
        current_satellite = ""
        line_count = 0

        lines = xml_data.split('\n')

        for line in lines:
            line_count += 1
            line = line.strip()

            # Get satellite position from comment (come prima)
            if line.startswith(
                    '<!--') and '-->' in line and '<channel' not in line:
                sat_match = re.search(r'<!--\s*([0-9.]+[EW])\s*-->', line)
                if sat_match:
                    current_satellite = sat_match.group(1)

            # Get channel entry
            elif '<channel id="' in line and '>' in line:
                # Extract channel ID (name)
                id_match = re.search(r'<channel id="([^"]+)"', line)
                if id_match:
                    channel_id = id_match.group(1)

                    # Extract SRC code
                    src_match = re.search(r'>([0-9:ABCDEF_]+:)<', line)
                    if src_match:
                        src_code_full = src_match.group(1)

                        # Convert to PNG format
                        src_for_png = src_code_full.rstrip(
                            ':').replace(':', '_')

                        # Get channel name from comment
                        name_match = re.search(r'<!--\s*(.+?)\s*-->', line)
                        channel_name = name_match.group(
                            1) if name_match else channel_id

                        # Aggiorna il dizionario
                        xml_mappings[src_for_png]['name'] = channel_name
                        if current_satellite:  # Aggiungi satellite solo se esiste
                            xml_mappings[src_for_png]['satellites'].add(
                                current_satellite)

        # Converti set in stringa ordinata
        for src in xml_mappings:
            if xml_mappings[src]['satellites']:
                # Ordina i satelliti e uniscili con |
                sorted_sats = sorted(xml_mappings[src]['satellites'])
                xml_mappings[src]['satellites_str'] = '|'.join(sorted_sats)
            else:
                xml_mappings[src]['satellites_str'] = 'Satellite Unknown'

        print(f"Parsed {len(xml_mappings)} unique SRC entries from XML")
        print(f"Total lines processed: {line_count}")

        return dict(xml_mappings)

    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}


def generate_mapping():
    print("Starting SRC mapping generation...")
    print("=" * 60)

    # 1. Get PNG files
    png_files = get_png_files()

    if not png_files:
        print("ERROR: No PNG files found!")
        return

    # 2. Parse XML
    xml_data = parse_xml()

    if not xml_data:
        print("ERROR: No XML data parsed!")
        return

    print("\n" + "=" * 60)
    print("Generating mapping...")

    # 3. Converti lista PNG in set per evitare duplicati locali
    # (anche se i duplicati potrebbero avere significato, li teniamo)
    png_srcs = {}
    for png_file in png_files:
        src_from_png = png_file.replace('.png', '')
        png_srcs[src_from_png] = png_srcs.get(src_from_png, 0) + 1

    print(f"Unique PNG SRC codes: {len(png_srcs)}")
    print(f"Total PNG files (with duplicates): {len(png_files)}")

    # 4. Genera output
    results = []
    not_found_list = []
    found_count = 0

    for src_from_png in sorted(png_srcs.keys()):
        if src_from_png in xml_data:
            info = xml_data[src_from_png]
            # Aggiungi anche il conteggio dei duplicati
            dup_count = png_srcs[src_from_png]
            if dup_count > 1:
                results.append(
                    f"{src_from_png} - {info['name']} - {info['satellites_str']} (appears {dup_count} times)")
            else:
                results.append(
                    f"{src_from_png} - {info['name']} - {info['satellites_str']}")
            found_count += 1
        else:
            not_found_list.append(src_from_png)
            dup_count = png_srcs[src_from_png]
            if dup_count > 1:
                results.append(
                    f"{src_from_png} - CHANNEL NOT FOUND IN XML - SATELLITE UNKNOWN (appears {dup_count} times)")
            else:
                results.append(
                    f"{src_from_png} - CHANNEL NOT FOUND IN XML - SATELLITE UNKNOWN")

    # 5. Scrivi file principale
    print("\nWriting files...")
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - Channel Name - Satellite Positions\n")
        f.write("# Generated automatically\n")
        f.write(
            f"# Unique PNG SRCs: {
                len(png_srcs)}, Found in XML: {found_count}, Not found: {
                len(not_found_list)}\n")
        f.write(
            f"# Note: Same SRC may appear multiple times with different satellite positions\n\n")

        for line in results:
            f.write(line + "\n")

    # 6. Scrivi file not found
    with open('not_found_src.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC codes not found in XML\n")
        f.write(f"# Total unique SRCs not found: {len(not_found_list)}\n")
        f.write(
            f"# Total PNG files not found (with duplicates): {
                sum(
                    png_srcs[src] for src in not_found_list)}\n")
        f.write(
            f"# Date: {
                __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for src in sorted(not_found_list):
            dup_count = png_srcs[src]
            if dup_count > 1:
                f.write(f"{src} (appears {dup_count} times)\n")
            else:
                f.write(f"{src}\n")

    # 7. Statistiche
    print("\n" + "=" * 60)
    print("FINAL STATISTICS:")
    print(f"Unique PNG SRC codes: {len(png_srcs)}")
    print(f"Total PNG files (with duplicates): {len(png_files)}")
    print(f"XML entries: {len(xml_data)}")
    print(
        f"Found in XML: {found_count} ({
            found_count /
            len(png_srcs) *
            100:.1f}% of unique SRCs)")
    print(
        f"Not found in XML: {
            len(not_found_list)} ({
            len(not_found_list) /
            len(png_srcs) *
            100:.1f}% of unique SRCs)")

    # Analizza i duplicati
    duplicate_counts = defaultdict(int)
    for count in png_srcs.values():
        duplicate_counts[count] += 1

    print(f"\nDuplicate analysis:")
    for count in sorted(duplicate_counts.keys(), reverse=True):
        if count > 1:
            print(f"  SRCs appearing {count} times: {duplicate_counts[count]}")

    if not_found_list:
        print(f"\nSample of SRC codes not found in XML (first 5):")
        for src in not_found_list[:5]:
            print(f"  {src} (appears {png_srcs[src]} times)")

    print(f"\nFiles created:")
    print(f"  - src_mapping.txt ({len(results)} entries)")
    print(f"  - not_found_src.txt ({len(not_found_list)} unique SRCs)")


if __name__ == "__main__":
    generate_mapping()
