# -*- coding: utf-8 -*-
# generate_final_mapping.py
import requests
import re
import time


def get_png_paths():
    """Get all PNG paths from txt/logos.txt"""
    txt_url = "https://raw.githubusercontent.com/Belfagor2005/logos/refs/heads/main/txt/logos.txt"

    try:
        response = requests.get(txt_url, timeout=30)
        lines = response.text.strip().split('\n')

        png_paths = []
        for line in lines:
            if line.strip().endswith('.png') and 'E2LIST' in line:
                png_paths.append(line.strip())

        print("Found " + str(len(png_paths)) + " PNG paths")
        return png_paths

    except Exception as e:
        print("Error: " + str(e))
        return []


def extract_src_and_satellite_from_path(path):
    """Extract SRC and satellite position from PNG path"""
    parts = path.split('/')
    
    satellite = ""
    if len(parts) >= 3:
        for part in parts:
            if re.search(r'\d+\.\d+[EW]', part):
                satellite = part
                break
    
    filename = parts[-1]
    if filename.endswith('.png'):
        src = filename[:-4]
    else:
        src = filename
    
    return src, satellite


def parse_xml():
    """Parse rytec.channels.xml"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"

    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text

        print("XML size: " + str(len(content)) + " bytes")
        
        src_to_info = {}
        
        # Simple regex for XML parsing
        pattern = r'<!--\s*(.*?)\s*-->\s*<channel id="(.*?)">(.*?)</channel>\s*(?:<!--\s*(.*?)\s*-->)?'
        matches = re.findall(pattern, content, re.DOTALL)
        
        print("Found " + str(len(matches)) + " channel entries")
        
        for before_comment, channel_id, service_ref, after_comment in matches:
            # Clean up
            before_comment = before_comment.strip()
            after_comment = after_comment.strip() if after_comment else ""
            service_ref = service_ref.strip().rstrip(':')
            
            # Extract satellite
            satellite = ""
            sat_match = re.search(r'(\d+\.\d+[EW])', before_comment)
            if sat_match:
                satellite = sat_match.group(1)
            
            # Get channel name
            if after_comment:
                channel_name = after_comment
            else:
                channel_name = channel_id
            
            # Convert to PNG format
            src_png = service_ref.replace(':', '_')
            
            src_to_info[src_png] = {
                'name': channel_name,
                'satellite': satellite,
                'id': channel_id
            }
        
        print("Parsed " + str(len(src_to_info)) + " unique SRCs")
        return src_to_info

    except Exception as e:
        print("Error parsing XML: " + str(e))
        return {}


def create_snp(channel_name):
    """Create SNP code from channel name"""
    if not channel_name or channel_name.lower() in ['unknown', 'no_epg', '']:
        return "UNKN"
    
    clean = re.sub(r'\b(?:HD|FHD|UHD|4K|SD|HEVC|TV|CHANNEL)\b', '', channel_name, flags=re.IGNORECASE)
    clean = re.sub(r'[^a-zA-Z0-9]', '', clean)
    
    if len(clean) >= 4:
        return clean[:4].upper()
    elif clean:
        return clean.upper().ljust(4, 'X')
    
    return "CHNL"


def generate_final_mapping():
    print("=" * 80)
    print("GENERATING FINAL MAPPING")
    print("=" * 80)
    
    start_time = time.time()

    # 1. Get PNG paths
    print("Getting PNG paths...")
    png_paths = get_png_paths()

    if not png_paths:
        print("No PNG paths!")
        return

    # 2. Parse XML
    print("\nParsing XML...")
    xml_data = parse_xml()

    # 3. Process PNGs
    print("\nProcessing PNGs...")
    png_srcs = {}
    
    for path in png_paths:
        src, sat = extract_src_and_satellite_from_path(path)
        if src and sat:
            if src not in png_srcs:
                png_srcs[src] = set()
            png_srcs[src].add(sat)
    
    print("Found " + str(len(png_srcs)) + " PNG SRCs")
    
    # 4. Generate mapping
    print("\nGenerating files...")
    
    mapping_lines = []
    missing_picons = []
    
    known = 0
    unknown = 0
    
    for src in sorted(png_srcs.keys()):
        sats = png_srcs[src]
        
        if src in xml_data:
            info = xml_data[src]
            snp = create_snp(info['name'])
            known += 1
            
            # Add XML satellite if available
            if info['satellite']:
                sats.add(info['satellite'])
        else:
            snp = "UNKN"
            unknown += 1
        
        # Format satellites
        if sats:
            def sort_key(s):
                m = re.match(r'(\d+\.?\d*)([EW])', s)
                if m:
                    n = float(m.group(1))
                    return -n if m.group(2) == 'W' else n
                return 999
            
            sorted_sats = sorted(sats, key=sort_key)
            sats_str = '|'.join(sorted_sats)
        else:
            sats_str = 'Unknown'
        
        mapping_lines.append(src + " - " + snp + " - " + sats_str)
    
    # Find missing picons
    for src, info in xml_data.items():
        if src not in png_srcs:
            missing_picons.append({
                'src': src,
                'name': info['name'],
                'satellite': info['satellite']
            })
    
    # 5. Write files
    print("\nWriting files...")
    
    # File 1: src_mapping.txt
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - SNP - Satellites\n")
        f.write("# Total: " + str(len(mapping_lines)) + "\n")
        f.write("# Known: " + str(known) + "\n")
        f.write("# Unknown: " + str(unknown) + "\n")
        
        if png_srcs:
            coverage = (known / len(png_srcs)) * 100
            f.write("# Coverage: " + str(round(coverage, 1)) + "%\n")
        
        f.write("# Date: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
        
        for line in mapping_lines:
            f.write(line + "\n")
    
    # File 2: missing_picons.txt (THE IMPORTANT ONE!)
    with open('missing_picons.txt', 'w', encoding='utf-8') as f:
        f.write("# MISSING PICONS\n")
        f.write("# ===============\n")
        f.write("# Total: " + str(len(missing_picons)) + "\n")
        f.write("# Date: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
        f.write("# These need PNG files\n\n")
        
        # Sort by name
        missing_sorted = sorted(missing_picons, key=lambda x: x['name'])
        
        for item in missing_sorted:
            f.write("SRC: " + item['src'] + "\n")
            f.write("NAME: " + item['name'] + "\n")
            f.write("SAT: " + (item['satellite'] if item['satellite'] else 'Unknown') + "\n")
            f.write("PNG: " + item['src'] + ".png\n")
            f.write("---\n")
    
    # 6. Final output
    print("\n" + "=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    
    print("Time: " + str(round(time.time() - start_time, 1)) + "s")
    print("PNG SRCs: " + str(len(png_srcs)))
    print("Known: " + str(known) + " (" + str(round(known/len(png_srcs)*100, 1)) + "%)")
    print("Unknown: " + str(unknown) + " (" + str(round(unknown/len(png_srcs)*100, 1)) + "%)")
    print("Missing picons: " + str(len(missing_picons)))
    
    print("\nFiles created:")
    print("  1. src_mapping.txt")
    print("  2. missing_picons.txt")
    
    if missing_picons:
        print("\nNEXT: Create " + str(len(missing_picons)) + " PNG files")
        print("      Check missing_picons.txt for list")


if __name__ == "__main__":
    generate_final_mapping()
