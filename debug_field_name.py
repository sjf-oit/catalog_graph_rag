import xml.etree.ElementTree as ET

NS = {'wp': 'http://wordpress.org/export/1.2/'}
tree = ET.parse("catalog.2026-2027.WordPress.2026-10-30.xml.txt")
root = tree.getroot()
channel = root.find('channel')

print("Scanning academic_programs post meta keys...\n")
for item in channel.findall('item'):
    pt = item.find('wp:post_type', NS)
    if pt is None or pt.text != 'academic_programs':
        continue

    title_el = item.find('title')
    title = title_el.text.strip() if title_el is not None else ''

    meta_keys = []
    for postmeta in item.findall('wp:postmeta', NS):
        k = postmeta.find('wp:meta_key', NS)
        v = postmeta.find('wp:meta_value', NS)
        if k is not None and k.text:
            val_preview = (v.text or '')[:80].replace('\n', ' ') if v is not None else ''
            meta_keys.append(f"  {k.text:<45} = {val_preview}")

    if meta_keys:
        print(f"Program: {title}")
        for mk in meta_keys:
            print(mk)
        print()
        break  # Just show first program for now