# -*- coding: utf-8 -*-
# generate_src_mapping.py
import requests
import re

def get_png_files():
    """Get PNG files from SRF folder"""
    url = "https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF"
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'SRC-Mapping-Generator'
    }
    
    all_files = []
    page = 1
    
    # GitHub API returns max 1000 files, we need to paginate
    while True:
        api_url = f"{url}?page={page}"
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            break
            
        data = response.json()
        if not data:
            break
            
        for item in data:
            if isinstance(item, dict):
                filename = item.get('name', '')
                if filename.endswith('.png'):
                    all_files.append(filename)
        
        # If we got less than 1000 items, we're done
        if len(data) < 1000:
            break
            
        page += 1
    
    print(f"Found {len(all_files)} total PNG files")
    return all_files

def parse_xml():
    """Parse XML and create dictionary of SRC -> (channel_name, satellite)"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    
    try:
        response = requests.get(xml_url)
        xml_data = response.text
        
        xml_mappings = {}
        current_satellite = ""
        
        print(f"XML size: {len(xml_data)} characters")
        
        lines = xml_data.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Get satellite position from comment
            if line.startswith('<!--') and '-->' in line and not '<channel' in line:
                sat_match = re.search(r'<!--\s*([0-9.]+[EW])\s*-->', line)
                if sat_match:
                    current_satellite = sat_match.group(1)
            
            # Get channel entry
            elif '<channel id="' in line and '>' in line:
                # Extract channel ID (name)
                id_match = re.search(r'<channel id="([^"]+)"', line)
                if id_match:
                    channel_id = id_match.group(1)
                    
                    # Extract SRC code
                    # Look for pattern like 1:0:19:460:526C:16E:A00000:0:0:0:
                    src_match = re.search(r'>([0-9:ABCDEF_]+:)<', line)
                    if src_match:
                        src_code_full = src_match.group(1)
                        
                        # Convert to PNG format
                        # Remove trailing : and replace : with _
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
        
    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}

def generate_mapping():
    print("Starting SRC mapping generation...")
    print("=" * 50)
    
    # 1. Get PNG files
    print("\n1. Getting PNG files from GitHub...")
    png_files = get_png_files()
    
    if len(png_files) == 0:
        print("ERROR: No PNG files found!")
        return
    
    print(f"Found {len(png_files)} PNG files")
    
    # 2. Parse XML
    print("\n2. Parsing XML file...")
    xml_data = parse_xml()
    print(f"Found {len(xml_data)} channel entries in XML")
    
    if len(xml_data) == 0:
        print("ERROR: No XML data parsed!")
        return
    
    # 3. Generate output
    print("\n3. Generating mapping...")
    results = []
    not_found_list = []
    found_count = 0
    
    for png_file in sorted(png_files):
        # Remove .png extension to get SRC
        src_from_png = png_file.replace('.png', '')
        
        if src_from_png in xml_data:
            info = xml_data[src_from_png]
            results.append(f"{src_from_png} - {info['name']} - {info['satellite']}")
            found_count += 1
        else:
            not_found_list.append(src_from_png)
            results.append(f"{src_from_png} - CHANNEL NOT FOUND IN XML - SATELLITE UNKNOWN")
    
    # 4. Write main mapping file
    print("\n4. Writing files...")
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - Channel Name - Satellite Position\n")
        f.write("# Generated automatically\n")
        f.write(f"# PNG files: {len(png_files)}, Found in XML: {found_count}, Not found: {len(not_found_list)}\n\n")
        
        for line in results:
            f.write(line + "\n")
    
    # 5. Write not found file
    with open('not_found_src.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC codes not found in XML\n")
        f.write(f"# Total: {len(not_found_list)}\n")
        f.write(f"# Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for src in sorted(not_found_list):
            f.write(src + "\n")
    
    # 6. Statistics
    print("=" * 50)
    print("\nSTATISTICS:")
    print(f"Total PNG files: {len(png_files)}")
    print(f"Found in XML: {found_count}")
    print(f"Not found in XML: {len(not_found_list)}")
    print(f"Percentage found: {(found_count/len(png_files)*100):.1f}%" if len(png_files) > 0 else "N/A")
    
    if not_found_list:
        print(f"\nSample of SRC codes not found in XML (first 10):")
        for src in not_found_list[:10]:
            print(f"  {src}")
    
    print("\nFiles created:")
    print("  - src_mapping.txt (main mapping file)")
    print("  - not_found_src.txt (SRC codes not found in XML)")

if __name__ == "__main__":
    generate_mapping()
