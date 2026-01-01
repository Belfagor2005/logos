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
    parts = path.split('/')

    # Estrai satellite dalla struttura di directory
    satellite = ""
    if len(parts) >= 3:
        for part in parts:
            if re.search(r'\d+\.\d+[EW]', part):
                satellite = part
                break

    # Estrai SRC dal nome del file
    filename = parts[-1]
    if filename.endswith('.png'):
        src = filename[:-4]
    else:
        src = filename

    return src, satellite


def parse_xml_for_channels():
    """Parse XML and extract channels with satellites"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print(f"XML size: {len(content)} bytes")

        # Regex migliorata per catturare tutto
        pattern = r'<!--\s*([^>]+?)\s*-->\s*<channel id="([^"]+)">([^<]+)</channel>\s*(?:<!--\s*([^>]+)\s*-->)?'
        matches = re.findall(pattern, content)

        print(f"Found {len(matches)} channel entries in XML")

        xml_dict = {}

        for match in matches:
            source_info, channel_id, service_ref, channel_comment = match

            # Estrai satellite da source_info (es: "16.0E" o "16.0E -->")
            satellite = ""
            if source_info:
                sat_match = re.search(r'(\d+(?:\.\d+)?[EW])', source_info)
                if sat_match:
                    satellite = sat_match.group(1)

            # Estrai nome canale
            channel_name = channel_id  # Default

            if channel_comment:
                channel_name = channel_comment.strip()
            elif '-->' in source_info:
                # Se source_info contiene -->channel, potrebbe avere il nome
                parts = source_info.split('-->')
                if len(parts) > 1:
                    channel_name = parts[-1].strip()

            # Converti SRC
            service_ref = service_ref.strip().rstrip(':')
            src_png = service_ref.replace(':', '_')

            # Salva nel dizionario
            xml_dict[src_png] = {
                'name': channel_name,
                'satellites': {satellite} if satellite else set(),
                'channel_id': channel_id
            }

        print(f"Parsed {len(xml_dict)} unique SRC entries from XML")

        return xml_dict

    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}


def create_snp_code(channel_name):
    """Create SNP code from channel name"""
    if not channel_name or channel_name.lower() in ['unknown', '']:
        return "UNKN"

    # Rimuovi estensioni comuni e pulisci
    clean = re.sub(
        r'\s*(?:HD|FHD|UHD|4K|SD|\.\w{2,4})$',
        '',
        channel_name,
        flags=re.IGNORECASE)
    clean = re.sub(r'[^a-zA-Z0-9]', '', clean)

    if not clean:
        return "CHNL"

    return clean[:4].upper()


def analyze_src_pattern(src):
    """Analyze SRC pattern to understand what it represents"""
    parts = src.split('_')
    if len(parts) >= 10:
        # Formato: 1_0_1_9_1_1_A00000_0_0_0
        # Interpretazione:
        # 1 = Service Type (1 = TV, 2 = Radio, etc.)
        # 0 = ???
        # 1 = Service ID
        # 9 = Transport Stream ID
        # 1 = Original Network ID
        # 1 = Namespace
        # A00000 = Service Reference
        # 0_0_0 = ???

        try:
            service_type = parts[0]
            service_id = parts[2]
            ts_id = parts[3]
            onid = parts[4]
            namespace = parts[5]

            return {
                'service_type': 'TV' if service_type == '1' else 'Radio' if service_type == '2' else f'Type{service_type}',
                'service_id': service_id,
                'ts_id': ts_id,
                'onid': onid,
                'namespace': namespace}
        except BaseException:
            return {}

    return {}


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
    print("\nParsing XML from rytec.channels.xml...")
    xml_dict = parse_xml_for_channels()

    # 3. Process PNG paths
    print("\nProcessing PNG paths...")
    png_srcs = {}

    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src:
            if src not in png_srcs:
                png_srcs[src] = set()
            if satellite:
                png_srcs[src].add(satellite)

    print(f"Found {len(png_srcs)} unique SRCs in PNG directories")

    # 4. Calcola statistiche corrette
    all_srcs = set(list(xml_dict.keys()) + list(png_srcs.keys()))
    srcs_in_both = set(xml_dict.keys()) & set(png_srcs.keys())
    srcs_only_in_xml = set(xml_dict.keys()) - set(png_srcs.keys())
    srcs_only_in_png = set(png_srcs.keys()) - set(xml_dict.keys())

    print(f"\nStatistics:")
    print(f"  Total unique SRCs: {len(all_srcs)}")
    print(f"  SRCs in both XML and PNG: {len(srcs_in_both)}")
    print(f"  SRCs only in XML (need PNGs): {len(srcs_only_in_xml)}")
    print(f"  SRCs only in PNG (need XML entries): {len(srcs_only_in_png)}")

    # 5. Genera i file
    print("\nGenerating output files...")

    # File 1: src_mapping.txt (solo SRC presenti in PNG)
    mapping_lines = []

    for src in sorted(png_srcs.keys()):
        satellites = png_srcs[src]

        # Ordina satelliti
        def sat_sort_key(s):
            if not s:
                return (1, 9999)
            match = re.match(r'(\d+\.?\d*)([EW])', s)
            if match:
                num = float(match.group(1))
                direction = match.group(2)
                # W negativi, E positivi
                return (0, -num if direction == 'W' else num)
            return (1, 9999)

        sorted_sats = sorted(satellites, key=sat_sort_key)
        satellites_str = '|'.join(sorted_sats) if sorted_sats else 'Unknown'

        # Se è nell'XML, usa info XML
        if src in xml_dict:
            xml_data = xml_dict[src]
            channel_name = xml_data['name']
            snp_code = create_snp_code(channel_name)

            # Combina satelliti
            xml_sats = xml_data['satellites']
            if xml_sats:
                all_sats = set(sorted_sats) | xml_sats
                sorted_all_sats = sorted(all_sats, key=sat_sort_key)
                satellites_str = '|'.join(sorted_all_sats)
        else:
            snp_code = "UNKN"

        mapping_lines.append(f"{src} - {snp_code} - {satellites_str}")

    # File 2: missing_pngs.txt (dettagliato)
    missing_lines = []

    for src in sorted(srcs_only_in_png):
        satellites = png_srcs[src]

        # Analizza pattern SRC
        src_analysis = analyze_src_pattern(src)

        # Crea linea dettagliata
        line = "=" * 60 + "\n"
        line += f"SRC: {src}\n"

        if src_analysis:
            line += f"Analysis: {
                src_analysis['service_type']}, Service ID: {
                src_analysis['service_id']}, "
            line += f"TS ID: {
                src_analysis['ts_id']}, ONID: {
                src_analysis['onid']}\n"

        if satellites:
            sorted_sats = sorted(satellites)
            line += f"Satellites: {' | '.join(sorted_sats)}\n"

            # Aggiungi info satellite
            sat_info = []
            for sat in sorted_sats:
                if sat == '13.0E':
                    sat_info.append(f"{sat} (Hotbird)")
                elif sat == '19.2E':
                    sat_info.append(f"{sat} (Astra 1)")
                elif sat == '23.5E':
                    sat_info.append(f"{sat} (Astra 3)")
                elif sat == '28.2E':
                    sat_info.append(f"{sat} (Astra 2)")
                elif sat == '0.8W':
                    sat_info.append(f"{sat} (Thor/Intelsat)")
                elif sat == '5.0W':
                    sat_info.append(f"{sat} (Sirius)")
                elif sat == '16.0E':
                    sat_info.append(f"{sat} (Eutelsat 16A)")
                elif sat == '9.0E':
                    sat_info.append(f"{sat} (Eutelsat 9A)")
                elif sat == '7.0E':
                    sat_info.append(f"{sat} (Eutelsat 7A)")
                elif sat == '4.8E':
                    sat_info.append(f"{sat} (Astra 4A)")
                else:
                    sat_info.append(sat)

            line += f"Satellite Info: {', '.join(sat_info)}\n"
        else:
            line += "Satellites: Unknown (check directory structure)\n"

        line += f"Status: PNG exists but missing in rytec.channels.xml\n"
        line += "Action: Need to add <channel> entry to XML\n"

        missing_lines.append(line)

    # 6. Scrivi i file
    print("\nWriting files...")

    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
        f.write(f"# Total entries: {len(mapping_lines)}\n")
        f.write(f"# SRCs with XML match: {len(srcs_in_both)}\n")
        f.write(f"# SRCs missing in XML: {len(srcs_only_in_png)}\n")
        f.write("# Generated from logos.txt and rytec.channels.xml\n")
        f.write("# Format example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")

        for line in sorted(mapping_lines):
            f.write(line + "\n")

    # File 2: missing_pngs_detailed.txt
    with open('missing_pngs_detailed.txt', 'w', encoding='utf-8') as f:
        f.write("# DETAILED REPORT: PNG FILES MISSING IN XML\n")
        f.write("# ==========================================\n")
        f.write(f"# Total missing PNGs: {len(srcs_only_in_png)}\n")
        f.write(
            "# These Service References have PNG files but NO entry in rytec.channels.xml\n")
        f.write("#\n")
        f.write("# HOW TO FIX:\n")
        f.write("# 1. For each SRC below, identify the channel name\n")
        f.write("# 2. Check satellite websites using the satellite info provided\n")
        f.write("# 3. Add the channel to rytec.channels.xml in format:\n")
        f.write("#    <!-- 13.0E --><channel id=\"ChannelName\">1:0:1:XXX:XXX:XXX:XXXXXX:0:0:0:</channel><!-- Channel Name -->\n")
        f.write("#\n")
        f.write("# USEFUL WEBSITES:\n")
        f.write("# - KingOfSat: https://en.kingofsat.net/\n")
        f.write("# - LyngSat: https://www.lyngsat.com/\n")
        f.write("# - SatelliTV: https://www.satellitetv.net/\n")
        f.write("# - SatSearch: https://satsearch.co/\n")
        f.write("# ==========================================\n\n")

        if missing_lines:
            for line in missing_lines:
                f.write(line + "\n")
        else:
            f.write("EXCELLENT! No missing PNGs found.\n")

    # File 3: missing_pngs_simple.txt
    with open('missing_pngs_simple.txt', 'w', encoding='utf-8') as f:
        f.write("# Simple list of SRCs missing in XML (for batch processing)\n")
        f.write(f"# Total: {len(srcs_only_in_png)}\n\n")

        for src in sorted(srcs_only_in_png):
            f.write(f"{src}\n")

    # File 4: xml_without_pngs.txt (SRC nell'XML ma senza PNG)
    with open('xml_without_pngs.txt', 'w', encoding='utf-8') as f:
        f.write("# SRCs in XML but missing PNG files\n")
        f.write(f"# Total: {len(srcs_only_in_xml)}\n\n")

        for src in sorted(srcs_only_in_xml):
            if src in xml_dict:
                channel_name = xml_dict[src]['name']
                f.write(f"{src} - {channel_name}\n")
            else:
                f.write(f"{src}\n")

    # 7. Statistiche finali
    print("\n" + "=" * 80)
    print("FINAL RESULTS:")
    print(f"Total unique SRCs processed: {len(all_srcs)}")
    print(f"SRCs in both XML and PNG: {len(srcs_in_both)}")
    print(f"SRCs only in XML (need PNG files): {len(srcs_only_in_xml)}")
    print(f"SRCs only in PNG (need XML entries): {len(srcs_only_in_png)}")

    print(
        f"\nCoverage: {
            len(srcs_in_both) /
            len(all_srcs) *
            100:.1f}% complete")

    # Esempi
    if mapping_lines:
        print(f"\nSample from src_mapping.txt (first 3 with channel names):")
        named_samples = [
            line for line in mapping_lines if ' - UNKN - ' not in line]
        for line in named_samples[:3]:
            print(f"  {line}")

        print(f"\nSample from src_mapping.txt (first 3 UNKN):")
        unkn_samples = [line for line in mapping_lines if ' - UNKN - ' in line]
        for line in unkn_samples[:3]:
            print(f"  {line}")

    if srcs_only_in_png:
        sample_missing = sorted(srcs_only_in_png)[0]
        print(f"\nSample missing PNG (first):")
        print(f"  SRC: {sample_missing}")
        if sample_missing in png_srcs:
            print(
                f"  Satellites: {
                    ', '.join(
                        sorted(
                            png_srcs[sample_missing]))}")

    print(f"\nFiles created:")
    print(
        f"  1. src_mapping.txt - Main mapping ({(len(mapping_lines) / 1024):.1f}KB)")
    print(f"  2. missing_pngs_detailed.txt - Detailed report of missing PNGs")
    print(f"  3. missing_pngs_simple.txt - Simple list for copy-paste")
    print(f"  4. xml_without_pngs.txt - SRCs in XML without PNG files")

    print(f"\nNext steps:")
    print(f"  1. Review missing_pngs_detailed.txt")
    print(f"  2. Identify channels using satellite websites")
    print(f"  3. Add missing channels to rytec.channels.xml")
    print(f"  4. Check xml_without_pngs.txt for channels needing logos")


if __name__ == "__main__":
    generate_final_mapping()
