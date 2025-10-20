from neo4j import GraphDatabase

def seed_neo4j():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "test"  # your chosen Neo4j password
    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        # Clear previous data
        session.run("MATCH (n) DETACH DELETE n")

        # Create users
        session.run("CREATE (:User {name:'alice'})")
        session.run("CREATE (:User {name:'bob'})")

        # Create authors
        session.run("CREATE (:Author {name:'Jane Doe'})")
        session.run("CREATE (:Author {name:'John Writer'})")

        # Create books and relationships
        session.run("""
            CREATE (b1:Book {id:'mongo_001', title:'Free Book 1'})
            CREATE (b2:Book {id:'mongo_002', title:'Premium Book 1'})
            WITH b1, b2
            MATCH (a1:Author {name:'Jane Doe'}), (a2:Author {name:'John Writer'}),
                  (u1:User {name:'alice'}), (u2:User {name:'bob'})
            CREATE (b1)-[:WRITTEN_BY]->(a1)
            CREATE (b2)-[:WRITTEN_BY]->(a2)
            CREATE (u1)-[:READ]->(b1)
            CREATE (u2)-[:READ]->(b2)
        """)

    driver.close()
    print("✅ Neo4j seeded successfully with demo data.")

if __name__ == "__main__":
    seed_neo4j()
