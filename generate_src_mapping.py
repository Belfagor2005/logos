# -*- coding: utf-8 -*-
# generate_src_mapping.py
import requests
import re

def get_png_files():
    """Get PNG files from SRF folder"""
    url = "https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF"
    response = requests.get(url, headers={'Accept': 'application/vnd.github.v3+json'})
    
    png_files = []
    for item in response.json():
        if isinstance(item, dict) and item.get('name', '').endswith('_small.png'):
            png_files.append(item['name'])
    
    return png_files

def parse_xml():
    """Parse XML and create dictionary of SRC -> (channel_name, satellite)"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    xml_data = requests.get(xml_url).text
    
    xml_mappings = {}
    current_satellite = ""
    
    lines = xml_data.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Get satellite position from comment
        if line.startswith('<!--') and '-->' in line:
            sat_match = re.search(r'<!--\s*([0-9.]+[EW])\s*-->', line)
            if sat_match:
                current_satellite = sat_match.group(1)
        
        # Get channel entry
        elif '<channel id="' in line:
            # Extract channel ID (name)
            id_match = re.search(r'<channel id="([^"]+)"', line)
            if id_match:
                channel_id = id_match.group(1)
                
                # Extract SRC code
                src_match = re.search(r'>([0-9A-F_:]+:)<', line)
                if src_match:
                    src_code_full = src_match.group(1)
                    
                    # Convert to PNG format
                    # 1:0:19:460:526C:16E:A00000:0:0:0: -> 1_0_19_460_526C_16E_A00000_0_0_0
                    src_for_png = src_code_full.rstrip(':').replace(':', '_')
                    
                    # Get channel name from comment
                    name_match = re.search(r'<!--\s*(.+?)\s*-->', line)
                    channel_name = name_match.group(1) if name_match else channel_id
                    
                    # Store in dictionary
                    xml_mappings[src_for_png] = {
                        'name': channel_name,
                        'satellite': current_satellite
                    }
    
    return xml_mappings

def generate_mapping():
    print("Starting SRC mapping generation...")
    
    # 1. Get PNG files
    print("Getting PNG files...")
    png_files = get_png_files()
    print(f"Found {len(png_files)} PNG files")
    
    # 2. Parse XML
    print("Parsing XML file...")
    xml_data = parse_xml()
    print(f"Found {len(xml_data)} channel entries in XML")
    
    # 3. Generate output
    results = []
    not_found_list = []
    
    for png_file in sorted(png_files):
        src_from_png = png_file.replace('_small.png', '')
        
        if src_from_png in xml_data:
            info = xml_data[src_from_png]
            results.append(f"{src_from_png} - {info['name']} - {info['satellite']}")
        else:
            not_found_list.append(src_from_png)
            # Still add to main file but mark as not found
            results.append(f"{src_from_png} - CHANNEL NOT FOUND IN XML - SATELLITE UNKNOWN")
    
    # 4. Write main mapping file
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - Channel Name - Satellite Position\n")
        f.write("# Generated automatically\n\n")
        
        for line in results:
            f.write(line + "\n")
    
    # 5. Write not found file
    with open('not_found_src.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC codes not found in XML\n")
        f.write(f"# Total: {len(not_found_list)}\n\n")
        
        for src in sorted(not_found_list):
            f.write(src + "\n")
    
    # 6. Statistics
    print(f"\nGenerated src_mapping.txt with {len(results)} entries")
    print(f"Generated not_found_src.txt with {len(not_found_list)} entries")
    
    if not_found_list:
        print(f"\nSRC codes not found in XML ({len(not_found_list)}):")
        for src in not_found_list[:20]:
            print(f"  {src}")
        if len(not_found_list) > 20:
            print(f"  ... and {len(not_found_list) - 20} more")

if __name__ == "__main__":
    generate_mapping()
