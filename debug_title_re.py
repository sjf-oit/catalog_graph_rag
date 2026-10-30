#!/usr/bin/env python3
"""
debug_title_re.py

Tests TITLE_LINE_RE against the live CSCI catalog page to show
exactly which course headers are matching and which are not.
"""

import re
import requests
from bs4 import BeautifulSoup

BASE_URL     = "https://catalog.sjf.edu"
CATALOG_YEAR = "2026-2027"
HEADERS      = {"User-Agent": "Mozilla/5.0 SJF-Catalog-Scraper/1.0"}

# Current regex
TITLE_LINE_RE = re.compile(
    r'^([A-Z]{2,5})-(\d{3,4}[A-Z0-9]*)\s+(.+?)\s*\((\d+(?:[.,\-\u2013]\d+)?(?:\s*TO\s*\d+)?)\)\s*$',
    re.IGNORECASE
)

url  = f"{BASE_URL}/{CATALOG_YEAR}/courses/?prefix=CSCI"
resp = requests.get(url, headers=HEADERS, timeout=20)
soup = BeautifulSoup(resp.text, "html.parser")
lines = [line.strip() for line in soup.get_text(separator="\n").split("\n") if line.strip()]

print("=== LINES THAT MATCH TITLE_LINE_RE ===")
matched = 0
for line in lines:
    if TITLE_LINE_RE.match(line):
        print(f"  MATCH: {line}")
        matched += 1

print(f"\nTotal matched: {matched}")

print("\n=== LINES CONTAINING A COURSE CODE PATTERN (potential missed headers) ===")
CODE_RE = re.compile(r'^[A-Z]{2,5}-\d{3,4}')
for line in lines:
    if CODE_RE.match(line) and not TITLE_LINE_RE.match(line):
        print(f"  MISSED: {repr(line)}")

print("\n=== LINES CONTAINING 'pre-requisites' ===")
for line in lines:
    if "pre-requisite" in line.lower():
        print(f"  PREREQ LINE: {repr(line)}")
