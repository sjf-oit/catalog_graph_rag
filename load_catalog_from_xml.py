#!/usr/bin/env python3
"""
load_catalog_from_xml.py

Self-contained Neo4j Knowledge Graph Loader for St. John Fisher University Catalogs.
Directly ingests Courses, Schools, Programs, ProgramTypes, RequirementGroups, and
Relationships (PREREQUISITE_FOR, REQUIRES_COURSE, HAS_LEVEL, etc.) from WordPress XML.

Usage:
  python load_catalog_from_xml.py                         # Defaults to 2026-2027
  python load_catalog_from_xml.py --year 2025-2026
  python load_catalog_from_xml.py --year 2024-2025
  python load_catalog_from_xml.py --year 2023-2024
  python load_catalog_from_xml.py --year 2022-2023
  python load_catalog_from_xml.py --xml custom_path.xml --year 2026-2027
"""

import os
import re
import glob
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from neo4j import GraphDatabase

# --- Configuration & Credentials ---
load_dotenv()
URI  = os.getenv("NEO4J_URI", "neo4j+ssc://a0747a9f.databases.neo4j.io")
USER = os.getenv("NEO4J_USER", "a0747a9f")
PWD  = os.getenv("NEO4J_PWD", "")

# XML Namespaces
NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'dc': 'http://purl.org/dc/elements/1.1/'
}

# Mapping table for Canonical Schools
CANONICAL_SCHOOL_MAP = {
    "school of arts and sciences": "School of Arts and Sciences",
    "school of business": "School of Business",
    "ralph c. wilson, jr. school of education": "Ralph C. Wilson, Jr. School of Education",
    "school of education": "Ralph C. Wilson, Jr. School of Education",
    "wegmans school of nursing": "Wegmans School of Nursing",
    "school of nursing": "Wegmans School of Nursing",
    "wegmans school of pharmacy": "Wegmans School of Pharmacy",
    "school of pharmacy": "Wegmans School of Pharmacy",
}

COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,5})[- ]?([0-9]{3,4}[A-Z]?)\b')


def parse_args():
    parser = argparse.ArgumentParser(description="Load SJF Catalog from XML directly into Neo4j.")
    parser.add_argument(
        '--year',
        type=str,
        default='2026-2027',
        help='Catalog year to process (e.g. 2026-2027, 2025-2026)'
    )
    parser.add_argument(
        '--xml',
        type=str,
        default=None,
        help='Optional path to explicit XML file. If omitted, auto-resolves based on --year.'
    )
    return parser.parse_args()


