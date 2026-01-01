# -*- coding: utf-8 -*-
# generate_src_mapping.py
import requests
import re
from collections import defaultdict
import json
import time


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
    """Parse XML CORRECTLY - VERSIONE DEFINITIVA"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print(f"XML size: {len(content):,} bytes")

        # PARSER MIGLIORATO: cerca pattern completo
        # Formato: <!-- 16.0E --><channel
        # id="ZicoTV.rs">1:0:1:9:1:1:A00000:0:0:0:</channel><!-- Zico TV -->
        pattern = r'<!--\s*([^>]+?)\s*-->\s*<channel id="([^"]+)">([^<]+)</channel>\s*<!--\s*([^>]+?)\s*-->'

        # Prima cerca con pattern completo
        matches_full = re.findall(pattern, content)
        print(
            f"Found {
                len(matches_full)} complete channel entries (with both comments)")

        # Poi cerca quelli senza commento finale
        pattern_no_end_comment = r'<!--\s*([^>]+?)\s*-->\s*<channel id="([^"]+)">([^<]+)</channel>'
        matches_no_end = re.findall(pattern_no_end_comment, content)
        print(f"Found {len(matches_no_end)} entries without end comment")

        # Combina match
        all_matches = []

        # Prima aggiungi quelli completi
        for match in matches_full:
            before_comment, channel_id, service_ref, after_comment = match
            all_matches.append(
                (before_comment, channel_id, service_ref, after_comment))

        # Poi quelli senza commento finale
        for match in matches_no_end:
            before_comment, channel_id, service_ref = match
            all_matches.append((before_comment, channel_id, service_ref, ""))

        print(f"Total channel entries found: {len(all_matches)}")

        xml_dict = {}

        for before_comment, channel_id, service_ref, after_comment in all_matches:
            # Estrai satellite dal commento prima
            satellite = ""
            sat_match = re.search(r'(\d+(?:\.\d+)?[EW])', before_comment)
            if sat_match:
                satellite = sat_match.group(1)

            # Determina nome canale
            channel_name = channel_id  # Default

            if after_comment:
                # Nome dal commento finale
                channel_name = after_comment.strip()
                # Pulisci: rimuovi eventuali " - " o altri separatori
                channel_name = re.sub(r'\s*[-–]\s*.*$', '', channel_name)
            elif before_comment:
                # Se non c'è commento finale, prova a estrarre dal commento prima
                # Rimuovi la parte satellitare
                clean_before = re.sub(r'\d+\.\d+[EW]\s*', '', before_comment)
                clean_before = re.sub(r'\s*[-–>]*\s*$', '', clean_before)
                if clean_before and not clean_before.startswith('<'):
                    channel_name = clean_before.strip()

            # Converti SRC
            service_ref = service_ref.strip().rstrip(':')
            src_png = service_ref.replace(':', '_')

            # Aggrega dati
            if src_png not in xml_dict:
                xml_dict[src_png] = {
                    'name': channel_name,
                    'satellites': set(),
                    'channel_id': channel_id
                }

            if satellite:
                xml_dict[src_png]['satellites'].add(satellite)

            # Se troviamo nomi migliori, aggiorna
            if after_comment and len(
                    after_comment.strip()) > len(channel_name):
                xml_dict[src_png]['name'] = after_comment.strip()

        print(f"Parsed {len(xml_dict)} unique SRC entries from XML")

        # DEBUG: mostra esempi REALI
        print("\n🔍 DEBUG - Sample parsed channels (first 10):")
        sample_count = 0
        for src, data in xml_dict.items():
            if sample_count >= 10:
                break
            if data['name'] and data['name'] != data['channel_id']:
                sats = ', '.join(
                    sorted(
                        data['satellites'])) if data['satellites'] else 'none'
                print(
                    f"  {src[:40]}... -> '{data['name']}' (id: {data['channel_id']}, sats: {sats})")
                sample_count += 1

        # Cerca esempi specifici dai tuoi output
        print("\n🔍 DEBUG - Looking for specific channels from your output:")
        test_srcs = [
            "1_0_16_1005_451_35_C00000_0_0_0",
            "1_0_16_1006_451_35_C00000_0_0_0",
            "1_0_11_BEA_20D0_13E_820000_0_0_0"
        ]

        for test_src in test_srcs:
            if test_src in xml_dict:
                data = xml_dict[test_src]
                print(
                    f"  Found: {test_src} -> '{data['name']}' (id: {data['channel_id']})")
            else:
                print(f"  Not found: {test_src}")

        return xml_dict

    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}


def create_snp_code(channel_name):
    """Create SNP code from channel name - VERSIONE MIGLIORATA"""
    if not channel_name or channel_name.lower() in ['unknown', 'no_epg', '']:
        return "UNKN"

    # Rimuovi numeri satellitari all'inizio (es: "13.0E" o "19.2E")
    clean = re.sub(r'^\d+\.\d+[EW]\s*', '', channel_name)

    # Rimuovi indicatori di qualità
    clean = re.sub(
        r'\s*(?:HD|FHD|UHD|4K|SD|HEVC|H265|H264)\b',
        '',
        clean,
        flags=re.IGNORECASE)

    # Rimuovi tutto dopo certi separatori
    clean = re.split(r'[-–:/()]', clean)[0]

    # Prendi solo lettere (rimuovi numeri e caratteri speciali)
    letters = re.findall(r'[a-zA-Z]', clean)
    clean = ''.join(letters)

    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')

    # Se ancora nulla, prova con il nome originale
    clean_orig = re.sub(r'[^a-zA-Z]', '', channel_name)
    if clean_orig:
        return clean_orig[:4].upper()

    return "CHNL"


def generate_final_mapping():
    print("=" * 80)
    print("GENERATING COMPLETE SRC MAPPING - FINAL VERSION")
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
    xml_dict = parse_xml_for_channels()

    if not xml_dict:
        print("ERROR: Failed to parse XML!")
        return

    # 3. Process PNG paths
    print("\nProcessing PNG paths...")
    png_srcs = defaultdict(set)

    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src and satellite:
            png_srcs[src].add(satellite)

    print(f"Found {len(png_srcs)} unique SRCs in PNG directories")

    # 4. Calcola statistiche
    all_srcs = set(list(xml_dict.keys()) + list(png_srcs.keys()))
    srcs_in_both = set(xml_dict.keys()) & set(png_srcs.keys())
    srcs_only_in_xml = set(xml_dict.keys()) - set(png_srcs.keys())
    srcs_only_in_png = set(png_srcs.keys()) - set(xml_dict.keys())

    print(f"\n📊 STATISTICS:")
    print(f"  Total unique SRCs: {len(all_srcs):,}")
    print(f"  SRCs in both XML and PNG: {len(srcs_in_both):,}")
    print(f"  SRCs only in XML (need PNGs): {len(srcs_only_in_xml):,}")
    print(f"  SRCs only in PNG (need XML entries): {len(srcs_only_in_png):,}")

    # 5. Genera src_mapping.txt
    print("\n📁 Generating src_mapping.txt...")
    mapping_lines = []

    # Contatori per statistiche
    known_with_name = 0
    known_without_name = 0
    unknown = 0

    # Processa tutti gli SRC nei PNG
    for src in sorted(png_srcs.keys()):
        satellites = png_srcs[src]

        # Determina nome e SNP
        if src in xml_dict:
            xml_data = xml_dict[src]
            channel_name = xml_data['name']

            # Controlla se il nome è valido o è solo ID/satellite
            if (channel_name and
                channel_name != xml_data['channel_id'] and
                not re.match(r'^\d+\.\d+[EW]', channel_name) and
                    len(channel_name) > 3):

                snp_code = create_snp_code(channel_name)
                known_with_name += 1
            else:
                # Nome non valido, usa UNKN
                snp_code = "UNKN"
                known_without_name += 1
        else:
            snp_code = "UNKN"
            unknown += 1

        # Combina satelliti (XML + PNG)
        all_satellites = set(satellites)
        if src in xml_dict:
            all_satellites.update(xml_dict[src]['satellites'])

        # Ordina satelliti
        def sat_sort_key(s):
            match = re.match(r'(\d+\.?\d*)([EW])', s)
            if match:
                num = float(match.group(1))
                return -num if match.group(2) == 'W' else num
            return 999

        sorted_sats = sorted(all_satellites, key=sat_sort_key)
        satellites_str = '|'.join(sorted_sats) if sorted_sats else 'Unknown'

        mapping_lines.append(f"{src} - {snp_code} - {satellites_str}")

    # 6. Genera missing_pngs.txt
    missing_lines = []
    if srcs_only_in_png:
        for src in sorted(srcs_only_in_png):
            satellites = png_srcs[src]
            sat_str = '|'.join(sorted(satellites)) if satellites else 'Unknown'
            missing_lines.append(f"{src} - {sat_str}")

    # 7. Genera xml_without_pngs.txt
    xml_no_png_lines = []
    if srcs_only_in_xml:
        for src in sorted(srcs_only_in_xml):
            if src in xml_dict:
                data = xml_dict[src]
                sats = '|'.join(
                    sorted(
                        data['satellites'])) if data['satellites'] else 'none'
                xml_no_png_lines.append(f"{src} - {data['name']} - {sats}")

    # 8. Scrivi i file
    print("\n💾 Writing files...")

    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
        f.write(f"# Total entries: {len(mapping_lines):,}\n")
        f.write(f"# Known channels with valid names: {known_with_name:,}\n")
        f.write(
            f"# Known channels without valid names: {
                known_without_name:,}\n")
        f.write(f"# Unknown channels (not in XML): {unknown:,}\n")
        f.write("# Generated from logos.txt and rytec.channels.xml\n")
        f.write("# Format example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")

        for line in mapping_lines:
            f.write(line + "\n")

    # File 2: missing_pngs.txt
    with open('missing_pngs.txt', 'w', encoding='utf-8') as f:
        f.write("# PNG files missing in XML (need to add to rytec.channels.xml)\n")
        f.write(f"# Total: {len(missing_lines):,}\n\n")

        if missing_lines:
            for line in missing_lines:
                f.write(line + "\n")
        else:
            f.write("# No missing PNGs found!\n")

    # File 3: xml_without_pngs.txt
    with open('xml_without_pngs.txt', 'w', encoding='utf-8') as f:
        f.write("# Channels in XML but missing PNG files\n")
        f.write(f"# Total: {len(xml_no_png_lines):,}\n")
        f.write("# Consider creating logos for these channels\n\n")

        for line in xml_no_png_lines[:1000]:  # Limita output
            f.write(line + "\n")

        if len(xml_no_png_lines) > 1000:
            f.write(f"\n# ... and {len(xml_no_png_lines) - 1000:,} more\n")

    # 9. Statistiche finali
    print("\n" + "=" * 80)
    print("🎯 FINAL RESULTS")
    print("=" * 80)
    print(f"✅ Processing completed in {time.time() - start_time:.1f} seconds")
    print(f"📊 Total SRCs processed: {len(all_srcs):,}")
    print(
        f"📈 Known with valid names: {
            known_with_name:,} ({
            known_with_name / len(mapping_lines) * 100:.1f}%)")
    print(
        f"📉 Known without valid names: {
            known_without_name:,} ({
            known_without_name / len(mapping_lines) * 100:.1f}%)")
    print(
        f"❓ Unknown (not in XML): {
            unknown:,} ({
            unknown / len(mapping_lines) * 100:.1f}%)")

    # Mostra esempi REALI con nomi
    print(f"\n📄 Sample channels WITH VALID NAMES (first 5):")
    valid_samples = []
    for line in mapping_lines:
        if ' - UNKN - ' not in line:
            valid_samples.append(line)

    for line in valid_samples[:5]:
        print(f"  {line}")

    if not valid_samples:
        print(f"  No valid channel names found!")
        print(f"\n🔍 Debug: checking XML parsing issues...")
        print(f"  Sample XML entries (first 5):")
        for i, (src, data) in enumerate(list(xml_dict.items())[:5]):
            print(
                f"    {src[:30]}... -> '{data['name']}' (id: {data['channel_id']})")

    print(f"\n❓ Sample UNKNOWN channels (first 3):")
    unkn_samples = [line for line in mapping_lines if ' - UNKN - ' in line]
    for line in unkn_samples[:3]:
        print(f"  {line}")

    print(f"\n📁 Files created:")
    print(f"  1. src_mapping.txt - Main mapping file")
    print(f"  2. missing_pngs.txt - PNGs missing in XML")
    print(f"  3. xml_without_pngs.txt - XML channels without PNGs")

    print(f"\n⚠️  ISSUE DIAGNOSIS:")
    if known_with_name == 0:
        print(f"  ❌ Problem: XML parser not extracting channel names correctly")
        print(f"  🔧 Fix: Check regex patterns in parse_xml_for_channels()")
        print(f"  💡 Tip: Manually inspect rytec.channels.xml format")
    else:
        print(f"  ✅ Good: Found {known_with_name:,} channels with valid names")


if __name__ == "__main__":
    generate_final_mapping()
