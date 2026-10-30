# step1c_fix_constraints.py
# Drops ALL existing constraints and indexes, then rebuilds clean schema
# Run this once before re-running step4_neo4j_loader.py

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI      = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PWD")


def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("✅ Connected\n")

    with driver.session() as session:

        # ── Step 1: List and drop ALL existing constraints ────────────────────
        print("🔍 Finding existing constraints...")
        result = session.run("SHOW CONSTRAINTS")
        constraints = [row["name"] for row in result if row.get("name")]

        if constraints:
            for name in constraints:
                try:
                    session.run(f"DROP CONSTRAINT `{name}` IF EXISTS")
                    print(f"  🗑️  Dropped constraint: {name}")
                except Exception as e:
                    print(f"  ⚠️  Could not drop {name}: {e}")
        else:
            print("  ℹ️  No constraints found")

        # ── Step 2: List and drop ALL existing indexes ────────────────────────
        print("\n🔍 Finding existing indexes...")
        result = session.run("SHOW INDEXES")
        indexes = [row["name"] for row in result if row.get("name") and row.get("type") != "LOOKUP"]

        if indexes:
            for name in indexes:
                try:
                    session.run(f"DROP INDEX `{name}` IF EXISTS")
                    print(f"  🗑️  Dropped index: {name}")
                except Exception as e:
                    print(f"  ⚠️  Could not drop {name}: {e}")
        else:
            print("  ℹ️  No indexes found")

        # ── Step 3: Wipe all nodes and relationships ──────────────────────────
        print("\n🗑️  Wiping all nodes and relationships...")
        session.run("MATCH (n) DETACH DELETE n")
        print("  ✅ Database cleared")

        # ── Step 4: Create fresh schema ───────────────────────────────────────
        print("\n🏗️  Creating fresh schema...")

        SCHEMA = [
            # Uniqueness constraints
            "CREATE CONSTRAINT catalog_year_unique IF NOT EXISTS FOR (c:CatalogYear) REQUIRE c.year IS UNIQUE",
            "CREATE CONSTRAINT level_name_unique   IF NOT EXISTS FOR (l:Level)       REQUIRE l.name IS UNIQUE",
            "CREATE CONSTRAINT program_url_unique  IF NOT EXISTS FOR (p:Program)     REQUIRE p.url  IS UNIQUE",

            # Node key constraints (composite)
            "CREATE CONSTRAINT school_node_key IF NOT EXISTS FOR (s:School) REQUIRE (s.name, s.catalog_year) IS NODE KEY",
            "CREATE CONSTRAINT course_node_key IF NOT EXISTS FOR (c:Course) REQUIRE (c.code, c.catalog_year) IS NODE KEY",
            "CREATE CONSTRAINT req_group_key   IF NOT EXISTS FOR (r:RequirementGroup) REQUIRE (r.name, r.program_url, r.catalog_year) IS NODE KEY",

            # Indexes
            "CREATE INDEX program_name_idx   IF NOT EXISTS FOR (p:Program) ON (p.name)",
            "CREATE INDEX course_title_idx   IF NOT EXISTS FOR (c:Course)  ON (c.title)",
            "CREATE INDEX course_credits_idx IF NOT EXISTS FOR (c:Course)  ON (c.credits)",
        ]

        for q in SCHEMA:
            try:
                session.run(q)
                print(f"  ✅ {q[:72]}...")
            except Exception as e:
                print(f"  ⚠️  {e}")

    driver.close()
    print("\n🎉 Schema reset complete! Now run:")
    print("   python step4_neo4j_loader.py")


if __name__ == "__main__":
    main()
