python -c "
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
URI = os.getenv('NEO4J_URI')
USER = os.getenv('NEO4J_USER')
PWD = os.getenv('NEO4J_PWD')

driver = GraphDatabase.driver(URI, auth=(USER, PWD))
with driver.session() as session:
    result = session.run('SHOW CONSTRAINTS')
    print('Current Constraints:')
    for record in result:
        name = record.get('name')
        print(f' - {name}')
        # Drop legacy single-field constraints if found
        if name in ['program_url_unique', 'program_name_unique', 'course_code_unique', 'school_name_unique']:
            session.run(f'DROP CONSTRAINT {name}')
            print(f'   ❌ Dropped legacy constraint: {name}')

driver.close()
print('\n✅ Constraint cleanup done!')
"
