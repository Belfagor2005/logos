# -*- coding: utf-8 -*-
# generate_mapping_simple.py
import requests
import re
import time


def get_png_paths():
    """Get PNG paths from txt/logos.txt"""
    txt_url = "https://raw.githubusercontent.com/Belfagor2005/logos/refs/heads/main/txt/logos.txt"
    
    try:
        response = requests.get(txt_url, timeout=30)
        lines = response.text.strip().split('\n')
        
        png_paths = []
        for line in lines:
            line = line.strip()
            if line.endswith('.png') and 'E2LIST' in line:
                png_paths.append(line)
        
        print("Found " + str(len(png_paths)) + " PNG paths")
        return png_paths
        
    except Exception as e:
        print("Error: " + str(e))
        return []


def extract_from_path(path):
    """Extract SRC and satellite from path"""
    parts = path.split('/')
    
    sat = ""
    for part in parts:
        if re.search(r'\d+\.\d+[EW]', part):
            sat = part
            break
    
    filename = parts[-1]
    if filename.endswith('.png'):
        src = filename[:-4]
    else:
        src = filename
    
    return src, sat


def parse_xml():
    """Parse rytec.channels.xml"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    
    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text
        
        print("XML size: " + str(len(content)) + " bytes")
        
        channels = {}
        
        # Simple parsing
        lines = content.split('\n')
        current_sat = ""
        
        for line in lines:
            line = line.strip()
            
            # Get satellite
            if line.startswith('<!--') and '-->' in line and '<channel' not in line:
                sat_match = re.search(r'(\d+\.\d+[EW])', line)
                if sat_match:
                    current_sat = sat_match.group(1)
            
            # Get channel
            elif '<channel id="' in line:
                # Get SRC
                src_match = re.search(r'>([0-9A-Fa-f_:]+:?)<', line)
                if src_match:
                    src_xml = src_match.group(1).rstrip(':')
                    src_png = src_xml.replace(':', '_')
                    
                    # Get name
                    name_match = re.search(r'<!--\s*(.+?)\s*-->$', line)
                    if name_match:
                        name = name_match.group(1).strip()
                    else:
                        # Try to get from channel id
                        id_match = re.search(r'id="([^"]+)"', line)
                        name = id_match.group(1) if id_match else "Unknown"
                    
                    channels[src_png] = {
                        'name': name,
                        'sat': current_sat
                    }
        
        print("Parsed " + str(len(channels)) + " channels from XML")
        return channels
        
    except Exception as e:
        print("Error parsing XML: " + str(e))
        return {}


def make_snp(name):
    """Make SNP code from name"""
    if not name or name == "Unknown":
        return "UNKN"
    
    # Clean name
    clean = re.sub(r'[^a-zA-Z0-9]', '', name)
    
    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper() + 'X' * (4 - len(clean))
    
    return "CHNL"


def main():
    print("=" * 80)
    print("GENERATING MAPPING")
    print("=" * 80)
    
    start = time.time()
    
    # 1. Get PNGs
    print("1. Getting PNG paths...")
    paths = get_png_paths()
    
    if not paths:
        print("No paths found!")
        return
    
    # 2. Parse XML
    print("2. Parsing XML...")
    xml_channels = parse_xml()
    
    # 3. Process PNGs
    print("3. Processing PNGs...")
    png_data = {}
    
    for path in paths:
        src, sat = extract_from_path(path)
        if src and sat:
            if src not in png_data:
                png_data[src] = set()
            png_data[src].add(sat)
    
    print("Found " + str(len(png_data)) + " unique PNG SRCs")
    
    # 4. Create lists
    print("4. Creating lists...")
    
    mapping_lines = []
    missing_list = []
    
    known = 0
    unknown = 0
    
    for src in sorted(png_data.keys()):
        sats = png_data[src]
        
        if src in xml_channels:
            info = xml_channels[src]
            snp = make_snp(info['name'])
            known += 1
            
            # Add XML satellite
            if info['sat']:
                sats.add(info['sat'])
        else:
            snp = "UNKN"
            unknown += 1
        
        # Make satellites string
        if sats:
            def sort_sat(s):
                m = re.match(r'(\d+\.?\d*)([EW])', s)
                if m:
                    n = float(m.group(1))
                    return -n if m.group(2) == 'W' else n
                return 999
            
            sorted_sats = sorted(sats, key=sort_sat)
            sat_str = '|'.join(sorted_sats)
        else:
            sat_str = 'Unknown'
        
        mapping_lines.append(src + " - " + snp + " - " + sat_str)
    
    # 5. Find missing picons
    for src, info in xml_channels.items():
        if src not in png_data:
            missing_list.append({
                'src': src,
                'name': info['name'],
                'sat': info['sat'] or 'Unknown'
            })
    
    # 6. Write files
    print("5. Writing files...")
    
    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - SNP - Satellites\n")
        f.write("# Generated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
        f.write("# PNG SRCs: " + str(len(png_data)) + "\n")
        f.write("# Known: " + str(known) + "\n")
        f.write("# Unknown: " + str(unknown) + "\n")
        
        if png_data:
            percent = (known / len(png_data)) * 100
            f.write("# Coverage: " + str(round(percent, 1)) + "%\n")
        
        f.write("\n")
        
        for line in mapping_lines:
            f.write(line + "\n")
    
    print("  Created: src_mapping.txt")
    
    # File 2: missing_picons.txt
    with open('missing_picons.txt', 'w', encoding='utf-8') as f:
        f.write("# MISSING PICONS\n")
        f.write("# ===============\n")
        f.write("# Generated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
        f.write("# Total missing: " + str(len(missing_list)) + "\n")
        f.write("#\n")
        f.write("# Format:\n")
        f.write("# SRC: service_reference\n")
        f.write("# NAME: channel_name\n")
        f.write("# SAT: satellite_position\n")
        f.write("# PNG: filename.png\n")
        f.write("# ---\n")
        f.write("\n")
        
        if missing_list:
            # Sort by name
            missing_list.sort(key=lambda x: x['name'])
            
            for item in missing_list:
                f.write("SRC: " + item['src'] + "\n")
                f.write("NAME: " + item['name'] + "\n")
                f.write("SAT: " + item['sat'] + "\n")
                f.write("PNG: " + item['src'] + ".png\n")
                f.write("---\n")
        else:
            f.write("NO MISSING PICONS FOUND!\n")
    
    print("  Created: missing_picons.txt with " + str(len(missing_list)) + " entries")
    
    # File 3: stats.txt
    with open('stats.txt', 'w', encoding='utf-8') as f:
        f.write("# STATISTICS\n")
        f.write("# ==========\n")
        f.write("Date: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
        f.write("Time: " + str(round(time.time() - start, 1)) + " seconds\n\n")
        
        f.write("PNG SRCs: " + str(len(png_data)) + "\n")
        f.write("XML channels: " + str(len(xml_channels)) + "\n\n")
        
        f.write("Known matches: " + str(known) + "\n")
        f.write("Unknown SRCs: " + str(unknown) + "\n")
        f.write("Missing picons: " + str(len(missing_list)) + "\n\n")
        
        if png_data:
            percent = (known / len(png_data)) * 100
            f.write("Coverage: " + str(round(percent, 1)) + "%\n")
    
    print("  Created: stats.txt")
    
    # 7. Final output
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    
    print("Time: " + str(round(time.time() - start, 1)) + "s")
    print("PNG SRCs: " + str(len(png_data)))
    print("Known: " + str(known) + " (" + str(round(known/len(png_data)*100, 1)) + "%)")
    print("Unknown: " + str(unknown) + " (" + str(round(unknown/len(png_data)*100, 1)) + "%)")
    print("Missing: " + str(len(missing_list)))
    
    if missing_list:
        print("\nFirst 5 missing picons:")
        for i, item in enumerate(missing_list[:5]):
            print("  " + str(i+1) + ". " + item['src'][:40] + "... - " + item['name'])
    
    print("\nFiles created:")
    print("  1. src_mapping.txt")
    print("  2. missing_picons.txt")
    print("  3. stats.txt")


if __name__ == "__main__":
    main()
