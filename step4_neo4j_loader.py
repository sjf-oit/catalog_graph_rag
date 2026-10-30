# step4_neo4j_loader.py
# Loads programs_data.json into Neo4j
# Uses .env for connection credentials
# Dependencies: neo4j, python-dotenv

import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI      = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PWD")

INPUT_FILE   = "programs_data.json"
CATALOG_YEAR = "2026-2027"

# ─────────────────────────────────────────────────────────────
# Cypher queries
# ─────────────────────────────────────────────────────────────

Q_CATALOG = """
MERGE (cy:CatalogYear {year: $year})
RETURN cy
"""

Q_LEVEL = """
MERGE (l:Level {name: $level})
RETURN l
"""

Q_CATALOG_LEVEL = """
MATCH (cy:CatalogYear {year: $year})
MATCH (l:Level {name: $level})
MERGE (cy)-[:HAS_LEVEL]->(l)
"""

Q_SCHOOL = """
MERGE (s:School {name: $name, catalog_year: $catalog_year})
RETURN s
"""

Q_SCHOOL_RELS = """
MATCH (s:School  {name: $school_name, catalog_year: $catalog_year})
MATCH (l:Level   {name: $level})
MATCH (cy:CatalogYear {year: $catalog_year})
MERGE (s)-[:BELONGS_TO]->(l)
MERGE (s)-[:OFFERED_IN]->(cy)
"""

Q_PROGRAM = """
MERGE (p:Program {url: $url})
SET   p.name         = $name,
      p.slug         = $slug,
      p.degree_type  = $degree_type,
      p.page_title   = $page_title,
      p.overview     = $overview,
      p.level        = $level,
      p.catalog_year = $catalog_year
RETURN p
"""

Q_PROGRAM_RELS = """
MATCH (s:School  {name: $school_name, catalog_year: $catalog_year})
MATCH (p:Program {url: $url})
MATCH (cy:CatalogYear {year: $catalog_year})
MERGE (s)-[:HAS_PROGRAM]->(p)
MERGE (p)-[:VALID_IN]->(cy)
"""

Q_REQ_GROUP = """
MERGE (r:RequirementGroup {name: $name, program_url: $program_url, catalog_year: $catalog_year})
SET   r.total_credits = $total_credits
RETURN r
"""

Q_REQ_GROUP_REL = """
MATCH (p:Program        {url: $program_url})
MATCH (r:RequirementGroup {name: $name, program_url: $program_url, catalog_year: $catalog_year})
MERGE (p)-[:HAS_REQUIREMENT_GROUP]->(r)
"""

Q_COURSE = """
MERGE (c:Course {code: $code, catalog_year: $catalog_year})
SET   c.title   = $title,
      c.credits = $credits
RETURN c
"""

Q_COURSE_REL_REQUIRED = """
MATCH (r:RequirementGroup {name: $group_name, program_url: $program_url, catalog_year: $catalog_year})
MATCH (c:Course           {code: $code, catalog_year: $catalog_year})
MERGE (r)-[:REQUIRES_COURSE]->(c)
"""

Q_COURSE_REL_OR = """
MATCH (r:RequirementGroup {name: $group_name, program_url: $program_url, catalog_year: $catalog_year})
MATCH (c:Course           {code: $code, catalog_year: $catalog_year})
MERGE (r)-[:ALLOWS_OR_COURSE]->(c)
"""


# ─────────────────────────────────────────────────────────────
# Loader functions
# ─────────────────────────────────────────────────────────────

def run(session, query, **params):
    session.run(query, **params)


def load_program(session, prog):
    school_name = prog.get("school", "Unknown School")
    level       = prog.get("level", "Undergraduate")
    program_url = prog["url"]

    # School
    run(session, Q_SCHOOL,
        name=school_name,
        catalog_year=CATALOG_YEAR)

    run(session, Q_SCHOOL_RELS,
        school_name=school_name,
        level=level,
        catalog_year=CATALOG_YEAR)

    # Program
    run(session, Q_PROGRAM,
        url=program_url,
        name=prog.get("name", ""),
        slug=prog.get("slug", ""),
        degree_type=prog.get("degree_type", ""),
        page_title=prog.get("page_title", ""),
        overview=prog.get("overview", ""),
        level=level,
        catalog_year=CATALOG_YEAR)

    run(session, Q_PROGRAM_RELS,
        school_name=school_name,
        url=program_url,
        catalog_year=CATALOG_YEAR)

    # Requirement groups + courses
    for group in prog.get("requirement_groups", []):
        group_name = group.get("name", "Requirements")

        run(session, Q_REQ_GROUP,
            name=group_name,
            program_url=program_url,
            catalog_year=CATALOG_YEAR,
            total_credits=group.get("total_credits", ""))

        run(session, Q_REQ_GROUP_REL,
            name=group_name,
            program_url=program_url,
            catalog_year=CATALOG_YEAR)

        for course in group.get("courses", []):
            ctype = course.get("type", "course")
            if ctype not in ("course", "or_course"):
                continue  # skip comments/headers

            code    = course.get("code", "").strip()
            title   = course.get("title", "").strip()
            credits = course.get("credits", "").strip()

            if not code:
                continue

            run(session, Q_COURSE,
                code=code,
                catalog_year=CATALOG_YEAR,
                title=title,
                credits=credits)

            if ctype == "or_course":
                run(session, Q_COURSE_REL_OR,
                    group_name=group_name,
                    program_url=program_url,
                    catalog_year=CATALOG_YEAR,
                    code=code)
            else:
                run(session, Q_COURSE_REL_REQUIRED,
                    group_name=group_name,
                    program_url=program_url,
                    catalog_year=CATALOG_YEAR,
                    code=code)


def main():
    print(f"🔌 Connecting to {URI} as '{USERNAME}'...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("✅ Connection successful!\n")

    with open(INPUT_FILE, encoding="utf-8") as f:
        programs = json.load(f)

    total = len(programs)
    print(f"📋 Loading {total} programs into Neo4j...\n")

    # Create CatalogYear + Levels once
    with driver.session() as session:
        run(session, Q_CATALOG, year=CATALOG_YEAR)
        for level in ("Undergraduate", "Graduate"):
            run(session, Q_LEVEL, level=level)
            run(session, Q_CATALOG_LEVEL, year=CATALOG_YEAR, level=level)
    print(f"  ✅ CatalogYear ({CATALOG_YEAR}) and Levels created\n")

    success = 0
    errors  = []

    for i, prog in enumerate(programs, 1):
        label = f"[{i:02d}/{total}] {prog.get('school','')} | {prog.get('name','')}"
        try:
            with driver.session() as session:
                load_program(session, prog)
            groups  = prog.get("total_groups", 0)
            courses = prog.get("total_courses", 0)
            print(f"  ✅ {label} → {groups} groups, {courses} courses")
            success += 1
        except Exception as e:
            print(f"  ❌ {label} → ERROR: {e}")
            errors.append({"program": prog.get("name"), "error": str(e)})

    driver.close()

    print(f"\n{'='*60}")
    print(f"✅ Loaded:  {success} programs")
    print(f"❌ Errors:  {len(errors)} programs")
    if errors:
        print("\nFailed programs:")
        for e in errors:
            print(f"  - {e['program']}: {e['error']}")
    print(f"\n🎉 Neo4j graph database populated!")
    print(f"   Open Neo4j Browser and run:")
    print(f"   MATCH (n) RETURN count(n) AS total_nodes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
