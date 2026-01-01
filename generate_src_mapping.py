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
    """Parse XML and extract channels with satellites - VERSIONE MIGLIORATA"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print(f"XML size: {len(content):,} bytes")

        # Regex migliorata che funziona con il formato reale
        # Cattura: <!-- satellite --><channel id="id">src</channel><!-- nome
        # canale -->
        pattern = r'(?:<!--\s*([^>]+?)\s*-->\s*)?<channel id="([^"]+)">([^<]+)</channel>\s*(?:<!--\s*([^>]+?)\s*-->)?'
        matches = re.findall(pattern, content)

        print(f"Found {len(matches):,} channel entries in XML")

        xml_dict = {}
        current_satellite = ""

        for match in matches:
            before_comment, channel_id, service_ref, after_comment = match

            # Determina satellite
            satellite = ""
            if before_comment:
                # Cerca posizione satellitare nel commento prima
                sat_match = re.search(r'(\d+(?:\.\d+)?[EW])', before_comment)
                if sat_match:
                    satellite = sat_match.group(1)
                    current_satellite = satellite

            # Se non trovato nel commento prima, usa satellite corrente
            if not satellite and current_satellite:
                satellite = current_satellite

            # Determina nome canale
            channel_name = channel_id  # Default

            if after_comment:
                # Prende il nome dal commento dopo
                channel_name = after_comment.strip()
            elif before_comment and '-->' not in before_comment:
                # Se il commento prima non contiene -->, potrebbe essere il
                # nome
                channel_name = before_comment.strip()

            # Pulisci nome canale
            channel_name = re.sub(
                r'^\d+\.\d+[EW]\s*[-–>]*\s*', '', channel_name)
            channel_name = channel_name.strip()

            # Converti SRC
            service_ref = service_ref.strip().rstrip(':')
            src_png = service_ref.replace(':', '_')

            # Salva
            if src_png not in xml_dict:
                xml_dict[src_png] = {
                    'name': channel_name,
                    'satellites': set(),
                    'channel_id': channel_id
                }

            if satellite:
                xml_dict[src_png]['satellites'].add(satellite)

        print(f"Parsed {len(xml_dict):,} unique SRC entries from XML")

        # Debug: mostra alcuni esempi
        print("\nSample XML entries (first 5):")
        samples = list(xml_dict.items())[:5]
        for src, data in samples:
            sats = ', '.join(
                data['satellites']) if data['satellites'] else 'none'
            print(f"  {src[:50]}... -> '{data['name'][:30]}' (sats: {sats})")

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

    # Rimuovi indicatori comuni
    clean = re.sub(
        r'\b(?:HD|FHD|UHD|4K|SD|HEVC|H265|H264|TV|CHANNEL)\b',
        '',
        channel_name,
        flags=re.IGNORECASE)

    # Rimuovi tutto dopo certi separatori
    clean = re.split(r'[-–:/()]', clean)[0]

    # Rimuovi spazi e caratteri speciali
    clean = re.sub(r'[^a-zA-Z0-9]', '', clean)

    if not clean:
        # Prova con il nome originale senza pulizia estrema
        clean = re.sub(r'[^a-zA-Z]', '', channel_name)

    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')

    return "CHNL"


def get_channel_suggestions(src, xml_dict):
    """Find suggestions for channel name based on SRC pattern"""
    suggestions = []

    # Analizza parti dell'SRC
    parts = src.split('_')
    if len(parts) < 7:
        return suggestions

    # Cerca canali con parti simili
    for xml_src, data in xml_dict.items():
        xml_parts = xml_src.split('_')

        # Confronta parti chiave
        if len(xml_parts) >= 7:
            # Confronta namespace (parte 6) e altre parti
            if parts[5] == xml_parts[5]:  # Namespace simile
                similarity = 0.5
                if parts[3] == xml_parts[3]:  # TS ID simile
                    similarity += 0.3
                if parts[4] == xml_parts[4]:  # ONID simile
                    similarity += 0.2

                if similarity > 0.5:
                    suggestions.append({
                        'src': xml_src,
                        'name': data['name'],
                        'similarity': similarity
                    })

    return sorted(suggestions, key=lambda x: x['similarity'], reverse=True)[:3]


def generate_final_mapping():
    print("=" * 80)
    print("GENERATING COMPLETE SRC MAPPING")
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

    # 3. Process PNG paths
    print("\nProcessing PNG paths...")
    png_srcs = {}

    for i, path in enumerate(png_paths):
        src, satellite = extract_src_and_satellite_from_path(path)
        if src:
            if src not in png_srcs:
                png_srcs[src] = set()
            if satellite:
                png_srcs[src].add(satellite)

    print(f"Found {len(png_srcs):,} unique SRCs in PNG directories")

    # 4. Calcola statistiche
    all_srcs = set(list(xml_dict.keys()) + list(png_srcs.keys()))
    srcs_in_both = set(xml_dict.keys()) & set(png_srcs.keys())
    srcs_only_in_xml = set(xml_dict.keys()) - set(png_srcs.keys())
    srcs_only_in_png = set(png_srcs.keys()) - set(xml_dict.keys())

    print(f"\n📊 STATISTICS:")
    print(f"  ├── Total unique SRCs: {len(all_srcs):,}")
    print(
        f"  ├── SRCs in both XML and PNG: {
            len(srcs_in_both):,} ({
            len(srcs_in_both) / len(all_srcs) * 100:.1f}%)")
    print(
        f"  ├── SRCs only in XML (need PNGs): {
            len(srcs_only_in_xml):,} ({
            len(srcs_only_in_xml) / len(all_srcs) * 100:.1f}%)")
    print(
        f"  └── SRCs only in PNG (need XML entries): {
            len(srcs_only_in_png):,} ({
            len(srcs_only_in_png) / len(all_srcs) * 100:.1f}%)")

    # 5. Genera i file
    print("\n📁 Generating output files...")

    # File 1: src_mapping.txt (solo SRC presenti in PNG)
    mapping_lines = []
    known_count = 0
    unknown_count = 0

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

            known_count += 1
        else:
            snp_code = "UNKN"
            unknown_count += 1

        mapping_lines.append(f"{src} - {snp_code} - {satellites_str}")

    # File 2: missing_pngs_detailed.txt
    missing_detailed = []

    for src in sorted(srcs_only_in_png):
        satellites = png_srcs[src]

        # Cerca suggerimenti
        suggestions = get_channel_suggestions(src, xml_dict)

        # Crea entry dettagliata
        entry = f"🚨 MISSING CHANNEL\n"
        entry += f"SRC: {src}\n"

        if satellites:
            sorted_sats = sorted(satellites)
            entry += f"📡 Satellites: {' | '.join(sorted_sats)}\n"

            # Aggiungi info satelliti comuni
            sat_map = {
                '13.0E': 'Hotbird',
                '19.2E': 'Astra 1KR/1L/1M/1N',
                '23.5E': 'Astra 3B',
                '28.2E': 'Astra 2E/2F/2G',
                '0.8W': 'Thor 5/6/7',
                '4.8E': 'Astra 4A',
                '5.0W': 'Sirius 4',
                '7.0E': 'Eutelsat 7A',
                '9.0E': 'Eutelsat 9A',
                '16.0E': 'Eutelsat 16A',
                '42.0E': 'TurkSat 4A/4B',
                '39.0E': 'Hellas Sat 3/4'
            }

            sat_info = []
            for sat in sorted_sats:
                info = sat_map.get(sat, "")
                sat_info.append(f"{sat} ({info})" if info else sat)

            entry += f"📊 Satellite Info: {', '.join(sat_info)}\n"

        # Analizza SRC
        parts = src.split('_')
        if len(parts) >= 7:
            entry += f"🔧 SRC Analysis:\n"
            entry += f"   Service Type: {
                parts[0]} ({
                'TV' if parts[0] == '1' else 'Radio' if parts[0] == '2' else 'Other'})\n"
            entry += f"   Service ID: {parts[2]}\n"
            entry += f"   TS ID: {parts[3]}\n"
            entry += f"   ONID: {parts[4]}\n"
            entry += f"   Namespace: {parts[5]}\n"

        if suggestions:
            entry += f"💡 Suggestions (similar channels in XML):\n"
            for sug in suggestions:
                entry += f"   • {
                    sug['name']} (similarity: {
                    sug['similarity']:.0%})\n"
                entry += f"     SRC: {sug['src']}\n"

        entry += f"🔗 Search on:\n"
        entry += f"   • KingOfSat: https://en.kingofsat.net/\n"
        if satellites:
            for sat in satellites:
                # Crea URL per ricerca su KingOfSat
                sat_num = sat.replace('E', '').replace('W', '')
                direction = 'east' if 'E' in sat else 'west'
                entry += f"   • KingOfSat {sat}: https://en.kingofsat.net/pos-{sat_num}{direction}.php\n"

        entry += "─" * 60 + "\n"
        missing_detailed.append(entry)

    # 6. Scrivi i file
    print("\n💾 Writing files...")

    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
        f.write(f"# Total entries: {len(mapping_lines):,}\n")
        f.write(
            f"# Known channels: {
                known_count:,} ({
                known_count / len(mapping_lines) * 100:.1f}%)\n")
        f.write(
            f"# Unknown channels: {
                unknown_count:,} ({
                unknown_count / len(mapping_lines) * 100:.1f}%)\n")
        f.write("# Generated from logos.txt and rytec.channels.xml\n")
        f.write("# Format example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")

        for line in sorted(mapping_lines):
            f.write(line + "\n")

    # File 2: missing_pngs_detailed.txt
    with open('missing_pngs_detailed.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("DETAILED REPORT: CHANNELS WITH PNG BUT MISSING IN XML\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"📈 SUMMARY:\n")
        f.write(f"• Total missing channels: {len(srcs_only_in_png):,}\n")
        f.write(
            f"• Percentage of all SRCs: {
                len(srcs_only_in_png) /
                len(all_srcs) *
                100:.1f}%\n")
        f.write(f"• Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("📝 HOW TO USE THIS REPORT:\n")
        f.write("1. For each channel below, check the satellite position\n")
        f.write("2. Visit KingOfSat/LyngSat for that satellite position\n")
        f.write("3. Look for channels with similar parameters (TS ID, ONID, etc.)\n")
        f.write("4. Add the channel to rytec.channels.xml\n")
        f.write("5. Format: <!-- 13.0E --><channel id=\"ChannelName\">1:0:1:XXX:XXX:XXX:XXXXXX:0:0:0:</channel><!-- Channel Name -->\n\n")
        f.write("=" * 80 + "\n\n")

        if missing_detailed:
            for entry in missing_detailed:
                f.write(entry + "\n")
        else:
            f.write("🎉 CONGRATULATIONS! No missing channels found.\n")

    # File 3: missing_pngs_simple.txt
    with open('missing_pngs_simple.txt', 'w', encoding='utf-8') as f:
        f.write("# Simple list of SRCs missing in XML\n")
        f.write(f"# Total: {len(srcs_only_in_png):,}\n")
        f.write("# Use this for batch processing\n\n")

        for src in sorted(srcs_only_in_png):
            f.write(f"{src}\n")

    # File 4: xml_without_pngs.txt
    with open('xml_without_pngs.txt', 'w', encoding='utf-8') as f:
        f.write("# Channels in XML but missing PNG files\n")
        f.write(f"# Total: {len(srcs_only_in_xml):,}\n")
        f.write("# Consider creating PNG logos for these channels\n\n")

        for src in sorted(srcs_only_in_xml):
            if src in xml_dict:
                name = xml_dict[src]['name']
                f.write(f"{src} - {name}\n")

    # File 5: statistics.json
    stats = {
        'total_srcs': len(all_srcs),
        'srcs_in_both': len(srcs_in_both),
        'srcs_only_in_xml': len(srcs_only_in_xml),
        'srcs_only_in_png': len(srcs_only_in_png),
        'coverage_percentage': len(srcs_in_both) / len(all_srcs) * 100,
        'known_channels': known_count,
        'unknown_channels': unknown_count,
        'generated': time.strftime('%Y-%m-%d %H:%M:%S'),
        'execution_time_seconds': time.time() - start_time
    }

    with open('statistics.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # 7. Statistiche finali
    print("\n" + "=" * 80)
    print("🎯 FINAL RESULTS")
    print("=" * 80)
    print(f"✅ Processing completed in {time.time() - start_time:.1f} seconds")
    print(f"📊 Coverage: {len(srcs_in_both) / len(all_srcs) * 100:.1f}%")
    print(
        f"📈 Known channels: {
            known_count:,} ({
            known_count / len(mapping_lines) * 100:.1f}%)")
    print(
        f"❓ Unknown channels: {
            unknown_count:,} ({
            unknown_count / len(mapping_lines) * 100:.1f}%)")

    # Esempi
    print(f"\n📄 Sample known channels (first 5):")
    known_samples = [
        line for line in mapping_lines if ' - UNKN - ' not in line]
    for line in known_samples[:5]:
        print(f"  {line}")

    print(f"\n❓ Sample unknown channels (first 3):")
    unknown_samples = [line for line in mapping_lines if ' - UNKN - ' in line]
    for line in unknown_samples[:3]:
        print(f"  {line}")

    print(f"\n📁 Files created:")
    print(
        f"  1. 📋 src_mapping.txt - Main mapping file ({len(mapping_lines):,} lines)")
    print(f"  2. 🔍 missing_pngs_detailed.txt - Detailed report with suggestions")
    print(f"  3. 📝 missing_pngs_simple.txt - Simple list for copy-paste")
    print(f"  4. 🖼️  xml_without_pngs.txt - Channels needing PNG logos")
    print(f"  5. 📊 statistics.json - Complete statistics")

    print(f"\n🚀 Next steps:")
    print(f"  1. Review missing_pngs_detailed.txt for missing channels")
    print(f"  2. Use satellite websites to identify unknown channels")
    print(f"  3. Add missing entries to rytec.channels.xml")
    print(f"  4. Check xml_without_pngs.txt for channels needing logos")
    print(f"  5. Run again to update coverage percentage")

    print(f"\n🔗 Useful resources:")
    print(f"  • KingOfSat: https://en.kingofsat.net/")
    print(f"  • LyngSat: https://www.lyngsat.com/")
    print(f"  • SatelliTV: https://www.satellitetv.net/")


if __name__ == "__main__":
    generate_final_mapping()
