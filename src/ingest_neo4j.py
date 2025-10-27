import os
import csv
from neo4j import GraphDatabase

# neo4j connection details
NEO4J_URI = "neo4j+s://a48ace4f.databases.neo4j.io"

NEO4J_USER = "neo4j"

NEO4J_PASSWORD = "mIH7T8grFTv7RqaYh1xUIW2Rf8NWjY743b656OruI7g"

script_dir = os.path.dirname(__file__)

CSV_FILE = os.path.join(script_dir, '..', 'data', 'products.csv')

class Neo4jIngestor:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print("Successfully connected to Neo4j Aura.")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        self.driver.close()
        print("Closed Neo4j connection.")

    def setup_constraints(self):
        """Create unique constraints to avoid duplicates and speed up queries."""
        with self.driver.session(database="neo4j") as session:
            print("Creating constraints...")
            session.run("""
                CREATE CONSTRAINT IF NOT EXISTS FOR (c:Category)
                REQUIRE c.name IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product)
                REQUIRE p.sku IS UNIQUE
            """)
            print("Constraints created.")

    def clear_database(self):
        """Clear all nodes and relationships."""
        with self.driver.session(database="neo4j") as session:
            print("Clearing database...")
            session.run("MATCH (n) DETACH DELETE n")
            print("Database cleared.")

    def ingest_data(self, csv_file_path):
        """Read CSV and create nodes and relationships."""
        print(f"Starting ingestion from {csv_file_path}...")

        ingest_query = """
        MERGE (c:Category {name: $row.category_name})
        MERGE (p:Product {sku: $row.sku})
        ON CREATE SET
            p.name = $row.product_name,
            p.price = toFloat($row.price)
        MERGE (p)-[:IN_CATEGORY]->(c)
        """

        count = 0
        with self.driver.session(database="neo4j") as session:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    session.run(ingest_query, row=row)
                    count += 1

        print(f"Ingestion complete. Processed {count} rows.")

# Main execution 
if __name__ == "__main__":
    try:
        ingestor = Neo4jIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

        ingestor.clear_database() 
        ingestor.setup_constraints()
        ingestor.ingest_data(CSV_FILE)

    except Exception as e:
        print(f"An error occurred during the process: {e}")
    finally:
        if 'ingestor' in locals() and ingestor.driver:
            ingestor.close()