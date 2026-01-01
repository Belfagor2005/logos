# -*- coding: utf-8 -*-
# generate_src_mapping_final_fixed.py
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

def parse_xml_perfectly():
    """Parse XML PERFECTLY with correct regex"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    
    try:
        response = requests.get(xml_url, timeout=60)
        xml_data = response.text
        
        xml_mappings = defaultdict(lambda: {'name': '', 'satellites': set()})
        current_satellite = ""
        
        lines = xml_data.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 1. Cerca satellite/posizione nei commenti PRIMA del channel
            if line.startswith('<!--') and '-->' in line and not '<channel' in line:
                comment = line[4:-3].strip()  # Rimuove <!-- e -->
                current_satellite = comment
            
            # 2. Cerca canale - pattern CORRETTO!
            elif '<channel id="' in line:
                # Pattern per estrarre SRC: >1:0:19:64:200:1D:EEEE0000:0:0:0:<
                # Deve essere PRECISO!
                src_match = re.search(r'>([0-9]:[0-9]:[0-9A-F]+:[0-9A-F]+:[0-9A-F]+:[0-9A-F]+:[0-9A-F]+:[0-9]:[0-9]:[0-9]:)<', line)
                
                if src_match:
                    src_xml = src_match.group(1)
                    
                    # Converti a PNG
                    src_png = src_xml.rstrip(':').replace(':', '_')
                    
                    # Estrai nome canale - CORRETTO!
                    # Cerca <!-- Nome Canale --> alla FINE della linea
                    name_match = re.search(r'<!--\s*([^<]+?)\s*-->$', line)
                    
                    if name_match:
                        channel_name = name_match.group(1).strip()
                    else:
                        # Se non trova alla fine, cerca nell'ID
                        id_match = re.search(r'id="([^"]+)"', line)
                        channel_name = id_match.group(1) if id_match else "Unknown"
                    
                    # Salva
                    xml_mappings[src_png]['name'] = channel_name
                    if current_satellite:
                        xml_mappings[src_png]['satellites'].add(current_satellite)
        
        # Converti satelliti in stringa
        for src in xml_mappings:
            if xml_mappings[src]['satellites']:
                sats = sorted(set(xml_mappings[src]['satellites']))
                xml_mappings[src]['satellites_str'] = '|'.join(sats)
            else:
                xml_mappings[src]['satellites_str'] = ''
        
        print(f"Parsed {len(xml_mappings)} SRC entries from XML")
        
        # Debug: mostra esempi CORRETTI
        print("\nCORRECT sample matches from XML:")
        count = 0
        for src, info in xml_mappings.items():
            if 'EEEE0000' in src and count < 3:
                print(f"  {src} -> '{info['name']}' - {info['satellites_str']}")
                count += 1
        
        return dict(xml_mappings)
        
    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}

def generate_mapping():
    print("=" * 80)
    print("SRC MAPPING - FINAL FIXED VERSION")
    print("=" * 80)
    
    # 1. Get PNG files
    png_files = get_png_files()
    
    if not png_files:
        print("ERROR: No PNG files found!")
        return
    
    # 2. Parse XML perfectly
    xml_data = parse_xml_perfectly()
    
    if not xml_data:
        print("ERROR: No XML data parsed!")
        return
    
    # 3. Process PNG files
    png_srcs = {}
    for png_file in png_files:
        src_from_png = png_file.replace('.png', '')
        png_srcs[src_from_png] = png_srcs.get(src_from_png, 0) + 1
    
    print(f"\nUnique PNG SRCs: {len(png_srcs)}")
    print(f"Unique XML entries: {len(xml_data)}")
    
    # 4. Generate mapping
    results = []
    not_found_list = []
    found_count = 0
    
    print(f"\nGenerating mapping...")
    
    for src_from_png in sorted(png_srcs.keys()):
        dup_count = png_srcs[src_from_png]
        
        if src_from_png in xml_data:
            info = xml_data[src_from_png]
            
            # Costruisci la linea
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
    
    # 5. Scrivi file
    print(f"\nWriting files...")
    
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - Channel Name - Satellite Positions\n")
        f.write("# Generated automatically - FINAL FIXED VERSION\n")
        f.write(f"# Unique PNG SRCs: {len(png_srcs)}\n")
        f.write(f"# Found in XML: {found_count} ({found_count/len(png_srcs)*100:.1f}%)\n")
        f.write(f"# Not found in XML: {len(not_found_list)} ({len(not_found_list)/len(png_srcs)*100:.1f}%)\n\n")
        
        for line in results:
            f.write(line + "\n")
    
    with open('not_found_src.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC codes not found in XML\n")
        f.write(f"# Total: {len(not_found_list)}\n\n")
        
        for src in sorted(not_found_list):
            f.write(f"{src}\n")
    
    # 6. Statistiche e debug
    print("\n" + "=" * 80)
    print("RESULTS:")
    print(f"Found: {found_count}/{len(png_srcs)} ({found_count/len(png_srcs)*100:.1f}%)")
    print(f"Not found: {len(not_found_list)}/{len(png_srcs)} ({len(not_found_list)/len(png_srcs)*100:.1f}%)")
    
    # Debug: cerca alcuni SRC specifici
    print(f"\nDebug - searching for specific SRC patterns:")
    
    # Cerca SRC con EEEE0000 (canali italiani)
    eeee_srcs = [s for s in png_srcs if 'EEEE0000' in s]
    print(f"PNG SRCs with EEEE0000: {len(eeee_srcs)}")
    
    # Verifica se alcuni esistono nell'XML
    test_srcs = eeee_srcs[:5]
    print(f"\nChecking first 5 EEEE0000 SRCs in XML:")
    for src in test_srcs:
        if src in xml_data:
            print(f"  ✓ {src} -> '{xml_data[src]['name']}'")
        else:
            print(f"  ✗ {src} NOT FOUND")
    
    print(f"\nFiles created:")
    print(f"  src_mapping.txt")
    print(f"  not_found_src.txt")

if __name__ == "__main__":
    generate_mapping()

if __name__ == "__main__":
    generate_mapping()
