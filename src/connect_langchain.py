import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_URI or not NEO4J_USER or not NEO4J_PASSWORD:
    raise ValueError(
        "Missing Neo4j credentials. "
        "Please check the .env file."
    )

print("Credentials loaded successfully.")

try:
    print("Connecting to Neo4j database via LangChain...")
    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD
    )
    print("Connection successful.")

    print("\nFetching graph schema...")
    schema = graph.get_schema
    
    print("--- Graph Schema ---")
    print(schema)
    print("--------------------")

except Exception as e:
    print(f"An error occurred: {e}")