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
    """Parse XML and extract ALL satellites for each SRC"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print(f"XML size: {len(content):,} bytes")
        
        # Crea dizionari per aggregare
        src_to_channels = defaultdict(list)  # src -> lista di (nome, satellite)
        src_to_satellites = defaultdict(set)  # src -> set di satelliti
        src_to_names = defaultdict(set)  # src -> set di nomi
        
        lines = content.split('\n')
        current_satellite = ""
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Cerca commento con satellite
            if line.startswith('<!--') and '-->' in line and '<channel' not in line:
                sat_match = re.search(r'<!--\s*([^>]+?)\s*-->', line)
                if sat_match:
                    sat_text = sat_match.group(1).strip()
                    # Cerca posizione satellitare
                    sat_pos_match = re.search(r'(\d+(?:\.\d+)?[EW])', sat_text)
                    if sat_pos_match:
                        current_satellite = sat_pos_match.group(1)
                    else:
                        current_satellite = ""
            
            # Cerca linea con channel
            elif '<channel id="' in line and '>' in line:
                # Estrai ID canale
                id_match = re.search(r'id="([^"]+)"', line)
                channel_id = id_match.group(1) if id_match else "unknown"
                
                # Estrai SRC (formato: 1:0:1:9:1:1:A00000:0:0:0:)
                src_match = re.search(r'>([0-9A-Fa-f_:]+:?)<', line)
                if src_match:
                    src_xml = src_match.group(1).rstrip(':')
                    src_png = src_xml.replace(':', '_')
                    
                    # Estrai nome canale dal commento finale
                    name_match = re.search(r'<!--\s*(.+?)\s*-->$', line)
                    channel_name = name_match.group(1).strip() if name_match else channel_id
                    
                    # Pulisci nome canale
                    channel_name = re.sub(r'^\s*[-–>]*\s*', '', channel_name)
                    
                    # Aggrega dati
                    src_to_channels[src_png].append((channel_name, current_satellite))
                    if current_satellite:
                        src_to_satellites[src_png].add(current_satellite)
                    src_to_names[src_png].add(channel_name)
        
        print(f"Found {len(src_to_channels)} unique SRCs in XML")
        
        # Crea dizionario finale con nome principale e tutti i satelliti
        xml_dict = {}
        for src, channels in src_to_channels.items():
            # Prendi il nome più comune (o il primo)
            names = list(src_to_names[src])
            main_name = names[0] if names else "Unknown"
            
            # Se ci sono più nomi, scegli il più corto (solitamente il nome base)
            if len(names) > 1:
                shortest_name = min(names, key=len)
                if len(shortest_name) > 3:  # Evita nomi troppo corti
                    main_name = shortest_name
            
            xml_dict[src] = {
                'name': main_name,
                'satellites': src_to_satellites[src],
                'all_names': names,
                'all_entries': channels
            }
        
        print(f"Parsed {len(xml_dict)} unique SRC entries from XML")
        
        # Esempi di aggregazione
        print("\n📡 Sample XML entries with multiple satellites (first 3):")
        multi_sat_samples = [(src, data) for src, data in xml_dict.items() 
                           if len(data['satellites']) > 1][:3]
        for src, data in multi_sat_samples:
            print(f"  {src[:40]}...")
            print(f"    Name: {data['name']}")
            print(f"    Satellites: {', '.join(sorted(data['satellites']))}")
        
        return xml_dict

    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}


def create_snp_code(channel_name):
    """Create SNP code from channel name"""
    if not channel_name or channel_name.lower() in ['unknown', 'no_epg', '']:
        return "UNKN"
    
    # Pulisci nome
    clean = re.sub(r'\b(?:HD|FHD|UHD|4K|SD|HEVC|H265|H264|TV|CHANNEL)\b', '', channel_name, flags=re.IGNORECASE)
    clean = re.sub(r'[^a-zA-Z0-9]', '', clean)
    
    if not clean:
        clean = re.sub(r'[^a-zA-Z]', '', channel_name)
    
    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')
    
    return "CHNL"


def generate_final_mapping():
    print("=" * 80)
    print("GENERATING COMPLETE SRC MAPPING WITH AGGREGATED SATELLITES")
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

    # 3. Process PNG paths - Aggrega tutti i satelliti dai PNG
    print("\nProcessing PNG paths and aggregating satellites...")
    png_srcs = defaultdict(set)  # src -> set di satelliti
    
    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src:
            if satellite:
                png_srcs[src].add(satellite)
    
    print(f"Found {len(png_srcs)} unique SRCs in PNG directories")
    
    # 4. Calcola statistiche
    all_srcs = set(list(xml_dict.keys()) + list(png_srcs.keys()))
    srcs_in_both = set(xml_dict.keys()) & set(png_srcs.keys())
    srcs_only_in_xml = set(xml_dict.keys()) - set(png_srcs.keys())
    srcs_only_in_png = set(png_srcs.keys()) - set(xml_dict.keys())
    
    print(f"\n📊 STATISTICS:")
    print(f"  ├── Total unique SRCs: {len(all_srcs):,}")
    print(f"  ├── SRCs in both XML and PNG: {len(srcs_in_both):,} ({len(srcs_in_both)/len(all_srcs)*100:.1f}%)")
    print(f"  ├── SRCs only in XML (need PNGs): {len(srcs_only_in_xml):,} ({len(srcs_only_in_xml)/len(all_srcs)*100:.1f}%)")
    print(f"  └── SRCs only in PNG (need XML entries): {len(srcs_only_in_png):,} ({len(srcs_only_in_png)/len(all_srcs)*100:.1f}%)")
    
    # 5. Genera i file
    print("\n📁 Generating output files...")
    
    # File 1: src_mapping.txt con satelliti aggregati
    mapping_lines = []
    
    # Prima: SRC in entrambi (XML e PNG)
    for src in sorted(srcs_in_both):
        xml_data = xml_dict[src]
        channel_name = xml_data['name']
        snp_code = create_snp_code(channel_name)
        
        # COMBINA TUTTI I SATELLITI: da XML + da PNG
        all_satellites = set(xml_data['satellites']) | png_srcs[src]
        
        # Ordina satelliti: prima W (ovest), poi E (est)
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
        
        sorted_sats = sorted(all_satellites, key=sat_sort_key)
        satellites_str = '|'.join(sorted_sats) if sorted_sats else 'Unknown'
        
        mapping_lines.append(f"{src} - {snp_code} - {satellites_str}")
    
    # Secondo: SRC solo in PNG
    for src in sorted(srcs_only_in_png):
        satellites = png_srcs[src]
        snp_code = "UNKN"
        
        # Ordina satelliti
        def sat_sort_key(s):
            if not s:
                return (1, 9999)
            match = re.match(r'(\d+\.?\d*)([EW])', s)
            if match:
                num = float(match.group(1))
                direction = match.group(2)
                return (0, -num if direction == 'W' else num)
            return (1, 9999)
        
        sorted_sats = sorted(satellites, key=sat_sort_key)
        satellites_str = '|'.join(sorted_sats) if sorted_sats else 'Unknown'
        
        mapping_lines.append(f"{src} - {snp_code} - {satellites_str}")
    
    # 6. Crea file dettagliato per PNG mancanti
    missing_detailed = []
    
    for src in sorted(srcs_only_in_png):
        satellites = png_srcs[src]
        
        # Cerca SRC simili nell'XML
        similar_srcs = []
        src_parts = src.split('_')
        
        for xml_src, xml_data in xml_dict.items():
            xml_parts = xml_src.split('_')
            if len(src_parts) >= 7 and len(xml_parts) >= 7:
                # Confronta parti chiave
                matches = 0
                # Namespace (parte 6) è importante
                if src_parts[5] == xml_parts[5]:
                    matches += 2
                # TS ID (parte 3)
                if src_parts[3] == xml_parts[3]:
                    matches += 1
                # ONID (parte 4)
                if src_parts[4] == xml_parts[4]:
                    matches += 1
                
                if matches >= 2:
                    similar_srcs.append({
                        'src': xml_src,
                        'name': xml_data['name'],
                        'matches': matches,
                        'satellites': xml_data['satellites']
                    })
        
        # Crea entry dettagliata
        entry = f"🚨 MISSING CHANNEL\n"
        entry += f"SRC: {src}\n"
        
        if satellites:
            sorted_sats = sorted(satellites)
            entry += f"📡 Found on satellites: {' | '.join(sorted_sats)}\n"
        
        if similar_srcs:
            entry += f"💡 Similar channels in XML:\n"
            for sim in sorted(similar_srcs, key=lambda x: x['matches'], reverse=True)[:3]:
                sat_str = '|'.join(sorted(sim['satellites'])) if sim['satellites'] else 'Unknown'
                entry += f"  • {sim['name']} (matches: {sim['matches']})\n"
                entry += f"    SRC: {sim['src']}\n"
                entry += f"    XML satellites: {sat_str}\n"
        
        # Suggerimenti di ricerca
        if satellites:
            entry += f"🔍 Search suggestions:\n"
            for sat in sorted(satellites):
                sat_num = sat.replace('E', '').replace('W', '')
                direction = 'east' if 'E' in sat else 'west'
                entry += f"  • KingOfSat {sat}: https://en.kingofsat.net/pos-{sat_num}{direction}.php\n"
        
        entry += "─" * 60 + "\n"
        missing_detailed.append(entry)
    
    # 7. Scrivi i file
    print("\n💾 Writing files...")
    
    # File 1: src_mapping.txt (formato corretto con satelliti aggregati)
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
        f.write(f"# Total entries: {len(mapping_lines):,}\n")
        f.write(f"# Known channels (in XML): {len(srcs_in_both):,}\n")
        f.write(f"# Unknown channels (not in XML): {len(srcs_only_in_png):,}\n")
        f.write("# Generated from logos.txt and rytec.channels.xml\n")
        f.write("# Format: SRC - SNP - satellite1|satellite2|satellite3\n")
        f.write("# Example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")
        
        for line in sorted(mapping_lines):
            f.write(line + "\n")
    
    # File 2: missing_pngs_detailed.txt
    with open('missing_pngs_detailed.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("DETAILED REPORT: PNG FILES MISSING IN XML\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"📈 SUMMARY:\n")
        f.write(f"• Total missing: {len(srcs_only_in_png):,} channels\n")
        f.write(f"• Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if missing_detailed:
            for entry in missing_detailed:
                f.write(entry + "\n")
        else:
            f.write("🎉 CONGRATULATIONS! All PNGs have corresponding XML entries.\n")
    
    # File 3: missing_pngs_simple.txt
    with open('missing_pngs_simple.txt', 'w', encoding='utf-8') as f:
        f.write("# Simple list of SRCs missing in XML\n")
        f.write(f"# Total: {len(srcs_only_in_png):,}\n\n")
        
        for src in sorted(srcs_only_in_png):
            satellites = '|'.join(sorted(png_srcs[src])) if png_srcs[src] else 'Unknown'
            f.write(f"{src} - Found on: {satellites}\n")
    
    # File 4: xml_without_pngs.txt
    with open('xml_without_pngs.txt', 'w', encoding='utf-8') as f:
        f.write("# Channels in XML but missing PNG files\n")
        f.write(f"# Total: {len(srcs_only_in_xml):,}\n\n")
        
        for src in sorted(srcs_only_in_xml)[:1000]:  # Limita a 1000 per leggibilità
            if src in xml_dict:
                data = xml_dict[src]
                sats = '|'.join(sorted(data['satellites'])) if data['satellites'] else 'Unknown'
                f.write(f"{src} - {data['name']} - {sats}\n")
        
        if len(srcs_only_in_xml) > 1000:
            f.write(f"\n# ... and {len(srcs_only_in_xml) - 1000:,} more\n")
    
    # File 5: multi_satellite_channels.txt
    multi_sat_channels = []
    for src in sorted(srcs_in_both):
        xml_sats = xml_dict[src]['satellites']
        png_sats = png_srcs[src]
        all_sats = xml_sats | png_sats
        
        if len(all_sats) > 1:
            channel_name = xml_dict[src]['name']
            snp_code = create_snp_code(channel_name)
            sorted_sats = sorted(all_sats)
            satellites_str = '|'.join(sorted_sats)
            multi_sat_channels.append(f"{src} - {snp_code} - {satellites_str}")
    
    with open('multi_satellite_channels.txt', 'w', encoding='utf-8') as f:
        f.write("# Channels available on multiple satellites\n")
        f.write(f"# Total: {len(multi_sat_channels):,}\n\n")
        
        for line in multi_sat_channels:
            f.write(line + "\n")
    
    # 8. Statistiche finali
    print("\n" + "=" * 80)
    print("🎯 FINAL RESULTS")
    print("=" * 80)
    print(f"✅ Processing completed in {time.time() - start_time:.1f} seconds")
    print(f"📊 Coverage: {len(srcs_in_both)/len(all_srcs)*100:.1f}%")
    print(f"📈 Multi-satellite channels: {len(multi_sat_channels):,}")
    
    # Esempi di canali con più satelliti
    print(f"\n🌍 Sample multi-satellite channels (first 5):")
    if multi_sat_channels:
        for line in multi_sat_channels[:5]:
            print(f"  {line}")
    else:
        print("  No multi-satellite channels found")
    
    # Esempi del file principale
    print(f"\n📄 Sample from src_mapping.txt (first 5):")
    for line in sorted(mapping_lines)[:5]:
        print(f"  {line}")
    
    print(f"\n📁 Files created:")
    print(f"  1. 📋 src_mapping.txt - Main mapping with aggregated satellites")
    print(f"  2. 🔍 missing_pngs_detailed.txt - Detailed report")
    print(f"  3. 📝 missing_pngs_simple.txt - Simple list")
    print(f"  4. 🖼️  xml_without_pngs.txt - Channels needing PNGs")
    print(f"  5. 🌍 multi_satellite_channels.txt - Channels on multiple satellites")
    
    print(f"\n✅ Output format is now CORRECT:")
    print(f"   SRC - SNP - satellite1|satellite2|satellite3")
    print(f"\n🔗 Example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W")


if __name__ == "__main__":
    generate_final_mapping()
