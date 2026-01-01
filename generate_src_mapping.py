# -*- coding: utf-8 -*-
# generate_src_mapping_exact.py
import requests
import re
from collections import defaultdict

def get_png_files():
    """Get PNG files"""
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
        
        return png_files
        
    except Exception as e:
        print(f"Error getting PNG files: {e}")
        return []

def parse_rytec_xml_like_plugin():
    """Parse rytec.channels.xml EXACTLY like your plugin does"""
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    
    try:
        response = requests.get(xml_url, timeout=60)
        content = response.text
        
        print(f"XML size: {len(content)} bytes")
        
        # Questo è il pattern che usa il tuo plugin!
        pattern = r'(<!--\s*([^>]+)\s*-->)?\s*<channel id="([^"]+)">([^<]+)</channel>\s*(?:<!--\s*([^>]+)\s*-->)?'
        matches = re.findall(pattern, content)
        
        print(f"Found {len(matches)} channel entries in XML (like plugin)")
        
        # Dizionari come nel plugin
        rytec_basic = {}       # channel_id -> service_ref
        rytec_extended = defaultdict(list)  # channel_id -> [info dict]
        
        current_satellite = ""
        
        for match in matches:
            comment_before, source_info, channel_id, service_ref, comment_after = match
            
            # Gestisci commenti come nel plugin
            comment = comment_before or comment_after or ""
            
            # Estrai posizione satellitare dai commenti
            if comment:
                # Cerca coordinate satellitari
                sat_match = re.search(r'([0-9.,]+\s*[EW])', comment)
                if sat_match:
                    current_satellite = sat_match.group(1)
                elif any(x in comment.upper() for x in ['DVB', 'IPTV', 'MISC']):
                    current_satellite = comment
            
            # Normalizza il service_ref come fa il tuo plugin
            normalized_ref = normalize_service_ref(service_ref, for_epg=True)
            
            # Salva nei dizionari
            if channel_id not in rytec_basic:
                rytec_basic[channel_id] = normalized_ref
            
            rytec_extended[channel_id].append({
                'sref': normalized_ref,
                'comment': comment.strip(),
                'source_type': get_source_type(comment),
                'sat_position': current_satellite
            })
        
        print(f"Basic mapping: {len(rytec_basic)} entries")
        print(f"Extended mapping: {len(rytec_extended)} entries")
        
        return rytec_basic, rytec_extended
        
    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
        return {}, defaultdict(list)

def normalize_service_ref(service_ref, for_epg=False):
    """Normalize service reference like your plugin does"""
    if not service_ref or not isinstance(service_ref, str):
        return service_ref
    
    # Se è un riferimento IPTV, convertilo
    if service_ref.startswith('4097:'):
        parts = service_ref.split(':')
        if len(parts) < 11:
            parts += ['0'] * (11 - len(parts))
        
        service_type = parts[2]
        service_id = parts[3]
        ts_id = parts[4]
        on_id = parts[5]
        namespace = parts[6]
        
        return f"1:0:{service_type}:{service_id}:{ts_id}:{on_id}:{namespace}:0:0:0:"
    
    parts = service_ref.split(':')
    if len(parts) < 11:
        parts += ['0'] * (11 - len(parts))
    
    return ':'.join(parts)

def get_source_type(comment):
    """Get source type from comment"""
    if not comment:
        return "unknown"
    
    if 'DVB-T' in comment:
        return "dvb-t"
    elif 'IPTV' in comment:
        return "iptv"
    elif any(x in comment for x in ['E', 'W', '.']):  # Coordinate satellitari
        return "satellite"
    else:
        return "unknown"

def find_matching_src(png_src, rytec_basic, rytec_extended):
    """Find matching SRC in rytec database"""
    # Converti PNG SRC in formato XML per confronto
    # PNG: 1_0_16_105_F01_20CB_EEEE0000_0_0_0
    # XML: 1:0:16:105:F01:20CB:EEEE0000:0:0:0:
    
    xml_format = png_src.replace('_', ':') + ':'
    
    # 1. Cerca esattamente nel basic mapping
    for channel_id, service_ref in rytec_basic.items():
        if service_ref == xml_format:
            return channel_id, service_ref, 'exact_basic'
    
    # 2. Cerca nell'extended mapping
    for channel_id, entries in rytec_extended.items():
        for entry in entries:
            if entry['sref'] == xml_format:
                return channel_id, entry['sref'], 'exact_extended'
    
    # 3. Prova matching parziale (senza gli ultimi zeri)
    parts = png_src.split('_')
    if len(parts) == 10:
        short_src = '_'.join(parts[:7])  # 1_0_16_105_F01_20CB_EEEE0000
        
        for channel_id, service_ref in rytec_basic.items():
            if service_ref:
                service_ref_png = service_ref.rstrip(':').replace(':', '_')
                if service_ref_png.startswith(short_src):
                    return channel_id, service_ref, 'partial_match'
    
    return None, None, None

