# -*- coding: utf-8 -*-
# generate_src_mapping_final_working.py
import requests
import re
from collections import defaultdict

def get_png_files():
    """Get all PNG files"""
    url = "https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF"
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'SRC-Mapping-Generator'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"API returned status {response.status_code}")
            return []
            
        data = response.json()
        png_files = []
        
        for item in data:
            if isinstance(item, dict):
                filename = item.get('name', '')
                if filename.endswith('.png'):
                    png_files.append(filename)
        
        print(f"Found {len(png_files)} PNG files")
        return png_files
        
    except Exception as e:
        print(f"Error getting PNG files: {e}")
        return []

def parse_xml_correctly():
    """Parse XML CORRECTLY - now we understand the format!"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    
    try:
        response = requests.get(xml_url, timeout=60)
        xml_data = response.text
        
        # Dizionario: SRC_PNG -> {name, satellites}
        xml_mappings = defaultdict(lambda: {'name': '', 'satellites': set()})
        current_satellite = ""
        
        lines = xml_data.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 1. Cerca satellite nei commenti
            # Formati: <!-- 13.0E -->, <!-- DVB-T -->, <!-- 0.8W -->
            if line.startswith('<!--') and '-->' in line and not '<channel' in line:
                comment = line[4:-3].strip()  # Rimuove <!-- e -->
                
                # Cerca coordinate satellitari
                if any(x in comment for x in ['E', 'W', 'DVB']):
                    current_satellite = comment
            
            # 2. Cerca canale
            elif '<channel id="' in line and '>' in line:
                # Estrai ID
                id_match = re.search(r'id="([^"]+)"', line)
                channel_id = id_match.group(1) if id_match else ""
                
                # Estrai SRC - IL FORMATO ESATTO!
                # Pattern: 1:0:19:64:200:1D:EEEE0000:0:0:0:
                src_match = re.search(r'>([0-9]:[0-9]:[0-9A-F]+:[0-9A-F]+:[0-9A-F]+:[0-9A-F]+:[0-9A-F]+:[0-9]:[0-9]:[0-9]:)<', line)
                
                if src_match:
                    src_xml = src_match.group(1)
                    
                    # Converti a formato PNG
                    # Rimuovi l'ultimo : e sostituisci : con _
                    src_png = src_xml.rstrip(':').replace(':', '_')
                    
                    # Estrai nome canale dal commento finale
                    # <!-- TV2000 --> alla fine della linea
                    name_match = re.search(r'<!--\s*(.+?)\s*-->$', line)
                    channel_name = name_match.group(1) if name_match else channel_id
                    
                    # Salva
                    xml_mappings[src_png]['name'] = channel_name
                    if current_satellite:
                        xml_mappings[src_png]['satellites'].add(current_satellite)
        
        # Converti satelliti in stringa
        for src in xml_mappings:
            if xml_mappings[src]['satellites']:
                # Rimuovi duplicati e ordina
                sats = sorted(set(xml_mappings[src]['satellites']))
                xml_mappings[src]['satellites_str'] = '|'.join(sats)
            else:
                xml_mappings[src]['satellites_str'] = ''
        
        print(f"Parsed {len(xml_mappings)} SRC entries from XML")
        
        # Debug: mostra alcuni esempi trovati
        print("\nSample matches found in XML:")
        sample_keys = list(xml_mappings.keys())[:5]
        for key in sample_keys:
            print(f"  {key} -> '{xml_mappings[key]['name']}' - {xml_mappings[key]['satellites_str']}")
        
        return dict(xml_mappings)
        
    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}

def generate_mapping():
    print("=" * 80)
    print("SRC MAPPING GENERATOR - FINAL WORKING VERSION")
    print("=" * 80)
    
    # 1. Get PNG files
    png_files = get_png_files()
    
    if not png_files:
        print("ERROR: No PNG files found!")
        return
    
    # 2. Parse XML correctly
    xml_data = parse_xml_correctly()
    
    if not xml_data:
        print("ERROR: No XML data parsed!")
        return
    
    print(f"\nUnique PNG files: {len(png_files)}")
    print(f"Unique XML entries: {len(xml_data)}")
    
    # 3. Process PNG files
    png_srcs = {}
    for png_file in png_files:
        src_from_png = png_file.replace('.png', '')
        png_srcs[src_from_png] = png_srcs.get(src_from_png, 0) + 1
    
    print(f"Unique PNG SRCs: {len(png_srcs)}")
    
    # 4. Generate mapping
    results = []
    not_found_list = []
    found_count = 0
    
    print(f"\nGenerating mapping...")
    
    for src_from_png in sorted(png_srcs.keys()):
        dup_count = png_srcs[src_from_png]
        
        if src_from_png in xml_data:
            info = xml_data[src_from_png]
            
            # Costruisci la linea nel formato richiesto
            satellites = info['satellites_str'] if info['satellites_str'] else 'Satellite Unknown'
            line = f"{src_from_png} - {info['name']} - {satellites}"
            
            if dup_count > 1:
                line += f" (appears {dup_count} times)"
            
            results.append(line)
            found_count += 1
        else:
            # Non trovato
            line = f"{src_from_png} - CHANNEL NOT FOUND IN XML - SATELLITE UNKNOWN"
            if dup_count > 1:
                line += f" (appears {dup_count} times)"
            
            results.append(line)
            not_found_list.append(src_from_png)
    
    # 5. Scrivi file principale
    print(f"\nWriting src_mapping.txt...")
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - Channel Name - Satellite Positions\n")
        f.write("# Generated automatically - CORRECT FORMAT\n")
        f.write(f"# Unique PNG SRCs: {len(png_srcs)}\n")
        f.write(f"# Found in XML: {found_count}\n")
        f.write(f"# Not found in XML: {len(not_found_list)}\n")
        f.write("# Format: 1_0_19_64_200_1D_EEEE0000_0_0_0 - TV2000 - DVB-T\n\n")
        
        for line in results:
            f.write(line + "\n")
    
    # 6. Scrivi file not found
    print(f"Writing not_found_src.txt...")
    with open('not_found_src.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC codes not found in XML\n")
        f.write(f"# Total: {len(not_found_list)}\n")
        f.write("# These PNG SRCs do not exist in the XML file\n\n")
        
        for src in sorted(not_found_list):
            f.write(f"{src}\n")
    
    # 7. Statistiche finali
    print("\n" + "=" * 80)
    print("FINAL RESULTS:")
    print(f"Total unique PNG SRCs: {len(png_srcs)}")
    print(f"Found in XML: {found_count} ({found_count/len(png_srcs)*100:.1f}%)")
    print(f"Not found: {len(not_found_list)} ({len(not_found_list)/len(png_srcs)*100:.1f}%)")
    
    if found_count > 0:
        print(f"\nSample of found channels:")
        found_samples = [r for r in results if 'NOT FOUND' not in r][:3]
        for sample in found_samples:
            print(f"  {sample}")
    
    if not_found_list:
        print(f"\nSample of not found SRCs (first 5):")
        for src in not_found_list[:5]:
            print(f"  {src}")
    
    print(f"\nFiles created:")
    print(f"  - src_mapping.txt ({len(results)} entries)")
    print(f"  - not_found_src.txt ({len(not_found_list)} entries)")

if __name__ == "__main__":
    generate_mapping()
