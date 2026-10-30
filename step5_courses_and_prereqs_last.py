#!/usr/bin/env python3
"""
step5_courses_and_prereqs.py

Exact-grammar Course & Prerequisite Extractor for SJF CourseLeaf Catalog.

KEY FIX: The SJF catalog renders prerequisite data as TWO separate lines:
    Line N:   'Pre-requisites:'          <- label only, no value
    Line N+1: 'CSCI-161  C'             <- value on the next line

The parser uses look-ahead to capture the next line as the value
when the label line is empty.
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI      = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PWD") or os.getenv("NEO4J_PASSWORD")

BASE_URL     = "https://catalog.sjf.edu"
CATALOG_YEAR = "2026-2027"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) SJF-Catalog-Scraper/1.0"
}

# Matches course codes: "CSCI-161", "CSCI 161", "MATH-120C"
COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,5})[- ](\d{3,4}[A-Z0-9]*)\b')

# Matches a full course title line as rendered in the SJF catalog:
# e.g. "CSCI-162 Found of Comp Sci II (3)"
# e.g. "MATH-120C P4 Calculus I (4)"
# e.g. "CSCI-496 Independent Study (1 TO 3)"
TITLE_LINE_RE = re.compile(
    r'^([A-Z]{2,5})-(\d{3,4}[A-Z0-9]*)\s+(.+?)\s*\((\d+(?:[.,\-\u2013]\d+)?(?:\s*TO\s*\d+)?)\)\s*$',
    re.IGNORECASE
)

# Known metadata label prefixes to skip in description
SKIP_PREFIXES = [
    "typically offered",
    "restrictions:",
    "formerly titled:",
    "fee:",
    "note:",
    "permission",
    "graded s/u",
    "cross-listed",
    "grading:",
]


def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def normalize_code(prefix, number):
    return f"{prefix.upper().strip()} {number.upper().strip()}"


def extract_codes(raw_string, self_code):
    """Extract and normalize course codes from a raw prerequisite/corequisite string."""
    codes = set()
    for m in COURSE_CODE_RE.findall(raw_string):
        norm = normalize_code(m[0], m[1])
        if norm != self_code:
            codes.add(norm)
    return sorted(list(codes))


def parse_page_courses(soup):
    """
    Parses all courses from a /courses/?prefix=XXX page.

    CRITICAL: The SJF CourseLeaf catalog renders metadata as split lines:
        'Pre-requisites:'          <- label line (empty value)
        'CSCI-161  C'             <- value line (next line)

    We use index-based iteration with look-ahead to handle this.
    """
    courses = []

    raw_text = soup.get_text(separator="\n")
    lines = [clean(l) for l in raw_text.split("\n") if clean(l)]

    # Group lines into per-course blocks using TITLE_LINE_RE as the boundary
    blocks = []
    curr = []

    for line in lines:
        if TITLE_LINE_RE.match(line):
            if curr:
                blocks.append(curr)
            curr = [line]
        elif curr:
            curr.append(line)

    if curr:
        blocks.append(curr)

    for block in blocks:
        header = block[0]
        m = TITLE_LINE_RE.match(header)
        if not m:
            continue

        subj    = m.group(1)
        num     = m.group(2)
        title   = clean(m.group(3))
        credits = clean(m.group(4))
        course_code = normalize_code(subj, num)

        desc_lines  = []
        prereqs_raw = ""
        coreqs_raw  = ""
        attributes  = []

        # Index-based loop so we can look ahead when needed
        i = 1
        while i < len(block):
            line  = block[i]
            lower = line.lower()

            # ── Pre-requisites ──────────────────────────────────────────────
            if lower.startswith("pre-requisites:") or lower.startswith("prerequisites:"):
                # Try to get value from same line first
                val = re.sub(r'^(?:pre[- ]?requisites?|prereqs?)\s*:\s*', '', line, flags=re.I).strip()

                if not val or val == "-":
                    # Value is on the NEXT line — look ahead
                    if i + 1 < len(block) and not TITLE_LINE_RE.match(block[i + 1]):
                        next_val = block[i + 1].strip()
                        if next_val and next_val != "-":
                            prereqs_raw = next_val
                            i += 2  # consume both label and value lines
                            continue
                else:
                    prereqs_raw = val

                i += 1
                continue

            # ── Co-requisites ───────────────────────────────────────────────
            if lower.startswith("co-requisites:") or lower.startswith("corequisites:"):
                val = re.sub(r'^(?:co[- ]?requisites?|coreqs?)\s*:\s*', '', line, flags=re.I).strip()

                if not val or val == "-":
                    if i + 1 < len(block) and not TITLE_LINE_RE.match(block[i + 1]):
                        next_val = block[i + 1].strip()
                        if next_val and next_val != "-":
                            coreqs_raw = next_val
                            i += 2
                            continue
                else:
                    coreqs_raw = val

                i += 1
                continue

            # ── Attributes ──────────────────────────────────────────────────
            if lower.startswith("attributes:"):
                val = re.sub(r'^attributes?\s*:\s*', '', line, flags=re.I).strip()

                if not val:
                    if i + 1 < len(block) and not TITLE_LINE_RE.match(block[i + 1]):
                        next_val = block[i + 1].strip()
                        if next_val:
                            attributes = [a.strip() for a in next_val.split() if a.strip()]
                            i += 2
                            continue
                else:
                    attributes = [a.strip() for a in val.split() if a.strip()]

                i += 1
                continue

            # ── Skip known non-description metadata ─────────────────────────
            if any(lower.startswith(k) for k in SKIP_PREFIXES):
                i += 1
                continue

            # ── Description line ────────────────────────────────────────────
            desc_lines.append(line)
            i += 1

        prereq_codes = extract_codes(prereqs_raw, course_code)
        coreq_codes  = extract_codes(coreqs_raw,  course_code)

        courses.append({
            "code":               course_code,
            "title":              title,
            "credits":            credits,
            "description":        " ".join(desc_lines)[:2500],
            "prerequisites_raw":  prereqs_raw,
            "prerequisite_codes": prereq_codes,
            "corequisites_raw":   coreqs_raw,
            "corequisite_codes":  coreq_codes,
            "attributes":         attributes,
        })

    return courses


# ---------------------------------------------------------------------------
# Neo4j Cypher Queries
# ---------------------------------------------------------------------------

Q_GET_ALL_COURSE_CODES = """
MATCH (c:Course {catalog_year: $catalog_year})
RETURN c.code AS code
"""

Q_UPDATE_COURSE = """
MERGE (c:Course {code: $code, catalog_year: $catalog_year})
ON CREATE SET
    c.title        = $title,
    c.credits      = $credits,
    c.description  = $description,
    c.attributes   = $attributes,
    c.prereqs_raw  = $prerequisites_raw,
    c.coreqs_raw   = $corequisites_raw
