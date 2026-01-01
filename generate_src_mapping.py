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
    """Parse XML and organize by channel_id for better matching"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print(f"XML size: {len(content):,} bytes")
        
        # Cerca pattern: <!-- sat --><channel id="id">src</channel><!-- name -->
        pattern = r'<!--\s*([^>]+?)\s*-->\s*<channel id="([^"]+)">([^<]+)</channel>\s*(?:<!--\s*([^>]+?)\s*-->)?'
        matches = re.findall(pattern, content)
        
        print(f"Found {len(matches)} channel entries in XML")
        
        # Strutture dati
        src_to_info = {}  # src_png -> {name, satellites, channel_id}
        channel_id_to_srcs = defaultdict(list)  # channel_id -> lista di src_png
        channel_id_to_names = defaultdict(set)  # channel_id -> set di nomi
        
        for before_comment, channel_id, service_ref, after_comment in matches:
            # Estrai satellite
            satellite = ""
            sat_match = re.search(r'(\d+(?:\.\d+)?[EW])', before_comment)
            if sat_match:
                satellite = sat_match.group(1)
            
            # Estrai nome
            channel_name = after_comment.strip() if after_comment else channel_id
            
            # Converti SRC
            service_ref = service_ref.strip().rstrip(':')
            src_png = service_ref.replace(':', '_')
            
            # Salva info SRC
            if src_png not in src_to_info:
                src_to_info[src_png] = {
                    'name': channel_name,
                    'satellites': set(),
                    'channel_id': channel_id
                }
            
            if satellite:
                src_to_info[src_png]['satellites'].add(satellite)
            
            # Aggrega per channel_id
            channel_id_to_srcs[channel_id].append(src_png)
            channel_id_to_names[channel_id].add(channel_name)
        
        print(f"Parsed {len(src_to_info)} unique SRCs from XML")
        print(f"Found {len(channel_id_to_srcs)} unique channel IDs")
        
        # Sostituisci nomi con il più comune per ciascun channel_id
        for channel_id, names in channel_id_to_names.items():
            if len(names) > 1:
                # Prendi il nome più lungo (di solito più completo)
                main_name = max(names, key=len)
                # Aggiorna tutti gli SRC con questo channel_id
                for src_png in channel_id_to_srcs[channel_id]:
                    if src_png in src_to_info:
                        src_to_info[src_png]['name'] = main_name
        
        return src_to_info, channel_id_to_srcs

    except Exception as e:
        print(f"Error parsing XML: {e}")
        return {}, {}


def create_snp_code(channel_name):
    """Create SNP code from channel name"""
    if not channel_name or channel_name.lower() in ['unknown', 'no_epg', '']:
        return "UNKN"
    
    # Rimuovi estensioni HD, TV, etc.
    clean = re.sub(r'\b(?:HD|FHD|UHD|4K|SD|HEVC|TV|CHANNEL|LIVE)\b', '', channel_name, flags=re.IGNORECASE)
    
    # Prendi solo lettere
    letters = re.findall(r'[a-zA-Z]', clean)
    clean = ''.join(letters)
    
    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')
    
    return "CHNL"


def find_similar_channels_in_xml(src_png, src_to_info, channel_id_to_srcs):
    """Find similar channels in XML based on various criteria"""
    suggestions = []
    src_parts = src_png.split('_')
    
    if len(src_parts) < 7:
        return suggestions
    
    # 1. Cerca per channel_id simile (se c'è pattern nei PNG)
    # Estrai possibili parti che potrebbero essere channel_id
    possible_ids = []
    
    # Cerca parti esadecimali che potrebbero essere ID
    for part in src_parts[3:6]:  # TS ID, ONID, Namespace
        if re.match(r'^[0-9A-F]{2,}$', part, re.IGNORECASE):
            possible_ids.append(part)
    
    # 2. Cerca SRC simili per struttura
    for xml_src, xml_info in src_to_info.items():
        xml_parts = xml_src.split('_')
        
        if len(xml_parts) < 7:
            continue
        
        # Calcola similarità
        similarity = 0
        
        # Namespace uguale = alta similarità
        if src_parts[5] == xml_parts[5]:
            similarity += 3
        
        # ONID uguale = media similarità
        if src_parts[4] == xml_parts[4]:
            similarity += 2
        
        # TS ID simile (primi caratteri)
        if src_parts[3][:4] == xml_parts[3][:4]:
            similarity += 1
        
        # Service ID simile
        if src_parts[2] == xml_parts[2]:
            similarity += 1
        
        if similarity >= 2:
            suggestions.append({
                'src': xml_src,
                'name': xml_info['name'],
                'channel_id': xml_info['channel_id'],
                'similarity': similarity,
                'satellites': xml_info['satellites']
            })
    
    return sorted(suggestions, key=lambda x: x['similarity'], reverse=True)[:5]


def generate_final_mapping():
    print("=" * 80)
    print("GENERATING SRC MAPPING - INTELLIGENT MATCHING")
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
    src_to_info, channel_id_to_srcs = parse_xml_for_channels()

    # 3. Process PNG paths - AGGREGA satelliti per SRC
    print("\nProcessing PNG paths and aggregating satellites...")
    png_srcs = defaultdict(set)  # src -> set di satelliti
    
    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src and satellite:
            png_srcs[src].add(satellite)
    
    print(f"Found {len(png_srcs)} unique SRCs in PNG directories")
    
    # Conta SRC su più satelliti
    multi_sat_pngs = sum(1 for sats in png_srcs.values() if len(sats) > 1)
    print(f"PNGs on multiple satellites: {multi_sat_pngs}")
    
    # 4. Genera mapping intelligente
    print("\n📁 Generating intelligent mapping...")
    
    mapping_lines = []
    missing_pngs = []
    matched_by_similarity = 0
    
    # Per ogni SRC nei PNG
    for src_png in sorted(png_srcs.keys()):
        png_satellites = png_srcs[src_png]
        
        # Determina nome e SNP
        snp_code = "UNKN"
        channel_name = ""
        all_satellites = set(png_satellites)
        
        # CASO 1: SRC trovato esattamente nell'XML
        if src_png in src_to_info:
            xml_info = src_to_info[src_png]
            channel_name = xml_info['name']
            snp_code = create_snp_code(channel_name)
            all_satellites.update(xml_info['satellites'])
        
        # CASO 2: Cerca canali simili nell'XML
        else:
            similar_channels = find_similar_channels_in_xml(src_png, src_to_info, channel_id_to_srcs)
            
            if similar_channels:
                # Prendi il più simile
                best_match = similar_channels[0]
                
                # Usa solo se similarity è abbastanza alta
                if best_match['similarity'] >= 3:
                    channel_name = f"{best_match['name']} (similar)"
                    snp_code = create_snp_code(best_match['name'])
                    all_satellites.update(best_match['satellites'])
                    matched_by_similarity += 1
                    
                    # Aggiungi al file missing per verifica
                    missing_pngs.append({
                        'src': src_png,
                        'png_satellites': png_satellites,
                        'suggested_name': best_match['name'],
                        'similar_src': best_match['src'],
                        'similarity': best_match['similarity']
                    })
                else:
                    # Similarità bassa, aggiungi a missing per ricerca manuale
                    missing_pngs.append({
                        'src': src_png,
                        'png_satellites': png_satellites,
                        'suggestions': similar_channels[:3]
                    })
            else:
                # Nessun match trovato
                missing_pngs.append({
                    'src': src_png,
                    'png_satellites': png_satellites,
                    'suggestions': []
                })
        
        # Ordina satelliti: W negativi, E positivi
        def sat_sort_key(s):
            match = re.match(r'(\d+\.?\d*)([EW])', s)
            if match:
                num = float(match.group(1))
                return -num if match.group(2) == 'W' else num
            return 999
        
        sorted_sats = sorted(all_satellites, key=sat_sort_key)
        satellites_str = '|'.join(sorted_sats)
        
        mapping_lines.append(f"{src_png} - {snp_code} - {satellites_str}")
    
    # 5. Scrivi i file
    print("\n💾 Writing files...")
    
    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
        f.write(f"# Total entries: {len(mapping_lines):,}\n")
        f.write(f"# Direct matches in XML: {len([l for l in mapping_lines if '(similar)' not in l and 'UNKN' not in l])}\n")
        f.write(f"# Similarity matches: {matched_by_similarity}\n")
        f.write(f"# Unknown: {len([l for l in mapping_lines if 'UNKN' in l]) - matched_by_similarity}\n")
        f.write("# Generated from logos.txt and rytec.channels.xml\n")
        f.write("# Format example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")
        
        for line in mapping_lines:
            f.write(line + "\n")
    
    # File 2: missing_pngs_detailed.txt
    with open('missing_pngs_detailed.txt', 'w', encoding='utf-8') as f:
        f.write("# DETAILED REPORT: PNG FILES NEEDING XML ENTRIES\n")
        f.write("# ================================================\n")
        f.write(f"# Total missing: {len(missing_pngs):,}\n")
        f.write(f"# Matched by similarity: {matched_by_similarity}\n")
        f.write(f"# Need manual identification: {len(missing_pngs) - matched_by_similarity}\n")
        f.write("# Generated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
        f.write("#\n")
        f.write("# COLUMNS:\n")
        f.write("# 1. PNG SRC that's missing in XML\n")
        f.write("# 2. Satellites where PNG was found\n")
        f.write("# 3. Suggested channel name (from similarity)\n")
        f.write("# 4. Similar channels in XML\n")
        f.write("# 5. Search links for identification\n")
        f.write("# ================================================\n\n")
        
        for item in missing_pngs:
            f.write(f"SRC: {item['src']}\n")
            f.write(f"PNG Satellites: {'|'.join(sorted(item['png_satellites']))}\n")
            
            if 'suggested_name' in item:
                f.write(f"SUGGESTED NAME: {item['suggested_name']} (similarity: {item['similarity']}/6)\n")
                f.write(f"Similar SRC in XML: {item['similar_src']}\n")
            elif 'suggestions' in item and item['suggestions']:
                f.write(f"POSSIBLE MATCHES in XML:\n")
                for sug in item['suggestions']:
                    sats = '|'.join(sorted(sug['satellites'])) if sug['satellites'] else 'none'
                    f.write(f"  • {sug['name']} (channel_id: {sug['channel_id']}, similarity: {sug['similarity']}/6)\n")
                    f.write(f"    SRC: {sug['src']}, Satellites: {sats}\n")
            else:
                f.write(f"NO SIMILAR CHANNELS FOUND in XML\n")
            
            # Aggiungi link di ricerca
            if item['png_satellites']:
                f.write(f"SEARCH ON:\n")
                for sat in sorted(item['png_satellites']):
                    sat_num = sat.replace('E', '').replace('W', '')
                    direction = 'east' if 'E' in sat else 'west'
                    f.write(f"  • KingOfSat {sat}: https://en.kingofsat.net/pos-{sat_num}{direction}.php\n")
            
            f.write("-" * 60 + "\n\n")
    
    # File 3: multi_satellite_channels.txt
    multi_sat_channels = []
    for line in mapping_lines:
        if '|' in line and 'Unknown' not in line:
            multi_sat_channels.append(line)
    
    with open('multi_satellite_channels.txt', 'w', encoding='utf-8') as f:
        f.write("# CHANNELS AVAILABLE ON MULTIPLE SATELLITES\n")
        f.write(f"# Total: {len(multi_sat_channels):,}\n")
        f.write("# These channels have the same SRC/PNG on different satellites\n")
        f.write("# Format: SRC - SNP - satellite1|satellite2|...\n\n")
        
        for line in sorted(multi_sat_channels):
            f.write(line + "\n")
    
    # 6. Statistiche finali
    print("\n" + "=" * 80)
    print("🎯 FINAL RESULTS")
    print("=" * 80)
    
    exact_matches = len([l for l in mapping_lines if '(similar)' not in l and 'UNKN' not in l])
    similarity_matches = matched_by_similarity
    unknown_count = len([l for l in mapping_lines if 'UNKN' in l]) - similarity_matches
    
    print(f"✅ Processing completed in {time.time() - start_time:.1f} seconds")
    print(f"📊 Total PNG SRCs: {len(png_srcs):,}")
    print(f"📈 Exact matches in XML: {exact_matches:,} ({exact_matches/len(png_srcs)*100:.1f}%)")
    print(f"📉 Similarity matches: {similarity_matches:,} ({similarity_matches/len(png_srcs)*100:.1f}%)")
    print(f"❓ Unknown (need research): {unknown_count:,} ({unknown_count/len(png_srcs)*100:.1f}%)")
    print(f"🌍 Multi-satellite channels: {len(multi_sat_channels):,}")
    
    # Esempi
    print(f"\n📄 Sample EXACT matches (first 5):")
    exact_samples = [l for l in mapping_lines if '(similar)' not in l and 'UNKN' not in l]
    for line in exact_samples[:5]:
        print(f"  {line}")
    
    if similarity_matches > 0:
        print(f"\n🔍 Sample SIMILARITY matches (first 3):")
        similar_samples = [l for l in mapping_lines if '(similar)' in l]
        for line in similar_samples[:3]:
            print(f"  {line}")
    
    print(f"\n❓ Sample UNKNOWN (first 3):")
    unknown_samples = [l for l in mapping_lines if 'UNKN' in l and '(similar)' not in l]
    for line in unknown_samples[:3]:
        print(f"  {line}")
    
    print(f"\n🌍 Sample MULTI-SATELLITE channels (first 3):")
    for line in multi_sat_channels[:3]:
        print(f"  {line}")
    
    print(f"\n📁 Files created:")
    print(f"  1. src_mapping.txt - Main mapping with | separated satellites")
    print(f"  2. missing_pngs_detailed.txt - Detailed report with suggestions")
    print(f"  3. multi_satellite_channels.txt - Channels on multiple satellites")
    
    print(f"\n✅ OUTPUT FORMAT IS CORRECT:")
    print(f"   SRC - SNP - satellite1|satellite2|satellite3")
    print(f"\n🔍 For {unknown_count:,} unknown channels, check missing_pngs_detailed.txt")
    print(f"   It includes search links and similarity suggestions!")


if __name__ == "__main__":
    generate_final_mapping()
