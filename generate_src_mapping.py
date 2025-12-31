# -*- coding: utf-8 -*-
import requests
import re
import io


def main():
    # Get PNG files from SRF folder
    api_url = "https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF"
    response = requests.get(
        api_url, headers={
            'Accept': 'application/vnd.github.v3+json'})
    png_files = [f['name']
                 for f in response.json() if f['name'].endswith('_small.png')]

    print("Found {} PNG files".format(len(png_files)))

    # Get channel names from XML
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    xml_data = requests.get(xml_url).text

    # Parse SRC -> channel name from XML
    channel_map = {}
    pattern = r'<channel\s+id="([^"]+)".*?<display-name>([^<]+)</display-name>'
    matches = re.findall(pattern, xml_data, re.DOTALL)

    for src, name in matches:
        if '_' in src:  # Ensure it is an SRC code
            channel_map[src] = name.strip()

    print("Found {} channels in XML".format(len(channel_map)))

    # Generate output lines
    lines = []
    for png in sorted(png_files):
        src = png.replace('_small.png', '')

        # Channel name from XML or default
        parts = src.split('_')
        if src in channel_map:
            channel = channel_map[src]
        elif len(parts) > 4:
            channel = "channel {}".format(parts[4])
        else:
            channel = "unknown"

        # Satellite positions (simple logic)
        if 'F01' in src:
            sat = "23.5E|16.0E|13.0E|0.8W"
        elif any(x in src for x in ['2C', '6', '2D', '2E', '2F', '30', '31', '32', '33']):
            sat = "13.0E"
        else:
            sat = "unknown"

        lines.append("{} - {} - {}".format(src, channel, sat))

    # Write mapping file
    with io.open('src_mapping.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print("Mapping file created with {} entries".format(len(lines)))


if __name__ == "__main__":
    main()
