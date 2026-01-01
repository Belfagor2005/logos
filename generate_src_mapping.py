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
    """Parse XML using the exact regex pattern from your code"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print(f"XML size: {len(content)} bytes")
        
        # USA LA STESSA REGEX DEL TUO PARSER
        pattern = r'(<!--\s*([^>]+)\s*-->)?\s*<channel id="([^"]+)">([^<]+)</channel>\s*(?:<!--\s*([^>]+)\s*-->)?'
        matches = re.findall(pattern, content)
        
        print(f"Found {len(matches)} channel entries in XML")
        
        xml_dict = defaultdict(lambda: {'name': '', 'satellites': set()})
        
        for match in matches:
            comment_before, source_info, channel_id, service_ref, comment_after = match
            comment = comment_before or comment_after or ""
            
            # Estrai nome canale dal commento
            channel_name = ""
            if comment:
                # Rimuovi info satellite e altre cose dal commento
                # Esempio: "16.0E --><channel id="ZicoTV.rs">" o "<!-- Zico TV -->"
                clean_comment = comment.strip()
                
                # Se contiene -->, prendi solo la parte dopo
                if '-->' in clean_comment:
                    clean_comment = clean_comment.split('-->')[-1].strip()
                
                # Rimuovi eventuali <channel...> tag
                clean_comment = re.sub(r'<[^>]+>', '', clean_comment)
                
                # Se è vuoto, usa channel_id
                if clean_comment and not clean_comment.startswith('channel'):
                    channel_name = clean_comment
                else:
                    channel_name = channel_id
            else:
                channel_name = channel_id
            
            # Estrai posizione satellitare dal source_info (comment_before)
            satellite = ""
            if source_info:
                # Cerca posizione satellitare (es: "16.0E")
                sat_match = re.search(r'(\d+(?:\.\d+)?[EW])', source_info)
                if sat_match:
                    satellite = sat_match.group(1)
            
            # Converti service_ref in formato PNG
            # Formato: 1:0:1:9:1:1:A00000:0:0:0:
            service_ref = service_ref.strip().rstrip(':')
            src_png = service_ref.replace(':', '_')
            
            # Aggiorna dizionario
            if not xml_dict[src_png]['name'] or xml_dict[src_png]['name'] == channel_id:
                xml_dict[src_png]['name'] = channel_name
            
            if satellite:
                xml_dict[src_png]['satellites'].add(satellite)
            
            # DEBUG: mostra primi 5
            if len(xml_dict) <= 5:
                print(f"  Parsed: {src_png} -> '{channel_name}' (sat: {satellite})")

        print(f"\nParsed {len(xml_dict)} unique SRC entries from XML")
        
        return dict(xml_dict)

    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}


def create_snp_code(channel_name):
    """Create SNP code from channel name"""
    if not channel_name or channel_name.lower() in ['unknown', '']:
        return "UNKN"
    
    # Rimuovi estensioni comuni
    clean_name = re.sub(r'\s*(?:HD|FHD|UHD|4K|SD|HEVC|H265|H264|\.\w{2,4})$', '', channel_name, flags=re.IGNORECASE)
    
    # Rimuovi caratteri speciali, mantieni lettere e numeri
    clean_name = re.sub(r'[^a-zA-Z0-9À-ÿ]', '', clean_name)
    
    if not clean_name:
        # Se non rimane nulla, prendi prime lettere dal nome originale
        clean_name = re.sub(r'[^a-zA-Z]', '', channel_name)
    
    if len(clean_name) >= 4:
        return clean_name[:4].upper()
    elif clean_name:
        return clean_name.upper().ljust(4, 'X')
    
    return "CHNL"


def extract_real_channel_name(comment):
    """Extract real channel name from comment like your _extract_real_channel_name method"""
    if not comment:
        return ""
    
    # Rimuovi info satellite e altre cose
    name = comment.strip()
    
    # Rimuovi tutto prima di --> se presente
    if '-->' in name:
        name = name.split('-->')[-1].strip()
    
    # Rimuovi eventuali tag HTML/XML
    name = re.sub(r'<[^>]+>', '', name)
    
    # Rimuovi parentesi e contenuto
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    
    # Rimuovi indicatori di qualità
    name = re.sub(r'\s*(?:HD|FHD|UHD|4K|SD|HEVC)\b', '', name, flags=re.IGNORECASE)
    
    # Rimuovi punteggiatura finale
    name = name.strip(' -')
    
    return name


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
    png_srcs = defaultdict(set)
    
    for path in png_paths:
        src, satellite = extract_src_and_satellite_from_path(path)
        if src:
            if satellite:
                png_srcs[src].add(satellite)
            else:
                png_srcs[src].add("Unknown")
    
    print(f"Found {len(png_srcs)} unique SRCs in PNG directories")
    
    # 4. Genera i due file
    print("\nGenerating output files...")
    
    mapping_lines = []
    missing_png_lines = []
    
    # Contatori
    xml_count = 0
    png_only_count = 0
    
    # Prima: processa SRC nell'XML
    for src in sorted(xml_dict.keys()):
        xml_data = xml_dict[src]
        channel_name = xml_data['name']
        
        # Usa extract_real_channel_name per pulire meglio
        clean_name = extract_real_channel_name(channel_name)
        if not clean_name:
            clean_name = channel_name
        
        snp_code = create_snp_code(clean_name)
        
        # Combina satelliti
        all_satellites = set(xml_data['satellites'])
        if src in png_srcs:
            all_satellites.update(png_srcs[src])
            del png_srcs[src]  # Rimuovi dai PNG processati
        
        # Ordina satelliti
        def sat_sort_key(s):
            if not s or s == "Unknown":
                return (1, 9999)
            match = re.match(r'(\d+\.?\d*)([EW])', s)
            if match:
                num = float(match.group(1))
                direction = match.group(2)
                # W negativi, E positivi
                return (0, -num if direction == 'W' else num + 360)
            return (1, 9999)
        
        sorted_satellites = sorted(all_satellites, key=sat_sort_key)
        satellites_str = '|'.join(sorted_satellites) if sorted_satellites else 'Unknown'
        
        mapping_lines.append(f"{src} - {snp_code} - {satellites_str}")
        xml_count += 1
    
    # Secondo: processa SRC solo nei PNG
    for src in sorted(png_srcs.keys()):
        satellites = png_srcs[src]
        
        # Ordina satelliti
        sorted_satellites = sorted(satellites)
        satellites_str = '|'.join(sorted_satellites) if sorted_satellites else 'Unknown'
        
        mapping_lines.append(f"{src} - UNKN - {satellites_str}")
        png_only_count += 1
        
        # Aggiungi ai missing PNGs
        for satellite in sorted_satellites:
            missing_png_lines.append(f"{src} - Found in PNG at {satellite} but not in XML")
    
    # 5. Scrivi i file
    print("\nWriting files...")
    
    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC (codice) - SNP (codice abbreviato del nome del canale) - posizioni satellitari disponibili\n")
        f.write(f"# Total entries: {len(mapping_lines)}\n")
        f.write(f"# From XML: {xml_count}, PNG only: {png_only_count}\n")
        f.write("# Generated from logos.txt and rytec.channels.xml\n")
        f.write("# Format example: 1_0_16_105_F01_20CB_EEEE0000_0_0_0 - filmbox premium - 23.5E|16.0E|13.0E|0.8W\n\n")
        
        for line in sorted(mapping_lines):
            f.write(line + "\n")
    
    # File 2: missing_pngs.txt
    with open('missing_pngs.txt', 'w', encoding='utf-8') as f:
        f.write("# PNG files that need to be added to XML\n")
        f.write(f"# Total missing: {len(missing_png_lines)}\n")
        f.write("# These SRC codes exist in PNG files but not in rytec.channels.xml\n\n")
        
        if missing_png_lines:
            for line in sorted(missing_png_lines):
                f.write(line + "\n")
        else:
            f.write("# No missing PNGs found!\n")
    
    # 6. Statistiche
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY:")
    print(f"Total PNG SRCs: {xml_count + png_only_count}")
    print(f"SRCs found in XML: {xml_count}")
    print(f"SRCs only in PNG (need XML entries): {png_only_count}")
    
    # Mostra esempi con SNP diversi da UNKN
    print(f"\nSample entries with channel names (first 5):")
    samples_with_names = [line for line in mapping_lines if ' - UNKN - ' not in line]
    for line in samples_with_names[:5]:
        print(f"  {line}")
    
    print(f"\nSample UNKN entries (first 3):")
    samples_unkn = [line for line in mapping_lines if ' - UNKN - ' in line]
    for line in samples_unkn[:3]:
        print(f"  {line}")
    
    print(f"\nFiles created:")
    print(f"  src_mapping.txt - Main mapping file")
    print(f"  missing_pngs.txt - PNGs that need XML entries")


if __name__ == "__main__":
    generate_final_mapping()
