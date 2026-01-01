# -*- coding: utf-8 -*-
# generate_src_mapping.py
import requests
import re
from collections import defaultdict


def get_png_paths():
    """Get all PNG paths from txt/logos.txt"""
    txt_url = "https://raw.githubusercontent.com/Belfagor2005/logos/refs/heads/main/txt/logos.txt"

    try:
        response = requests.get(txt_url, timeout=30)
        lines = response.text.strip().split('\n')

        # Filtra solo le linee che finiscono con .png e contengono E2LIST
        png_paths = []
        for line in lines:
            if line.strip().endswith('.png') and 'E2LIST' in line:
                png_paths.append(line.strip())

        print(f"Found {len(png_paths)} PNG paths in logos.txt")
        return png_paths

    except Exception as e:
        print(f"Error getting logos.txt: {e}")
        return []


def extract_src_and_satellite_from_path(path):
    """Extract SRC and satellite position from PNG path"""
    # Esempio: logos/E2LIST/39.0E/1_0_1_67_E_3_130000_0_0_0.png
    # Estrae: (1_0_1_67_E_3_130000_0_0_0, "39.0E")

    parts = path.split('/')

    # Estrai satellite dalla struttura di directory
    satellite = ""
    if len(parts) >= 3:
        # Cerca la parte che contiene la posizione satellitare (es: "39.0E",
        # "5.0W")
        for part in parts:
            if re.search(r'\d+\.\d+[EW]', part):
                satellite = part
                break

    # Estrai SRC dal nome del file
    filename = parts[-1]
    if filename.endswith('.png'):
        src = filename[:-4]  # Rimuove ".png"
    else:
        src = filename

    return src, satellite