def create_snp_code(channel_id):
    """Create SNP code from channel ID"""
    if not channel_id:
        return "UNKN"
    
    # Rimuovi estensione del paese
    base_id = channel_id.split('.')[0]
    
    # Prendi prime 4 lettere
    snp = base_id[:4].upper()
    
    # Special cases
    special_cases = {
        'RAI1': 'RAI1',
        'RAI2': 'RAI2',
        'RAI3': 'RAI3',
        'RAI4': 'RAI4',
        'RAI5': 'RAI5',
        'FILMBOX': 'FBOX',
        'DISCOVERY': 'DISC',
        'NATGEO': 'NGEO',
        'FOX': 'FOX',
        'MTV': 'MTV',
        'NICK': 'NICK',
        'CANALE5': 'C5',
        'ITALIA1': 'IT1',
        'RETE4': 'RET4',
    }
    
    for key, code in special_cases.items():
        if key in base_id.upper():
            return code
    
    return snp

def generate_mapping():
    print("=" * 90)
    print("SRC MAPPING - EXACT PLUGIN MATCHING")
    print("=" * 90)
    
    # 1. Get PNG files
    png_files = get_png_files()
    if not png_files:
        print("No PNG files!")
        return
    
    print(f"PNG files: {len(png_files)}")
    
    # 2. Parse XML EXACTLY like plugin
    rytec_basic, rytec_extended = parse_rytec_xml_like_plugin()
    
    if not rytec_basic:
        print("No XML data!")
        return
    
    # 3. Process PNG files
    png_srcs = {}
    for png_file in png_files:
        src = png_file.replace('.png', '')
        png_srcs[src] = png_srcs.get(src, 0) + 1
    
    print(f"\nUnique PNG SRCs: {len(png_srcs)}")
    
    # 4. Find matches
    results = []
    not_found = []
    
    print("\nFinding matches...")
    
    for png_src in sorted(png_srcs.keys()):
        dup_count = png_srcs[png_src]
        
        # Cerca match
        channel_id, service_ref, match_type = find_matching_src(png_src, rytec_basic, rytec_extended)
        
        if channel_id and service_ref:
            # Estrai informazioni
            snp_code = create_snp_code(channel_id)
            
            # Cerca posizione satellitare
            satellite = "Unknown"
            if channel_id in rytec_extended:
                for entry in rytec_extended[channel_id]:
                    if entry.get('sat_position'):
                        satellite = entry['sat_position']
                        break
            
            # Crea linea
            line = f"{png_src} - {snp_code} - {satellite}"
            if dup_count > 1:
                line += f" (appears {dup_count} times)"
            
            results.append(line)
        else:
            # Non trovato
            line = f"{png_src} - NOTFOUND - Unknown"
            if dup_count > 1:
                line += f" (appears {dup_count} times)"
            
            results.append(line)
            not_found.append(png_src)
    
    # 5. Write output
    print(f"\nWriting files...")
    
    with open('src_mapping_final.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - SNP - Satellite Positions\n")
        f.write("# Generated with EXACT plugin matching\n")
        f.write(f"# PNG SRCs: {len(png_srcs)}\n")
        f.write(f"# Found in XML: {len(png_srcs) - len(not_found)}\n")
        f.write(f"# Not found: {len(not_found)}\n\n")
        
        for line in results:
            f.write(line + "\n")
    
    if not_found:
        with open('not_found_final.txt', 'w', encoding='utf-8') as f:
            f.write("# SRC not found in XML\n")
            f.write(f"# Total: {len(not_found)}\n\n")
            
            for src in sorted(not_found):
                f.write(f"{src}\n")
    
    # 6. Statistics
    print("\n" + "=" * 90)
    print("RESULTS:")
    print(f"Total PNG SRCs: {len(png_srcs)}")
    print(f"Found: {len(png_srcs) - len(not_found)}")
    print(f"Not found: {len(not_found)}")
    
    # Debug: mostra alcuni esempi
    print(f"\nSample matches:")
    found_samples = [r for r in results if 'NOTFOUND' not in r][:3]
    for sample in found_samples:
        print(f"  {sample}")
    
    if not_found:
        print(f"\nSample not found:")
        for src in not_found[:3]:
            print(f"  {src}")

if __name__ == "__main__":
    generate_mapping()

if __name__ == "__main__":
    generate_mapping()