def find_xml_file(catalog_year, explicit_path=None):
    """Auto-resolves the matching XML file for the specified catalog year."""
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path

    patterns = [
        f"catalog.{catalog_year}.WordPress.*.xml.txt",
        f"catalog.{catalog_year}.WordPress.*.xml",
        f"catalog.{catalog_year}.xml.txt",
        f"catalog.{catalog_year}.xml",
        f"catalog_{catalog_year}.xml"
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return sorted(matches)[-1]
    return None


def normalize_code(code_str):
    """Normalize course codes: 'HIST-103D' -> 'HIST 103D', 'CSCI161' -> 'CSCI 161'."""
    if not code_str:
        return ""
    code = code_str.strip().upper()
    code = re.sub(r'[-_]', ' ', code)
    code = re.sub(r'\s+', ' ', code)
    m = re.match(r'^([A-Z]{2,5})\s*([0-9]{3,4}[A-Z]*)$', code)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return code


def parse_prerequisites(prereq_raw):
    """Extract list of referenced course codes from prerequisite field."""
    if not prereq_raw:
        return []
    matches = COURSE_CODE_RE.findall(prereq_raw.upper())
    prereqs = [f"{subj} {num}" for subj, num in matches]
    return list(dict.fromkeys(prereqs))


def normalize_school(raw_name):
    """Returns (canonical_school_name, level) from a raw WordPress schoolhome title."""
    if not raw_name:
        return None, None
    name = raw_name.strip()
    level = "Undergraduate"

    if name.upper().startswith("GR "):
        level = "Graduate"
        name = name[3:].strip()
    elif name.lower().startswith("graduate "):
        level = "Graduate"
        name = name[9:].strip()

    canonical = CANONICAL_SCHOOL_MAP.get(name.lower())
    return canonical, level


def detect_program_type(title, level):
    """Classifies program into: Minor, Certificate, Graduate Degree, or Undergraduate Degree."""
    t = title.lower()

    if "minor" in t:
        return "Minor"

    if "certificate" in t or "cert." in t:
        return "Certificate"

    grad_degree_tokens = [
        "m.s.", " ms ", "master of science", "master of arts", " m.a.",
        "mba", "m.b.a.", "ed.d.", "doctor of education", "ph.d.", "doctor of philosophy",
        "pharm.d.", "doctor of pharmacy", "d.n.p.", "dnp", "doctor of nursing practice",
        "m.s.ed.", "m.ed."
    ]
    if any(tok in t for tok in grad_degree_tokens):
        return "Graduate Degree"

    undergrad_degree_tokens = [
        "b.s.", " bs ", "bachelor of science", "b.a.", " ba ", "bachelor of arts",
        "b.s.n.", "bachelor of science in nursing", "dual major"
    ]
    if any(tok in t for tok in undergrad_degree_tokens):
        return "Undergraduate Degree"

    if level == "Graduate":
        return "Graduate Degree"
    return "Undergraduate Degree"


def parse_requirement_html(html_str, prog_url='', default_group_name='Requirements'):
    """
    Parses requirement groups and embedded course codes directly from WordPress HTML fields.
    Returns structured requirement groups with isolated course lists.
    """
    if not html_str:
        return []

    soup = BeautifulSoup(html_str, 'html.parser')
    groups = []
    current_group_name = default_group_name
    current_courses = []

    for el in soup.find_all(['h2', 'h3', 'h4', 'li', 'p', 'tr']):
        text = el.get_text(separator=' ', strip=True)
        if not text:
            continue

        # Headings define requirement groups/sections
        if el.name in ['h2', 'h3', 'h4']:
            if current_courses:
                groups.append({
                    'name': current_group_name,
                    'program_url': prog_url,
                    'courses': current_courses,
                    'min_credits': ''
                })
            current_group_name = text
            current_courses = []
        else:
            # Extract course codes found in paragraph/list items
            matches = COURSE_CODE_RE.findall(text.upper())
            for subj, num in matches:
                code = normalize_code(f"{subj} {num}")
                parts = code.split()
                if len(parts) == 2 and parts[0].isalpha() and parts[1][0].isdigit():
                    current_courses.append({
                        'code': code,
                        'raw': text[:120]
                    })

    if current_courses:
        groups.append({
            'name': current_group_name,
            'program_url': prog_url,
            'courses': current_courses,
            'min_credits': ''
        })

    # Deduplicate codes within the same group
    for g in groups:
        seen = set()
        deduped = []
        for c in g['courses']:
            if c['code'] not in seen:
                seen.add(c['code'])
                deduped.append(c)
        g['courses'] = deduped

    return groups


def parse_xml_catalog(filepath, catalog_year):
    """Parse courses, schools, and programs directly from WordPress XML export."""
    print(f"📖 Parsing WordPress XML file: {filepath} for Catalog Year: {catalog_year}...")
    tree = ET.parse(filepath)
    root = tree.getroot()
    channel = root.find('channel')

    courses = []
    schools = []
    programs = []

    skip_program_titles = {
        'undergraduate program offerings',
        'graduate program offerings',
        'minors, concentrations, and certificate programs',
        'special programs and academic opportunities',
        'academic programs',
        'programs',
        'courses',
        'course descriptions'
    }

    for item in channel.findall('item'):
        post_type_el = item.find('wp:post_type', NS)
        if post_type_el is None or post_type_el.text is None:
            continue
        post_type = post_type_el.text.strip()

        status_el = item.find('wp:status', NS)
        status = status_el.text.strip() if (status_el is not None and status_el.text) else ""
        if status != 'publish':
            continue

        meta = {}
        for postmeta in item.findall('wp:postmeta', NS):
            k = postmeta.find('wp:meta_key', NS)
            v = postmeta.find('wp:meta_value', NS)
            if k is not None and k.text:
                meta[k.text.strip()] = v.text.strip() if (v is not None and v.text) else ""

        title_el = item.find('title')
        title = title_el.text.strip() if (title_el is not None and title_el.text) else ""
        content_el = item.find('content:encoded', NS)
        content = content_el.text.strip() if (content_el is not None and content_el.text) else ""
        link_el = item.find('link')
        link = link_el.text.strip() if (link_el is not None and link_el.text) else ""

        # --- 1. COURSES ---
        if post_type in ['courses', 'course']:
            subj_num = meta.get('Subject_Course_Number', '')
            subj = meta.get('ct_Subject_Co_text_46b1', '')
            num = meta.get('ct_Course_Num_text_be9d', '')

            if not subj_num and subj and num:
                subj_num = f"{subj} {num}"

            course_code = normalize_code(subj_num)
            parts = course_code.split()

            # Defensive Check: Require valid alpha prefix and numeric starting digit (skips ghost media/attachments)
            if len(parts) < 2 or not parts[0].isalpha() or not parts[1][0].isdigit():
                continue

            active_flag = meta.get('ct_Active_radio_dcc7', 'Y').upper()
            credits_val = meta.get('ct_Credit_Hou_text_b8a9', '')
            prereq_raw = meta.get('ct_Prerequisi_editor_e687', '')
            restrictions = meta.get('ct_Restrictio_editor_4933', '')
            attributes = meta.get('ct_Course_Att_text_888e', '')

            prereq_list = parse_prerequisites(prereq_raw)

            courses.append({
                'code': course_code,
                'subject': subj or parts[0],
                'number': num or parts[1],
                'title': title,
                'credits': str(credits_val),
                'description': content,
                'prereq_raw': prereq_raw,
                'prerequisites': prereq_list,
                'restrictions': restrictions,
                'attributes': attributes,
                'active': active_flag,
                'catalog_year': catalog_year
            })

        # --- 2. SCHOOLS ---
        elif post_type in ['schoolhome', 'schools', 'school']:
            if title:
                canonical, level = normalize_school(title)
                if canonical:
                    schools.append({
                        'name': canonical,
                        'level': level,
                        'url': link,
                        'catalog_year': catalog_year
                    })

        # --- 3. ACADEMIC PROGRAMS ---
        elif post_type in ['academic_programs', 'programs', 'program']:
            if not title or title.strip().lower() in skip_program_titles:
                continue

            # Authoritative level from XML selectbox meta
            level_code = meta.get('ct_College_Co_selectbox_9443', 'UG').strip().upper()
            level = 'Graduate' if level_code == 'GR' else 'Undergraduate'

            prog_type = detect_program_type(title, level)

            # Ingest requirement HTML fields directly from XML
            req_html = meta.get('ct_Program_Re_editor_226b', '')
            minor_html = meta.get('ct_Minor_editor_f6ff', '')

            req_groups = parse_requirement_html(req_html, prog_url=link, default_group_name='Degree Requirements')
            minor_groups = parse_requirement_html(minor_html, prog_url=link, default_group_name='Minor Requirements')
            all_req_groups = req_groups + minor_groups

            programs.append({
                'name': title,
                'friendly_name': meta.get('ct_Friendly_N_text_8b77', title),
                'url': link,
                'level': level,
                'program_type': prog_type,
                'subject_prefix': meta.get('ct_Course_Pre_text_ea2e', ''),
                'content_owner': meta.get('ct_Content_Ow_text_6429', ''),
                'requirement_groups': all_req_groups,
                'catalog_year': catalog_year
            })

    print(f"  ✅ Extracted {len(courses)} active/inactive courses (ghost attachments excluded)")
    print(f"  ✅ Extracted {len(schools)} school mappings (resolving to canonical 5 schools)")
    print(f"  ✅ Extracted {len(programs)} academic programs with direct requirement groups")
    return courses, schools, programs


def setup_schema(session):
    """Setup multi-year idempotent constraints and indexes in Neo4j."""
    print("\n🏗️  Setting up Neo4j schema & constraints...")
    
    # 1. Drop legacy single-property constraints that block multi-year loading
    legacy_constraints = [
        "program_url_unique",
        "program_name_unique", 
        "course_code_unique",
        "school_name_unique",
        "reqgroup_node_key"
    ]
    for c_name in legacy_constraints:
        try:
            session.run(f"DROP CONSTRAINT {c_name} IF EXISTS")
        except Exception:
            pass

    # 2. Assert multi-year composite node keys & indexes
    queries = [
        "CREATE CONSTRAINT catalog_year_unique IF NOT EXISTS FOR (c:CatalogYear) REQUIRE c.year IS UNIQUE",
        "CREATE CONSTRAINT level_name_unique   IF NOT EXISTS FOR (l:Level)       REQUIRE l.name IS UNIQUE",
        "CREATE CONSTRAINT progtype_name_unique IF NOT EXISTS FOR (pt:ProgramType) REQUIRE pt.name IS UNIQUE",
        "CREATE CONSTRAINT school_node_key     IF NOT EXISTS FOR (s:School)      REQUIRE (s.name, s.catalog_year) IS NODE KEY",
        "CREATE CONSTRAINT course_node_key     IF NOT EXISTS FOR (c:Course)      REQUIRE (c.code, c.catalog_year) IS NODE KEY",
        "CREATE CONSTRAINT program_url_key     IF NOT EXISTS FOR (p:Program)     REQUIRE (p.url, p.catalog_year) IS NODE KEY",
        "CREATE CONSTRAINT req_group_key       IF NOT EXISTS FOR (r:RequirementGroup) REQUIRE (r.name, r.program_url, r.catalog_year) IS NODE KEY",
        "CREATE INDEX course_title_idx         IF NOT EXISTS FOR (c:Course)      ON (c.title)",
        "CREATE INDEX program_name_idx         IF NOT EXISTS FOR (p:Program)     ON (p.name)"
    ]
    for q in queries:
        try:
            session.run(q)
        except Exception as e:
            print(f"  ⚠️ Schema query notice: {e}")
    print("  ✅ Schema ready.")


def load_to_neo4j(courses, schools, programs, catalog_year):
    """Load extracted records, requirement groups, and relationships into Neo4j."""
    print(f"\n🔌 Connecting to Neo4j at {URI}...")
    driver = GraphDatabase.driver(URI, auth=(USER, PWD))
    driver.verify_connectivity()
    print("  ✅ Connected successfully!")

    with driver.session() as session:
        # 1. Constraints & Indexes
        setup_schema(session)

        # 2. Year, Levels, and Program Types
        print(f"\n📅 Initializing CatalogYear ({catalog_year}), Level, and ProgramType nodes...")
        session.run("""
            MERGE (cy:CatalogYear {year: $catalog_year})
            MERGE (ug:Level {name: 'Undergraduate'})
            MERGE (gr:Level {name: 'Graduate'})
            MERGE (ug)-[:VALID_IN]->(cy)
            MERGE (gr)-[:VALID_IN]->(cy)
            MERGE (:ProgramType {name: 'Undergraduate Degree'})
            MERGE (:ProgramType {name: 'Graduate Degree'})
            MERGE (:ProgramType {name: 'Minor'})
            MERGE (:ProgramType {name: 'Certificate'})
        """, catalog_year=catalog_year)

        # 3. Canonical Schools
        print(f"🏫 Ingesting canonical School nodes for {catalog_year}...")
        for s in schools:
            session.run("""
                MATCH (cy:CatalogYear {year: $catalog_year})
                MATCH (lvl:Level {name: $level})
                MERGE (sch:School {name: $name, catalog_year: $catalog_year})
                ON CREATE SET sch.url = $url
                MERGE (sch)-[:VALID_IN]->(cy)
                MERGE (sch)-[:HAS_LEVEL]->(lvl)
            """, name=s['name'], level=s['level'], url=s['url'], catalog_year=catalog_year)

        # 4. Ingest Courses
        print(f"📚 Ingesting {len(courses)} courses in batches...")
        course_query = """
            UNWIND $batch AS c
            MATCH (cy:CatalogYear {year: c.catalog_year})
            MERGE (node:Course {code: c.code, catalog_year: c.catalog_year})
            SET node.subject      = c.subject,
                node.number       = c.number,
                node.title        = c.title,
                node.credits      = c.credits,
                node.description  = c.description,
                node.restrictions = c.restrictions,
                node.attributes   = c.attributes,
                node.active       = c.active,
                node.prereq_raw   = c.prereq_raw
            MERGE (node)-[:OFFERED_IN]->(cy)
        """
        batch_size = 200
        for i in range(0, len(courses), batch_size):
            batch = courses[i:i + batch_size]
            session.run(course_query, batch=batch)
            print(f"   - Loaded courses {i + 1} to {min(i + batch_size, len(courses))}")

        # 5. Prerequisite Links
        print("\n🔗 Building PREREQUISITE_FOR relationships...")
        prereq_query = """
            UNWIND $batch AS item
            MATCH (prereq:Course {code: item.prereq_code, catalog_year: $catalog_year})
            MATCH (target:Course {code: item.target_code, catalog_year: $catalog_year})
            MERGE (prereq)-[:PREREQUISITE_FOR]->(target)
        """
        prereq_pairs = []
        for c in courses:
            for p in c['prerequisites']:
                prereq_pairs.append({'prereq_code': p, 'target_code': c['code']})

        for i in range(0, len(prereq_pairs), batch_size):
            batch = prereq_pairs[i:i + batch_size]
            session.run(prereq_query, batch=batch, catalog_year=catalog_year)
        print(f"  ✅ Created/verified {len(prereq_pairs)} prerequisite links.")

        # 6. Academic Programs
        print(f"\n🎓 Ingesting {len(programs)} academic programs...")
        prog_query = """
            UNWIND $batch AS p
            MATCH (cy:CatalogYear {year: p.catalog_year})
            MATCH (lvl:Level {name: p.level})
            MATCH (pt:ProgramType {name: p.program_type})
            MERGE (prog:Program {url: p.url, catalog_year: p.catalog_year})
            SET prog.name           = p.name,
                prog.friendly_name  = p.friendly_name,
                prog.level          = p.level,
                prog.program_type   = p.program_type,
                prog.subject_prefix = p.subject_prefix,
                prog.content_owner  = p.content_owner
            MERGE (prog)-[:HAS_LEVEL]->(lvl)
            MERGE (prog)-[:HAS_TYPE]->(pt)
            MERGE (prog)-[:VALID_IN]->(cy)
        """
        for i in range(0, len(programs), batch_size):
            batch = programs[i:i + batch_size]
            session.run(prog_query, batch=batch)

        # 7. Requirement Groups & Course Links (Parsed directly from XML HTML)
        print(f"\n📋 Linking Requirement Groups and Course Requirements...")
        rg_count = 0
        req_link_count = 0

        for prog in programs:
            prog_url = prog['url']
            for rg in prog.get('requirement_groups', []):
                rg_name = rg['name']
                courses_in_group = rg.get('courses', [])
                if not courses_in_group:
                    continue

                min_credits = rg.get('min_credits', '')

                session.run("""
                    MATCH (p:Program {url: $prog_url, catalog_year: $catalog_year})
                    MERGE (rg:RequirementGroup {
                        name: $rg_name,
                        program_url: $prog_url,
                        catalog_year: $catalog_year
                    })
                    ON CREATE SET rg.min_credits = $min_credits
                    ON MATCH  SET rg.min_credits = $min_credits
                    MERGE (p)-[:HAS_REQUIREMENT_GROUP]->(rg)
                """, prog_url=prog_url, catalog_year=catalog_year, rg_name=rg_name, min_credits=min_credits)
                rg_count += 1

                for item in courses_in_group:
                    session.run("""
                        MATCH (rg:RequirementGroup {
                            name: $rg_name,
                            program_url: $prog_url,
                            catalog_year: $catalog_year
                        })
                        MATCH (c:Course {code: $code, catalog_year: $catalog_year})
                        MERGE (rg)-[:REQUIRES_COURSE]->(c)
                    """, rg_name=rg_name, prog_url=prog_url, catalog_year=catalog_year, code=item['code'])
                    req_link_count += 1

        print(f"  ✅ Created {rg_count} RequirementGroups")
        print(f"  ✅ Created {req_link_count} REQUIRES_COURSE relationships")

        print("\n=======================================================")
        print(f"🎉 Catalog Year {catalog_year} Ingestion Complete!")
        print("=======================================================")

    driver.close()


def main():
    args = parse_args()
    catalog_year = args.year
    xml_path = find_xml_file(catalog_year, args.xml)

    if not xml_path or not os.path.exists(xml_path):
        print(f"❌ Error: Could not find XML file for catalog year '{catalog_year}'.")
        print("Please place the XML file in this directory or specify it with --xml <path>")
        return

    courses, schools, programs = parse_xml_catalog(xml_path, catalog_year)
    load_to_neo4j(courses, schools, programs, catalog_year)


if __name__ == "__main__":
    main()