def parse_xml_for_channels():
    """Parse XML and create dictionary of SRC -> (channel_name, satellites_list)"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        xml_data = response.text

        # Dizionario: SRC_PNG -> {'name': channel_name, 'satellites': set()}
        xml_dict = defaultdict(lambda: {'name': '', 'satellites': set()})
        current_satellite = ""

        lines = xml_data.split('\n')

        for line in lines:
            line = line.strip()

            # Cerca satellite nei commenti
            if line.startswith('<!--') and '-->' in line:
                sat_match = re.search(r'<!--\s*([^>]+)\s*-->', line)
                if sat_match:
                    sat_text = sat_match.group(1).strip()
                    # Estrai solo la posizione satellitare (es: "16.0E")
                    sat_pos_match = re.search(r'(\d+\.\d+[EW])', sat_text)
                    if sat_pos_match:
                        current_satellite = sat_pos_match.group(1)
                    else:
                        current_satellite = ""

            # Cerca channel
            elif '<channel id="' in line and '>' in line:
                # Estrai ID canale
                id_match = re.search(r'id="([^"]+)"', line)
                if id_match:
                    channel_id = id_match.group(1)

                    # Estrai SRC
                    src_match = re.search(
                        r'>([0-9A-Fa-f:]+:[0-9A-Fa-f:]+:[0-9A-Fa-f:]+:[0-9A-Fa-f:]+:[0-9A-Fa-f:]+:[0-9A-Fa-f:]+:[0-9A-Fa-f:]+:[0-9]+:[0-9]+:[0-9]+:)<',
                        line,
                        re.IGNORECASE)

                    if src_match:
                        src_xml = src_match.group(1)
                        # Converti a PNG format
                        src_png = src_xml.rstrip(':').replace(':', '_')

                        # Estrai nome canale
                        name_match = re.search(r'<!--\s*([^<]+)\s*-->$', line)
                        channel_name = name_match.group(
                            1).strip() if name_match else channel_id

                        # Aggiorna il dizionario
                        if not xml_dict[src_png]['name']:
                            xml_dict[src_png]['name'] = channel_name

                        if current_satellite:
                            xml_dict[src_png]['satellites'].add(
                                current_satellite)

        print(f"Parsed {len(xml_dict)} unique SRC entries from XML")
        return dict(xml_dict)

    except Exception as e:
        print(f"Error parsing XML: {e}")
        return {}


def create_snp_code(channel_name):
    """Create SNP code from channel name (prime 4 lettere del nome pulito)"""
    if not channel_name:
        return "UNKN"

    # Rimuovi spazi e caratteri speciali
    clean_name = re.sub(r'\s+', '', channel_name)  # Rimuovi spazi
    # Rimuovi caratteri speciali
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', clean_name)

    if not clean_name:
        return "CHNL"

    # Prendi prime 4 lettere e converti in maiuscolo
    return clean_name[:4].upper()


def generate_final_mapping():
    print("=" * 80)
    print("GENERATING SRC MAPPING")
    print("=" * 80)

    # 1. Get PNG paths
    print("Getting PNG paths from logos.txt...")
    png_paths = get_png_paths()

    if not png_paths:
        print("No PNG paths found!")
        return

    # 2. Parse XML
    print("Parsing XML...")
    xml_dict = parse_xml_for_channels()

    if not xml_dict:
        print("No XML data!")
        return

    # 3. Process PNG paths
    print("Processing PNG paths...")

    # Dizionario per tenere traccia di tutti i satelliti trovati nei PNG
    png_srcs = defaultdict(set)  # src -> set di satelliti

    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src and satellite:
            png_srcs[src].add(satellite)

    print(f"Found {len(png_srcs)} unique SRCs in PNG directories")

    # 4. Genera i due file
    print("\nGenerating output files...")

    # File 1: mapping completo (SRC - SNP - satelliti)
    mapping_lines = []

    # File 2: PNG mancanti nell'XML
    missing_png_lines = []

    # Prima: processa gli SRC che sono nell'XML
    for src in sorted(xml_dict.keys()):
        xml_data = xml_dict[src]
        channel_name = xml_data['name']

        # Crea SNP code
        snp_code = create_snp_code(channel_name)

        # Prendi satelliti dall'XML
        xml_satellites = xml_data['satellites']

        # Aggiungi satelliti dai PNG se esistono
        all_satellites = set(xml_satellites)
        if src in png_srcs:
            all_satellites.update(png_srcs[src])

        # Ordina satelliti (prima Est, poi Ovest)
        def sat_sort_key(s):
            if not s:
                return 9999
            # Estrai numero e direzione
            match = re.match(r'(\d+\.?\d*)([EW])', s)
            if match:
                num = float(match.group(1))
                direction = match.group(2)
                # Per ordinare da ovest a est: W negativo, E positivo
                if direction == 'W':
                    return -num
                else:
                    return num + 1000  # Metti tutti gli E dopo i W
            return 9999

        sorted_satellites = sorted(all_satellites, key=sat_sort_key)

        # Formatta la stringa satelliti
        if sorted_satellites:
            satellites_str = '|'.join(sorted_satellites)
        else:
            satellites_str = 'Unknown'

        # Aggiungi alla lista mapping
        mapping_lines.append(f"{src} - {snp_code} - {satellites_str}")

        # Rimuovi dagli SRC PNG processati
        if src in png_srcs:
            del png_srcs[src]

    # Secondo: processa gli SRC rimanenti (solo nei PNG, non nell'XML)
    for src in sorted(png_srcs.keys()):
        satellites = png_srcs[src]

        # Per il file mapping: usa UNKN come SNP
        if satellites:
            satellites_str = '|'.join(sorted(satellites))
        else:
            satellites_str = 'Unknown'

        mapping_lines.append(f"{src} - UNKN - {satellites_str}")

        # Per il file PNG mancanti: aggiungi tutti i dettagli
        for satellite in sorted(satellites):
            missing_png_lines.append(
                f"{src} - Found in PNG at {satellite} but not in XML")

    # 5. Scrivi i file
    print("\nWriting files...")

    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
        f.write(f"# Total entries: {len(mapping_lines)}\n")
        f.write("# Generated from logos.txt and rytec.channels.xml\n")
        f.write("# Format example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")

        for line in sorted(mapping_lines):
            f.write(line + "\n")

    # File 2: missing_pngs.txt
    with open('missing_pngs.txt', 'w', encoding='utf-8') as f:
        f.write("# PNG files that need to be added to XML\n")
        f.write(f"# Total missing: {len(missing_png_lines)}\n")
        f.write("# These SRC codes exist in PNG files but not in rytec.channels.xml\n")
        f.write("# Need to add corresponding <channel> entries to the XML\n\n")

        if missing_png_lines:
            for line in sorted(missing_png_lines):
                f.write(line + "\n")
        else:
            f.write(
                "# No missing PNGs found - all PNGs have corresponding XML entries!\n")

    # 6. Statistiche
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY:")
    print(
        f"Total PNG SRCs found: {
            len(png_srcs) +
            len(xml_dict) -
            len(png_srcs)}")
    print(f"SRCs found in XML: {len(xml_dict)}")
    print(f"SRCs only in PNG (not in XML): {len(png_srcs)}")
    print(f"Total lines in mapping file: {len(mapping_lines)}")
    print(f"Missing PNGs to add to XML: {len(missing_png_lines)}")

    if mapping_lines:
        print(f"\nSample from src_mapping.txt (first 5 lines):")
        for line in sorted(mapping_lines)[:5]:
            print(f"  {line}")

    if missing_png_lines:
        print(f"\nSample from missing_pngs.txt (first 5 lines):")
        for line in sorted(missing_png_lines)[:5]:
            print(f"  {line}")
    else:
        print(f"\nGreat! No missing PNGs found.")

    print(f"\nFiles created:")
    print(f"  src_mapping.txt - Main mapping file (SRC - SNP - satellites)")
    print(f"  missing_pngs.txt - PNGs that need XML entries")


if __name__ == "__main__":
    generate_final_mapping()
