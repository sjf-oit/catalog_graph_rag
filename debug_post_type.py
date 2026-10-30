import xml.etree.ElementTree as ET

NS = {'wp': 'http://wordpress.org/export/1.2/'}
tree = ET.parse("catalog.2026-2027.WordPress.2026-10-30.xml.txt")
root = tree.getroot()
channel = root.find('channel')

post_types = set()
for item in channel.findall('item'):
    pt = item.find('wp:post_type', NS)
    if pt is not None and pt.text:
        post_types.add(pt.text.strip())

print("Post types found in XML:")
for pt in sorted(post_types):
    print(f"  - {pt}")
