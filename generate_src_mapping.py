# -*- coding: utf-8 -*-
# debug_src_matching.py
import requests
import re

def find_exact_match_example():
    """Find one SRC that exists in both PNG and XML"""
    
    # Prendi alcuni PNG
    url = "https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF"
    response = requests.get(url, headers={'Accept': 'application/vnd.github.v3+json'})
    png_files = []
    
    for item in response.json():
        if isinstance(item, dict):
            filename = item.get('name', '')
            if filename.endswith('.png'):
                png_files.append(filename.replace('.png', ''))
    
    print(f"Got {len(png_files)} PNG SRCs")
    
    # Prendi XML
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    xml_data = requests.get(xml_url).text
    
    # Cerca il PRIMO match
    for png_src in png_files[:50]:  # Primi 50
        # Cerca nel XML
        if png_src.replace('_', ':') + ':' in xml_data:
            print(f"\nFOUND MATCH!")
            print(f"PNG SRC: {png_src}")
            print(f"XML format: {png_src.replace('_', ':')}:")
            
            # Trova la linea nel XML
            lines = xml_data.split('\n')
            for line in lines:
                if png_src.replace('_', ':') + ':' in line:
                    print(f"XML line: {line.strip()}")
                    return
    
    print("\nNo matches found in first 50 PNGs!")

def analyze_src_formats():
    """Analyze SRC formats in both files"""
    print("Analyzing SRC formats...")
    
    # Esempio dal tuo output
    png_example = "1_0_0_10_384_110_EEEE0000_0_0_0"
    print(f"\nPNG example: {png_example}")
    print(f"Parts: {png_example.split('_')}")
    
    # Cerca questo esatto SRC nel XML
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    xml_data = requests.get(xml_url).text
    
    # Converti in formato XML
    xml_format = png_example.replace('_', ':') + ':'
    print(f"\nLooking for in XML: {xml_format}")
    
    if xml_format in xml_data:
        print("FOUND in XML!")
        lines = xml_data.split('\n')
        for line in lines:
            if xml_format in line:
                print(f"Line: {line.strip()}")
    else:
        print("NOT FOUND in XML!")
        
        # Cerca varianti
        print("\nSearching for variants...")
        # Variante 1: Senza gli ultimi zeri
        variant1 = '1:0:0:10:384:110:EEEE0000:'
        if variant1 in xml_data:
            print(f"Found variant 1: {variant1}")
        
        # Variante 2: Solo parte iniziale
        variant2 = '1:0:0:10:'
        if variant2 in xml_data:
            print(f"Found variant 2: {variant2}")

if __name__ == "__main__":
    print("=" * 60)
    print("DEBUG SRC MATCHING")
    print("=" * 60)
    
    find_exact_match_example()
    analyze_src_formats()
