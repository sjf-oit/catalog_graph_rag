# step1_schema_setup.py
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# --- Load credentials from .env ---
load_dotenv()
URI      = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PWD")

SCHEMA_QUERIES = [
    # --- Uniqueness Constraints ---
    "CREATE CONSTRAINT catalog_year_unique IF NOT EXISTS FOR (c:CatalogYear) REQUIRE c.year IS UNIQUE",
    "CREATE CONSTRAINT level_name_unique   IF NOT EXISTS FOR (l:Level)       REQUIRE l.name IS UNIQUE",
    "CREATE CONSTRAINT program_url_unique  IF NOT EXISTS FOR (p:Program)     REQUIRE p.url  IS UNIQUE",

    # --- Node Key Constraints (composite) ---
    "CREATE CONSTRAINT school_node_key IF NOT EXISTS FOR (s:School) REQUIRE (s.name, s.catalog_year) IS NODE KEY",
    "CREATE CONSTRAINT course_node_key IF NOT EXISTS FOR (c:Course) REQUIRE (c.code, c.catalog_year) IS NODE KEY",
    "CREATE CONSTRAINT req_group_key   IF NOT EXISTS FOR (r:RequirementGroup) REQUIRE (r.name, r.program_url, r.catalog_year) IS NODE KEY",

    # --- Indexes ---
    "CREATE INDEX program_name_idx   IF NOT EXISTS FOR (p:Program) ON (p.name)",
    "CREATE INDEX course_title_idx   IF NOT EXISTS FOR (c:Course)  ON (c.title)",
    "CREATE INDEX course_credits_idx IF NOT EXISTS FOR (c:Course)  ON (c.credits)",
]

def run_query(tx, query):
    tx.run(query)

def main():
    print(f"🔌 Connecting to {URI} as '{USERNAME}'...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

    # Verify connectivity before proceeding
    driver.verify_connectivity()
    print("✅ Connection successful!\n")

    with driver.session() as session:
        for q in SCHEMA_QUERIES:
            try:
                session.execute_write(run_query, q)
                print(f"  ✅ {q[:72]}...")
            except Exception as e:
                print(f"  ⚠️  Skipped: {e}")

    driver.close()
    print("\n🎉 Schema setup complete! Ready for Step 2.")

if __name__ == "__main__":
    main()