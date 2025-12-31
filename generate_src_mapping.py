# -*- coding: utf-8 -*-
# debug_detailed.py
import requests
import re


def analyze_png_and_xml():
    print("=" * 80)
    print("DETAILED ANALYSIS OF PNG AND XML FORMATS")
    print("=" * 80)

    # 1. Prendi i primi 10 PNG
    print("\n1. ANALYZING PNG FILES...")
    url = "https://api.github.com/repos/Belfagor2005/logos/contents/logos/SRF"
    response = requests.get(
        url, headers={
            'Accept': 'application/vnd.github.v3+json'})

    png_srcs = []
    for item in response.json():
        if isinstance(item, dict):
            filename = item.get('name', '')
            if filename.endswith('.png'):
                src = filename.replace('.png', '')
                png_srcs.append(src)
                if len(png_srcs) >= 10:
                    break

    print(f"First 10 PNG SRCs:")
    for i, src in enumerate(png_srcs, 1):
        parts = src.split('_')
        print(f"\n{i}. {src}")
        print(f"   Parts: {len(parts)}")
        for j, part in enumerate(parts, 1):
            print(
                f"   [{j}] {part} (hex: {
                    part if all(
                        c in '0123456789ABCDEF' for c in part.upper()) else 'no'})")

    # 2. Prendi XML e cerca pattern
    print("\n\n2. ANALYZING XML FILE...")
    xml_url = "https://raw.githubusercontent.com/Belfagor2005/EPGimport-Sources/main/rytec.channels.xml"
    xml_data = requests.get(xml_url).text

    # Cerca SRC nel formato dei PNG ma con :
    print("\nSearching for PNG SRCs in XML (converted to XML format):")

    for png_src in png_srcs:
        xml_format = png_src.replace('_', ':') + ':'

        # Cerca nel XML
        if xml_format in xml_data:
            print(f"\n✓ FOUND: {png_src}")
            print(f"  XML format: {xml_format}")

            # Trova la linea
            lines = xml_data.split('\n')
            for line in lines:
                if xml_format in line:
                    print(f"  XML line: {line.strip()}")
                    break
        else:
            print(f"\n✗ NOT FOUND: {png_src}")
            print(f"  Tried: {xml_format}")

            # Prova varianti
            variants = []

            # Variante 1: hex vs decimal
            parts = png_src.split('_')
            if len(parts) >= 7:
                # I campi 4,5,6 potrebbero essere decimali o hex
                try:
                    # Prova a convertire campo 4 (SID)
                    sid_dec = int(parts[3])
                    sid_hex = hex(sid_dec)[2:].upper()

                    # Prova a convertire campo 5 (TSID)
                    tsid_dec = int(parts[4])
                    tsid_hex = hex(tsid_dec)[2:].upper()

                    # Prova a convertire campo 6 (ONID)
                    onid_dec = int(parts[5])
                    onid_hex = hex(onid_dec)[2:].upper()

                    variant1 = f"{
                        parts[0]}:{
                        parts[1]}:{
                        parts[2]}:{sid_hex}:{tsid_hex}:{onid_hex}:{
                        parts[6]}:{
                        parts[7]}:{
                        parts[8]}:{
                            parts[9]}:"
                    variants.append(variant1)

                    variant2 = f"{
                        parts[0]}:{
                        parts[1]}:{
                        parts[2]}:{sid_dec}:{tsid_dec}:{onid_dec}:{
                        parts[6]}:{
                        parts[7]}:{
                        parts[8]}:{
                            parts[9]}:"
                    variants.append(variant2)

                except BaseException:
                    pass

            # Testa le varianti
            for variant in variants:
                if variant in xml_data:
                    print(f"  FOUND VARIANT: {variant}")
                    break

    # 3. Analizza il formato XML esistente
    print("\n\n3. ANALYZING EXISTING XML FORMATS...")

    # Cerca alcune linee XML casuali per vedere il formato
    lines = xml_data.split('\n')
    xml_samples = []

    for line in lines:
        if '<channel id="' in line and '>' in line:
            # Estrai SRC
            src_match = re.search(r'>([^<]+)<', line)
            if src_match:
                src = src_match.group(1).strip(':')
                parts = src.split(':')
                if len(parts) >= 7:
                    xml_samples.append((line.strip(), src, parts))
                    if len(xml_samples) >= 5:
                        break

    print("\nSample XML entries:")
    for i, (line, src, parts) in enumerate(xml_samples, 1):
        print(f"\n{i}. Line: {line}")
        print(f"   SRC: {src}")
        print(f"   Parts ({len(parts)}):")
        for j, part in enumerate(parts[:7], 1):  # Solo primi 7 campi
            print(f"   [{j}] {part} (len: {len(part)})")

    # 4. Prova matching avanzato
    print("\n\n4. ADVANCED MATCHING ATTEMPT...")

    for png_src in png_srcs:
        parts_png = png_src.split('_')
        if len(parts_png) < 7:
            continue

        print(f"\nAnalyzing PNG: {png_src}")

        # Cerca nel XML per campi individuali
        search_patterns = []

        # Pattern 1: Provider ID (campo 7)
        provider = parts_png[6]
        if provider:
            search_patterns.append(provider)

        # Pattern 2: ONID (campo 6) come hex
        onid = parts_png[5]
        try:
            onid_hex = hex(int(onid))[2:].upper() if onid.isdigit() else onid
            search_patterns.append(onid_hex)
        except BaseException:
            search_patterns.append(onid)

        # Cerca questi pattern nel XML
        found_matches = []
        for pattern in search_patterns:
            if pattern in xml_data and len(pattern) > 2:
                # Trova le linee con questo pattern
                for line in lines:
                    if pattern in line and '<channel' in line:
                        # Estrai SRC dalla linea
                        src_match = re.search(r'>([\dA-F_:]+:)<', line)
                        if src_match:
                            xml_src = src_match.group(1).rstrip(':')
                            found_matches.append((xml_src, line.strip()))

        if found_matches:
            print(f"  Found {len(found_matches)} potential matches:")
            for xml_src, line in found_matches[:2]:  # Mostra max 2
                print(f"    XML: {xml_src}")
                # Confronta i campi
                xml_parts = xml_src.split(':')
                if len(xml_parts) >= 7 and len(parts_png) >= 7:
                    print(f"    Compare:")
                    print(
                        f"      PNG[{3}]: {
                            parts_png[2]} vs XML[{3}]: {
                            xml_parts[2]}")  # SID
                    print(
                        f"      PNG[{6}]: {
                            parts_png[5]} vs XML[{6}]: {
                            xml_parts[5]}")  # ONID
                    print(
                        f"      PNG[{7}]: {
                            parts_png[6]} vs XML[{7}]: {
                            xml_parts[6]}")  # Provider
        else:
            print(f"  No matches found for any pattern")


