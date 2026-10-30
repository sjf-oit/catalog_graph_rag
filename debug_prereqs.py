import requests
from bs4 import BeautifulSoup

url = "https://catalog.sjf.edu/2026-2027/programs/undergraduate/school-of-arts-and-sciences/computer-science/?prefix=CSCI"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
soup = BeautifulSoup(resp.text, "html.parser")

# 1. What div classes exist on this page?
print("=== ALL DIV CLASSES ON PAGE ===")
classes_seen = set()
for tag in soup.find_all(True):
    for c in (tag.get("class") or []):
        classes_seen.add(f"<{tag.name} class='{c}'>")
for c in sorted(classes_seen):
    if any(k in c.lower() for k in ["course", "block", "catalog", "content", "entry", "main", "body"]):
        print(c)

# 2. Search for "Pre-requisites" text anywhere on the page
print("\n=== ELEMENTS CONTAINING 'Pre-requisites' ===")
for tag in soup.find_all(string=lambda t: t and "Pre-requisites" in t):
    parent = tag.parent
    print(f"\nTag: <{parent.name} class='{parent.get('class')}'>")
    print(f"Text: {tag.strip()[:200]}")
    grandparent = parent.parent
    print(f"Parent: <{grandparent.name} class='{grandparent.get('class')}'>")

# 3. Dump first 3000 chars of page body text to see structure
print("\n=== FIRST 3000 CHARS OF PAGE TEXT ===")
print(soup.get_text(separator="\n")[:3000])