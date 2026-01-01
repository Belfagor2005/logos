# -*- coding: utf-8 -*-
# generate_src_simple_final.py
import requests
import re

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

def extract_src_from_path(path):
    """Extract SRC from PNG path"""
    # Esempio: logos/E2LIST/1.9E/1_0_1_67_E_3_130000_0_0_0.png
    # Estrae: 1_0_1_67_E_3_130000_0_0_0
    
    # Prendi solo il nome del file
    filename = path.split('/')[-1]
    
    # Rimuovi .png
    if filename.endswith('.png'):
        return filename[:-4]  # Rimuove ".png"
    
    return filename

def parse_xml_for_src():
    """Parse XML and create dictionary of SRC -> (channel_name, satellite)"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    
    try:
        response = requests.get(xml_url, timeout=60)
        xml_data = response.text
        
        # Dizionario: SRC_PNG -> (channel_name, satellite)
        xml_dict = {}
        current_satellite = ""
        
        lines = xml_data.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Cerca satellite nei commenti
            if line.startswith('<!--') and '-->' in line and not '<channel' in line:
                sat_match = re.search(r'<!--\s*([^>]+)\s*-->', line)
                if sat_match:
                    current_satellite = sat_match.group(1).strip()
            
            # Cerca channel
            elif '<channel id="' in line and '>' in line:
                # Estrai ID canale
                id_match = re.search(r'id="([^"]+)"', line)
                if id_match:
                    channel_id = id_match.group(1)
                    
                    # Estrai SRC
                    src_match = re.search(r'>([0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9]+:[0-9]+:[0-9]+:)<', line, re.IGNORECASE)
                    
                    if src_match:
                        src_xml = src_match.group(1)
                        # Converti a PNG format
                        src_png = src_xml.rstrip(':').replace(':', '_')
                        
                        # Estrai nome canale
                        name_match = re.search(r'<!--\s*([^<]+)\s*-->$', line)
                        channel_name = name_match.group(1).strip() if name_match else channel_id
                        
                        # Salva nel dizionario
                        xml_dict[src_png] = (channel_name, current_satellite)
        
        print(f"Parsed {len(xml_dict)} SRC entries from XML")
        return xml_dict
        
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return {}

def create_snp_code(channel_name):
    """Create simple SNP code from channel name"""
    if not channel_name:
        return "UNKN"
    
    # Rimuovi caratteri speciali, prendi prime 4 lettere
    clean = re.sub(r'[^a-zA-Z0-9]', '', channel_name)
    
    if not clean:
        return "CHNL"
    
    return clean[:4].upper()

def generate_simple_mapping():
    print("=" * 80)
    print("SIMPLE SRC MAPPING")
    print("=" * 80)
    
    # 1. Get PNG paths
    print("Getting PNG paths from logos.txt...")
    png_paths = get_png_paths()
    
    if not png_paths:
        print("No PNG paths found!")
        return
    
    # 2. Parse XML
    print("Parsing XML...")
    xml_dict = parse_xml_for_src()
    
    if not xml_dict:
        print("No XML data!")
        return
    
    # 3. Extract SRCs from paths
    print("Processing PNG files...")
    png_srcs = {}
    
    for path in png_paths:
        src = extract_src_from_path(path)
        png_srcs[src] = png_srcs.get(src, 0) + 1
    
    print(f"Unique PNG SRCs: {len(png_srcs)}")
    
    # 4. Generate mapping
    print("Generating mapping...")
    
    found_results = []
    not_found_list = []
    
    for src in sorted(png_srcs.keys()):
        dup_count = png_srcs[src]
        
        if src in xml_dict:
            # TROVATO nel XML
            channel_name, satellite = xml_dict[src]
            snp_code = create_snp_code(channel_name)
            
            if not satellite:
                satellite = "Satellite Unknown"
            
            line = f"{src} - {snp_code} - {satellite}"
            if dup_count > 1:
                line += f" (appears {dup_count} times)"
            
            found_results.append(line)
        else:
            # NON TROVATO
            not_found_list.append(src)
    
    # 5. Write files
    print("\nWriting files...")
    
    # File con i match trovati
    with open('src_mapping_found.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - SNP - Satellite Positions\n")
        f.write("# Only SRCs found in XML\n")
        f.write(f"# Total PNG SRCs: {len(png_srcs)}\n")
        f.write(f"# Found in XML: {len(found_results)}\n")
        f.write("# Generated from logos.txt and rytec.channels.xml\n\n")
        
        for line in sorted(found_results):
            f.write(line + "\n")
    
    # File con quelli non trovati
    with open('src_not_found.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC codes NOT found in XML\n")
        f.write(f"# Total: {len(not_found_list)}\n")
        f.write("# These need to be added to the XML\n\n")
        
        for src in sorted(not_found_list):
            f.write(src + "\n")
    
    # 6. Statistics
    print("\n" + "=" * 80)
    print("RESULTS:")
    print(f"Total PNG SRCs from logos.txt: {len(png_srcs)}")
    print(f"Found in XML: {len(found_results)} ({len(found_results)/len(png_srcs)*100:.1f}%)")
    print(f"Not found in XML: {len(not_found_list)} ({len(not_found_list)/len(png_srcs)*100:.1f}%)")
    
    if found_results:
        print(f"\nSample of found SRCs (first 3):")
        for line in found_results[:3]:
            print(f"  {line}")
    
    if not_found_list:
        print(f"\nSample of not found SRCs (first 3):")
        for src in not_found_list[:3]:
            print(f"  {src}")
    
    print(f"\nFiles created:")
    print(f"  src_mapping_found.txt - SRCs found in XML")
    print(f"  src_not_found.txt - SRCs NOT found in XML")

if __name__ == "__main__":
    generate_simple_mapping()
