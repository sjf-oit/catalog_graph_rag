# step3_scraper.py
# Pure Python scraper for catalog.sjf.edu
# Parses CourseLeaf prose/list format
# Dependencies: requests, beautifulsoup4 (already installed)
# Compatible: Python 3.9+ on Linux or Windows

import json
import time
import re
import requests
from bs4 import BeautifulSoup

INPUT_FILE  = "catalog_map.json"
OUTPUT_FILE = "programs_data.json"
DEBUG       = False   # Set to True to print raw HTML for first program

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

REQUIREMENTS_FIELD_ID = "ct_Program_Re_editor_226b"

# Matches course codes like "MATH 120C", "BIOL 151", "ACCT 101"
COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,5})\s+(\d{3}[A-Z0-9]*)\b')

# Matches credits like "(3)" or "(3-4)" or "(1-4)"
CREDITS_RE = re.compile(r'\((\d+(?:[–\-]\d+)?)\)\s*$')

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def fetch_page(url, retries=3):
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, timeout=20)
            if resp.status_code == 200:
                if DEBUG:
                    print(f"\n{'='*60}")
                    print(f"DEBUG HTML for: {url}")
                    print(resp.text[:3000])
                    print(f"{'='*60}\n")
                return BeautifulSoup(resp.text, 'html.parser')
            else:
                print(f"      ⚠️  HTTP {resp.status_code} → {url}")
                return None
        except requests.RequestException as e:
            if attempt < retries - 1:
                print(f"      ↩️  Retry {attempt + 1} ({e})")
                time.sleep(2)
            else:
                print(f"      ❌ Failed after {retries} attempts: {e}")
                return None


def parse_course_line(text):
    """
    Parse a line of text into a course dict if it contains a course code.
    e.g. "MATH 120C – P4 Calculus I (4)" → {code, title, credits}
    """
    text = clean(text)
    if not text:
        return None

    match = COURSE_CODE_RE.search(text)
    if not match:
        return None

    code = f"{match.group(1)} {match.group(2)}"

    credits_match = CREDITS_RE.search(text)
    credits = credits_match.group(1) if credits_match else ""

    after_code = text[match.end():].strip()
    after_code = re.sub(r'^[\s\-–—]+', '', after_code)
    title = CREDITS_RE.sub('', after_code).strip()
    title = re.sub(r'[\s\-–—]+$', '', title).strip()

    return {
        "type":    "course",
        "code":    code,
        "title":   title,
        "credits": credits,
        "raw":     text,
    }


def parse_requirements_from_soup(soup):
    """
    Parse program requirements from CourseLeaf prose/list HTML.
    Walks all block elements in document order.
    """
    groups = []

    # Try to find the main content div — CourseLeaf wraps content in various ways
    content = (
        soup.find('div', class_=re.compile(r'field-items|field-body|field-item', re.I))
        or soup.find('div', id=re.compile(r'content|main|program', re.I))
        or soup.find('main')
        or soup.find('article')
        or soup.find('body')
        or soup
    )

    current_group  = None
    current_courses = []

    def save_group():
        nonlocal current_group, current_courses
        if current_group is not None:
            groups.append({
                "name":    current_group,
                "courses": current_courses[:],
            })
        current_group   = None
        current_courses = []

    for el in content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'li']):
        tag  = el.name
        text = clean(el.get_text())

        if not text:
            continue

        # Skip page title
        if tag == 'h1':
            continue

        # New requirement group heading
        if tag in ('h2', 'h3', 'h4'):
            save_group()
            current_group   = text
            current_courses = []
            continue

        # Skip paragraph containers that just wrap lists (children handled separately)
        if tag == 'p' and el.find(['ul', 'ol', 'li']):
            continue

        # Try to parse as a course line
        if tag in ('li', 'p'):
            course = parse_course_line(text)
            if course:
                if re.match(r'^(or\b|OR\b)', text):
                    course['type'] = 'or_course'
                if current_group is None:
                    current_group   = "Program Requirements"
                    current_courses = []
                current_courses.append(course)
            else:
                # Short non-course text = subheader or comment
                if current_group is not None and 10 < len(text) < 300:
                    if re.search(
                        r'credit|choose|select|following|elective|require|note|must|may',
                        text, re.I
                    ):
                        current_courses.append({"type": "comment", "text": text})

    save_group()

    # Compute estimated total credits per group
    for group in groups:
        total = 0
        for c in group["courses"]:
            if c.get("type") in ("course", "or_course"):
                m = re.match(r'(\d+)', str(c.get("credits", "")))
                if m:
                    total += int(m.group(1))
        group["total_credits"] = str(total) if total > 0 else ""

    return groups


