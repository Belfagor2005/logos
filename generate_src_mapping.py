# generate_src_mapping_fast.py
import requests
import re


def main():
    print("Generazione file SRC mapping...")
    
    # 1. Prendi file PNG dalla cartella SRF
    png_response = requests.get("https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF")
    png_files = [item['name'] for item in png_response.json() if item['name'].endswith('_small.png')]
    
    print(f"Trovati {len(png_files)} file PNG")
    
    # 2. Prendi il file XML
    xml_response = requests.get("https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml")
    xml_content = xml_response.text
    
    # 3. Crea dizionario SRC -> Nome Canale dal XML
    channel_map = {}
    # Cerca pattern: <channel id="1_0_16_105_F01_20CB_EEEE0000_0_0_0">
    matches = re.findall(r'<channel\s+id="([^"]+)".*?<display-name>([^<]+)</display-name>', xml_content, re.DOTALL)
    
    for src, name in matches:
        if '_' in src:  # Assicurati che sia uno SRC
            channel_map[src] = name.strip()
    
    print(f"Trovati {len(channel_map)} canali nel XML")
    
    # 4. Genera il file
    with open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - Nome Canale - Posizioni Satellitari\n\n")
        
        for png_file in sorted(png_files):
            src = png_file.replace('_small.png', '')
            
            # Nome canale
            channel_name = channel_map.get(src, f"canale {src.split('_')[4] if len(src.split('_')) > 4 else 'sconosciuto'}")
            
            # Posizioni satellitari (logica semplice)
            if 'F01' in src:
                satellites = "23.5E|16.0E|13.0E|0.8W"
            elif any(x in src for x in ['2C', '6', '2D', '2E', '2F', '30', '31', '32', '33']):
                satellites = "13.0E"
            else:
                satellites = "posizione non determinata"
            
            f.write(f"{src} - {channel_name} - {satellites}\n")
    
    print("File generato con successo!")


if __name__ == "__main__":
    main()