def test_regex_patterns():
    """Test different regex patterns for extracting SRC from XML"""
    print("\n" + "=" * 80)
    print("TESTING REGEX PATTERNS")
    print("=" * 80)

    # Linea di esempio dal XML
    test_line = '<!-- 13.0E --><channel id="DonnaTV.it">1:0:1:27:791A:217C:EEEE0000:0:0:0:</channel><!-- Donna TV -->'

    print(f"\nTest line: {test_line}")

    patterns = [
        r'>([0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9:ABCDEF]+:[0-9]+:[0-9]+:[0-9]+:)<',
        r'>([\dA-F_:]+:)<',
        r'>([^<]+)<',
        r'>([0-9:]+:)<',
        r'>([0-9:A-F]+:)<',
    ]

    for i, pattern in enumerate(patterns, 1):
        print(f"\nPattern {i}: {pattern}")
        match = re.search(pattern, test_line)
        if match:
            print(f"  MATCH: {match.group(1)}")
            src = match.group(1).rstrip(':')
            print(f"  Clean: {src}")
            print(f"  PNG format: {src.replace(':', '_')}")
        else:
            print(f"  NO MATCH")


if __name__ == "__main__":
    analyze_png_and_xml()
    test_regex_patterns()

    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print("\nSe i PNG non vengono trovati nell'XML, potrebbe essere perché:")
    print("1. I campi sono in formato diverso (decimale vs esadecimale)")
    print("2. L'XML usa un namespace/orbita diversa")
    print("3. I PNG sono per un sistema diverso (es: Sky Italia vs Hotbird)")
    print("4. L'XML è incompleto per i canali italiani")