def scrape_program(program, debug_mode=False):
    global DEBUG
    DEBUG = debug_mode

    base_url = program["url"].rstrip('/')

    # 1. Fetch overview
    overview_soup = fetch_page(base_url + '/')
    if not overview_soup:
        return None

    h1         = overview_soup.find('h1')
    page_title = clean(h1.get_text()) if h1 else program["name"]

    content_el = (
        overview_soup.find('div', class_=re.compile(r'field-items|field-body|field-item', re.I))
        or overview_soup.find('main')
    )
    overview = clean(content_el.get_text())[:2000] if content_el else ""

    degree_type = ""
    for marker in ["B.S.", "B.A.", "M.S.", "M.S.Ed.", "M.B.A.", "MBA",
                   "Ed.D.", "Pharm.D.", "DNP", "Minor", "Certificate"]:
        if marker.lower() in page_title.lower() or marker.lower() in program["name"].lower():
            degree_type = marker
            break

    # 2. Fetch requirements tab
    req_url  = f"{base_url}?fieldid={REQUIREMENTS_FIELD_ID}"
    req_soup = fetch_page(req_url)

    if req_soup:
        req_groups = parse_requirements_from_soup(req_soup)
    else:
        print(f"      ⚠️  No requirements page found")
        req_groups = []

    total_courses = sum(
        1 for g in req_groups
        for c in g["courses"]
        if c.get("type") in ("course", "or_course")
    )

    return {
        "name":               program["name"],
        "slug":               program.get("slug", ""),
        "url":                base_url + '/',
        "requirements_url":   req_url,
        "level":              program.get("level", ""),
        "school":             program.get("school", ""),
        "catalog_year":       program.get("catalog_year", "2026-2027"),
        "page_title":         page_title,
        "degree_type":        degree_type,
        "overview":           overview,
        "requirement_groups": req_groups,
        "total_groups":       len(req_groups),
        "total_courses":      total_courses,
    }


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        catalog = json.load(f)

    # Flatten all programs with school/level context
    all_programs = []
    for school in catalog["schools"]:
        for level_entry in school["levels"]:
            for prog in level_entry["programs"]:
                all_programs.append({
                    **prog,
                    "school":       school["name"],
                    "level":        level_entry["level"],
                    "catalog_year": catalog["catalog_year"],
                })

    total = len(all_programs)
    print(f"📋 {total} programs to scrape\n")

    results = []
    errors  = []

    for i, prog in enumerate(all_programs, 1):
        label = f"[{i:02d}/{total}] {prog['school']} | {prog['name']}"
        print(f"  🔍 {label}")

        # Enable debug HTML dump for first program only
        debug_this = (i == 1)
        data = scrape_program(prog, debug_mode=debug_this)

        if data:
            results.append(data)
            # Incremental save after every successful scrape
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"      ✅ {data['total_groups']} groups, {data['total_courses']} courses")
        else:
            errors.append(prog)
            print(f"      ❌ Failed to fetch page")

        time.sleep(0.75)

    print(f"\n{'='*60}")
    print(f"✅ Scraped:  {len(results)} programs")
    print(f"❌ Failed:   {len(errors)} programs")
    if errors:
        print("\nFailed programs:")
        for p in errors:
            print(f"  - {p['name']} ({p.get('url', 'no url')})")
    print(f"\n📄 Saved to: {OUTPUT_FILE}")
    print(f"{'='*60}")
    print(f"\n🚀 Ready for Step 4 — Neo4j loader!")


if __name__ == "__main__":
    main()