ON MATCH SET
    c.description  = CASE WHEN $description        <> '' THEN $description        ELSE c.description  END,
    c.attributes   = CASE WHEN size($attributes)   > 0   THEN $attributes         ELSE c.attributes   END,
    c.prereqs_raw  = CASE WHEN $prerequisites_raw  <> '' THEN $prerequisites_raw  ELSE c.prereqs_raw  END,
    c.coreqs_raw   = CASE WHEN $corequisites_raw   <> '' THEN $corequisites_raw   ELSE c.coreqs_raw   END,
    c.title        = CASE WHEN (c.title   IS NULL OR c.title   = '') AND $title   <> '' THEN $title   ELSE c.title   END,
    c.credits      = CASE WHEN (c.credits IS NULL OR c.credits = '') AND $credits <> '' THEN $credits ELSE c.credits END
RETURN c.code AS code
"""

Q_MERGE_PREREQ = """
MERGE (prereq:Course {code: $prereq_code, catalog_year: $catalog_year})
MERGE (course:Course {code: $course_code, catalog_year: $catalog_year})
MERGE (prereq)-[:PREREQUISITE_FOR]->(course)
"""

Q_MERGE_COREQ = """
MERGE (coreq:Course {code: $coreq_code, catalog_year: $catalog_year})
MERGE (course:Course {code: $course_code, catalog_year: $catalog_year})
MERGE (coreq)-[:COREQUISITE_WITH]->(course)
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Connecting to Neo4j at {URI}...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("Connected to Neo4j!\n")

    with driver.session() as session:
        result         = session.run(Q_GET_ALL_COURSE_CODES, catalog_year=CATALOG_YEAR)
        existing_codes = set(row["code"] for row in result)

    prefixes = set()
    for c in existing_codes:
        mm = COURSE_CODE_RE.search(c)
        if mm:
            prefixes.add(mm.group(1).upper())
    sorted_prefixes = sorted(list(prefixes))

    print(f"Found {len(existing_codes)} Course nodes in Neo4j")
    print(f"Scanning {len(sorted_prefixes)} subject prefixes across the catalog...\n")

    scraped_courses     = {}
    total_prereqs_found = 0

    for i, prefix in enumerate(sorted_prefixes, 1):
        target_url = f"{BASE_URL}/{CATALOG_YEAR}/courses/?prefix={prefix}"
        try:
            resp    = requests.get(target_url, headers=HEADERS, timeout=20)
            courses = parse_page_courses(BeautifulSoup(resp.text, "html.parser")) if resp.status_code == 200 else []
        except Exception:
            courses = []

        prereq_count         = sum(len(c.get("prerequisite_codes", [])) for c in courses)
        total_prereqs_found += prereq_count

        print(f"  [{i:02d}/{len(sorted_prefixes)}] Prefix: {prefix:<6} ... {len(courses):3d} courses  ({prereq_count:3d} prereq links)")

        for c in courses:
            scraped_courses[c["code"]] = c

        time.sleep(0.15)

    print(f"\n{'='*60}")
    print(f"Total unique courses extracted: {len(scraped_courses)}")
    print(f"Total prerequisite links found: {total_prereqs_found}")

    with open("courses_data.json", "w", encoding="utf-8") as f:
        json.dump(list(scraped_courses.values()), f, indent=2, ensure_ascii=False)
    print("Saved courses data to courses_data.json")

    print("\nUpdating Neo4j...")
    updated_count = 0
    prereq_links  = 0
    coreq_links   = 0

    with driver.session() as session:
        for code, c_data in scraped_courses.items():
            res = session.run(
                Q_UPDATE_COURSE,
                code=code,
                catalog_year=CATALOG_YEAR,
                title=c_data.get("title", ""),
                credits=c_data.get("credits", ""),
                description=c_data.get("description", ""),
                attributes=c_data.get("attributes", []),
                prerequisites_raw=c_data.get("prerequisites_raw", ""),
                corequisites_raw=c_data.get("corequisites_raw", ""),
            )
            if res.single():
                updated_count += 1

            for prereq in c_data.get("prerequisite_codes", []):
                try:
                    session.run(Q_MERGE_PREREQ, prereq_code=prereq, course_code=code, catalog_year=CATALOG_YEAR)
                    prereq_links += 1
                except Exception:
                    pass

            for coreq in c_data.get("corequisite_codes", []):
                try:
                    session.run(Q_MERGE_COREQ, coreq_code=coreq, course_code=code, catalog_year=CATALOG_YEAR)
                    coreq_links += 1
                except Exception:
                    pass

    driver.close()

    print(f"{'='*60}")
    print(f"Courses Enriched:               {updated_count}")
    print(f"PREREQUISITE_FOR Relationships: {prereq_links}")
    print(f"COREQUISITE_WITH Relationships: {coreq_links}")
    print(f"Complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
