# step1b_cleanup.py
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI      = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PWD")

CLEANUP_QUERIES = [
    # Drop the failed constraint if it partially exists
    "DROP CONSTRAINT course_node_key IF EXISTS",

    # Wipe ALL existing nodes and relationships
    "MATCH (n) DETACH DELETE n",
]

def run_query(tx, query):
    tx.run(query)

def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("✅ Connected\n")

    with driver.session() as session:
        for q in CLEANUP_QUERIES:
            try:
                session.execute_write(run_query, q)
                print(f"  ✅ {q[:60]}")
            except Exception as e:
                print(f"  ⚠️  {e}")

    driver.close()
    print("\n🧹 Database wiped clean!")

if __name__ == "__main__":
    main()