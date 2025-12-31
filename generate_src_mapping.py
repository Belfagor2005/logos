# -*- coding: utf-8 -*-
# generate_src_mapping.py
import requests
import re
from collections import defaultdict

def get_png_files():
    """Get PNG files from SRF folder"""
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

def parse_xml_complete():
    """Parse ALL channels from XML file"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    
    try:
        response = requests.get(xml_url, timeout=60)
        xml_data = response.text
        
        xml_mappings = defaultdict(lambda: {'name': '', 'satellites': set()})
        current_satellite = ""
        line_count = 0
        channel_count = 0
        
        lines = xml_data.split('\n')
        total_lines = len(lines)
        
        print(f"XML has {total_lines} lines")
        
        for line in lines:
            line_count += 1
            if line_count % 5000 == 0:
                print(f"  Processing line {line_count}/{total_lines}...")
            
            line = line.strip()
            
            # Get satellite position
            if line.startswith('<!--') and '-->' in line and not '<channel' in line:
                # Cerca qualsiasi posizione satellitare
                sat_match = re.search(r'<!--\s*([^>]*[0-9.,]+[EW][^>]*)\s*-->', line)
                if sat_match:
                    current_satellite = sat_match.group(1).strip()
            
            # Get channel entry
            elif '<channel id="' in line and '>' in line:
                channel_count += 1
                
                # Extract channel ID
                id_match = re.search(r'<channel id="([^"]+)"', line)
                if id_match:
                    channel_id = id_match.group(1)
                    
                    # Extract SRC - cerca QUALSIASI pattern di SRC
                    # Formato generale: numeri/lettere separati da :
                    src_match = re.search(r'>([\dA-F_:]+:)<', line)
                    if src_match:
                        src_code_full = src_match.group(1)
                        
                        # Clean and convert to PNG format
                        src_code_full = src_code_full.strip()
                        if src_code_full.endswith(':'):
                            src_code_full = src_code_full[:-1]
                        
                        # Convert to PNG format: replace : with _
                        src_for_png = src_code_full.replace(':', '_')
                        
                        # Get channel name from comment
                        name_match = re.search(r'<!--\s*(.+?)\s*-->', line)
                        channel_name = name_match.group(1) if name_match else channel_id
                        
                        # Store in dictionary
                        xml_mappings[src_for_png]['name'] = channel_name
                        if current_satellite:
                            xml_mappings[src_for_png]['satellites'].add(current_satellite)
        
        # Convert sets to strings
        for src in xml_mappings:
            if xml_mappings[src]['satellites']:
                sorted_sats = sorted(xml_mappings[src]['satellites'])
                xml_mappings[src]['satellites_str'] = '|'.join(sorted_sats)
            else:
                xml_mappings[src]['satellites_str'] = 'Satellite Unknown'
        
        print(f"\nParsed {channel_count} channel entries from XML")
        print(f"Unique SRCs in XML: {len(xml_mappings)}")
        
        # Show statistics about different systems
        print("\nProvider ID analysis in XML:")
        provider_stats = defaultdict(int)
        for src in xml_mappings:
            parts = src.split('_')
            if len(parts) >= 7:
                provider_id = parts[6]  # Campo 7: namespace esteso
                provider_stats[provider_id] += 1
        
        print("Top provider IDs in XML:")
        for provider, count in sorted(provider_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {provider}: {count} channels")
        
        return dict(xml_mappings)
        
    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}

def generate_mapping():
    print("=" * 70)
    print("COMPLETE SRC MAPPING GENERATOR")
    print("=" * 70)
    
    # 1. Get PNG files
    png_files = get_png_files()
    
    if not png_files:
        print("ERROR: No PNG files found!")
        return
    
    # 2. Parse XML - TUTTI i canali
    xml_data = parse_xml_complete()
    
    if not xml_data:
        print("ERROR: No XML data parsed!")
        return
    
    print("\n" + "=" * 70)
    print("GENERATING MAPPING...")
    
    # 3. Analyze PNG SRCs
    png_srcs = {}
    provider_stats_png = defaultdict(int)
    
    for png_file in png_files:
        src_from_png = png_file.replace('.png', '')
        png_srcs[src_from_png] = png_srcs.get(src_from_png, 0) + 1
        
        # Analyze provider ID
        parts = src_from_png.split('_')
        if len(parts) >= 7:
            provider_id = parts[6]  # Campo 7
            provider_stats_png[provider_id] += 1
    
    print(f"Unique PNG SRC codes: {len(png_srcs)}")
    print(f"Total PNG files (with duplicates): {len(png_files)}")
    
    print("\nProvider ID analysis in PNG files:")
    for provider, count in sorted(provider_stats_png.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {provider}: {count} channels")
    
    # 4. Generate output
    results = []
    not_found_list = []
    found_count = 0
    
    print(f"\nStarting matching process...")
    
    for src_from_png in sorted(png_srcs.keys()):
        # Try exact match first
        if src_from_png in xml_data:
            info = xml_data[src_from_png]
            dup_count = png_srcs[src_from_png]
            if dup_count > 1:
                results.append(f"{src_from_png} - {info['name']} - {info['satellites_str']} (appears {dup_count} times)")
            else:
                results.append(f"{src_from_png} - {info['name']} - {info['satellites_str']}")
            found_count += 1
        else:
            not_found_list.append(src_from_png)
            dup_count = png_srcs[src_from_png]
            if dup_count > 1:
                results.append(f"{src_from_png} - CHANNEL NOT FOUND IN XML - SATELLITE UNKNOWN (appears {dup_count} times)")
            else:
                results.append(f"{src_from_png} - CHANNEL NOT FOUND IN XML - SATELLITE UNKNOWN")
    
    # 5. Write main file
    print(f"\nWriting files...")
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - Channel Name - Satellite Positions\n")
        f.write("# Generated automatically from ALL XML channels\n")
        f.write(f"# Unique PNG SRCs: {len(png_srcs)}\n")
        f.write(f"# Found in XML: {found_count}\n")
        f.write(f"# Not found in XML: {len(not_found_list)}\n")
        f.write("# XML contains channels from multiple satellite systems\n")
        f.write("# PNG files may be from different system than XML\n\n")
        
        for line in results:
            f.write(line + "\n")
    
    # 6. Write not found file with analysis
    with open('not_found_src.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC codes not found in XML\n")
        f.write(f"# Total unique SRCs not found: {len(not_found_list)}\n")
        f.write("# Analysis of not found SRCs:\n")
        
        # Analyze not found SRCs by provider
        not_found_stats = defaultdict(int)
        for src in not_found_list:
            parts = src.split('_')
            if len(parts) >= 7:
                provider = parts[6]  # Campo 7
                not_found_stats[provider] += 1
        
        f.write("# By provider ID:\n")
        for provider, count in sorted(not_found_stats.items(), key=lambda x: x[1], reverse=True):
            f.write(f"#   {provider}: {count} SRCs\n")
        
        f.write(f"\n# Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for src in sorted(not_found_list):
            dup_count = png_srcs[src]
            if dup_count > 1:
                f.write(f"{src} (appears {dup_count} times)\n")
            else:
                f.write(f"{src}\n")
    
    # 7. Statistics
    print("\n" + "=" * 70)
    print("FINAL RESULTS:")
    print(f"Unique PNG SRCs: {len(png_srcs)}")
    print(f"Found in XML: {found_count} ({found_count/len(png_srcs)*100:.1f}%)")
    print(f"Not found: {len(not_found_list)} ({len(not_found_list)/len(png_srcs)*100:.1f}%)")
    
    if found_count == 0:
        print("\nCRITICAL: No matches found!")
        print("This means PNG SRCs and XML SRCs are from COMPLETELY DIFFERENT SYSTEMS.")
        print("Possible reasons:")
        print("  1. PNG files are for Sky Italia/Mediaset DVB-T")
        print("  2. XML contains satellite channels (Hotbird, Astra, etc.)")
        print("  3. Different namespace/orbital positions")
    
    if not_found_list:
        print(f"\nFirst 3 not found SRCs with analysis:")
        for src in not_found_list[:3]:
            parts = src.split('_')
            print(f"\n  {src}")
            print(f"    Parts: {len(parts)}")
            if len(parts) >= 7:
                print(f"    Provider ID (field 7): {parts[6]}")
                print(f"    ONID (field 5): {parts[4] if len(parts) > 4 else 'N/A'}")
                print(f"    Namespace (field 6): {parts[5] if len(parts) > 5 else 'N/A'}")
    
    print(f"\nFiles created:")
    print(f"  - src_mapping.txt ({len(results)} entries)")
    print(f"  - not_found_src.txt ({len(not_found_list)} unique SRCs)")

if __name__ == "__main__":
    generate_mapping()
