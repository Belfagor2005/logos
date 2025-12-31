# generate_src_mapping_fast.py
# -*- coding: utf-8 -*-
import requests
import re
import io


def main():
    print("Generating SRC mapping file...")

    # 1. Get PNG files from SRF folder
    png_response = requests.get(
        "https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF")
    png_files = [item['name'] for item in png_response.json(
    ) if item['name'].endswith('_small.png')]

    print("Found {} PNG files".format(len(png_files)))

    # 2. Get XML file
    xml_response = requests.get(
        "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml")
    xml_content = xml_response.text

    # 3. Build dictionary SRC -> Channel Name from XML
    channel_map = {}
    # Pattern: <channel id="1_0_16_105_F01_20CB_EEEE0000_0_0_0">
    matches = re.findall(
        r'<channel\s+id="([^"]+)".*?<display-name>([^<]+)</display-name>',
        xml_content,
        re.DOTALL)

    for src, name in matches:
        if '_' in src:  # Ensure it's an SRC code
            channel_map[src] = name.strip()

    print("Found {} channels in XML".format(len(channel_map)))

    # 4. Generate the mapping file
    with io.open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("# SRC - Channel Name - Satellite Positions\n\n")

        for png_file in sorted(png_files):
            src = png_file.replace('_small.png', '')

            # Channel name
            parts = src.split('_')
            channel_name = channel_map.get(
                src, "Channel {}".format(
                    parts[4] if len(parts) > 4 else "Unknown"))

            # Satellite positions (simple logic)
            if 'F01' in src:
                satellites = "23.5E|16.0E|13.0E|0.8W"
            elif any(x in src for x in ['2C', '6', '2D', '2E', '2F', '30', '31', '32', '33']):
                satellites = "13.0E"
            else:
                satellites = "Position not determined"

            f.write("{} - {} - {}\n".format(src, channel_name, satellites))

    print("Mapping file generated successfully!")


if __name__ == "__main__":
    main()
