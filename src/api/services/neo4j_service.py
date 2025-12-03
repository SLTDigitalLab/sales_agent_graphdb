import os
import csv
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up 3 levels to get to the main project folder (from src/api/services/)
PROJECT_ROOT = os.path.join(script_dir, '..', '..', '..') 
# POINT TO THE SCRAPERS FOLDER
CSV_FILE = os.path.join(PROJECT_ROOT, 'products.csv')

# Debug print to verify path
print(f"Neo4j Service will look for CSV at: {os.path.abspath(CSV_FILE)}")

# Initialize Neo4j connections
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Initialize Neo4j graph connection with error handling
try:
    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD
    )
    graph.refresh_schema()
    print("Neo4j schema refreshed for service.")
    
    # Define QA chain
    QA_TEMPLATE_TEXT = """
    You are an assistant that helps to form nice and human-readable answers...
    **IMPORTANT:** All prices are in Sri Lankan Rupees (Rs.)...
    Information:
    {context}
    Question: {question}
    Helpful Answer:
    """
    QA_PROMPT = PromptTemplate(input_variables=["context", "question"], template=QA_TEMPLATE_TEXT)

    # Custom Cypher Generation Prompt 
    CYPHER_GENERATION_TEMPLATE = """
    You are an expert Cypher query generator. Your goal is to create flexible, case-insensitive queries.
    Given a graph schema and a user question, create a Cypher query to retrieve the information.

    **Querying Rules:**
    1.  **Always use `CONTAINS` for string matching.**
    2.  **Always be case-insensitive.** Use `toLower()` on both property and search term.
    
    **Example for a CATEGORY:**
    Question: "what are my options for security cameras?"
    Cypher: `MATCH (p:Product)-[:IN_CATEGORY]->(c:Category) WHERE toLower(c.name) CONTAINS toLower('security camera') RETURN p.name, p.price, p.url`

    **Example for a PRODUCT:**
    Question: "how much is the prolink ds-3103"
    Cypher: `MATCH (p:Product) WHERE toLower(p.name) CONTAINS toLower('prolink ds-3103') RETURN p.price`

    Schema:
    {schema}

    Question: {question}
    Cypher Query:
    """
    CYPHER_PROMPT = PromptTemplate(input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE)

    neo4j_qa_chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        allow_dangerous_requests=True,
        qa_prompt=QA_PROMPT,
        cypher_prompt=CYPHER_PROMPT
    )
    print("Neo4j QA Chain service initialized.")
    neo4j_available = True
except Exception as e:
    print(f"Error initializing Neo4j connection: {e}")
    print("Neo4j service will be unavailable until connection is restored.")
    neo4j_available = False
    neo4j_qa_chain = None

# Define ingestion logic
class Neo4jIngestor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()
    def close(self):
        self.driver.close()
    def setup_constraints(self):
        with self.driver.session(database="neo4j") as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.sku IS UNIQUE")
    def clear_database(self):
        with self.driver.session(database="neo4j") as session:
            session.run("MATCH (n) DETACH DELETE n")
    def ingest_data(self, csv_file_path):
        # UPDATED QUERY: Now saves the URL as well
        ingest_query = """
        MERGE (c:Category {name: $row.category_name})
        MERGE (p:Product {sku: $row.sku})
        ON CREATE SET 
            p.name = $row.product_name, 
            p.price = toFloat($row.price),
            p.url = $row.url
        MERGE (p)-[:IN_CATEGORY]->(c)
        """
        count = 0
        with self.driver.session(database="neo4j") as session:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    session.run(ingest_query, row=row)
                    count += 1
        return count

# Define service functions
def run_graph_query(question: str) -> str:
    """Runs the QA chain for a given question."""
    print(f"Neo4j Service: Received query: {question}")
    
    if not neo4j_available or neo4j_qa_chain is None:
        return "Error: Neo4j database is currently unavailable. Please try again later."
    
    try:
        result = neo4j_qa_chain.invoke({"query": question})
        return result.get('result', "Error: No result found.")
    except Exception as e:
        print(f"Error during Neo4j query: {e}")
        return f"Error: {str(e)}"

# Fixed: Removed unused 'source' argument to avoid errors
def run_neo4j_ingestion() -> int:
    """Clears and re-loads the Neo4j database."""
    print("Neo4j Service: Received ingestion request.")
    ingestor = None
    try:
        ingestor = Neo4jIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        print("Clearing Neo4j database...")
        ingestor.clear_database()
        print("Setting up constraints...")
        ingestor.setup_constraints()
        print(f"Ingesting data from {CSV_FILE}...")
        processed_count = ingestor.ingest_data(CSV_FILE)
        print(f"Neo4j ingestion complete. Processed {processed_count} rows.")
        return processed_count
    finally:
        if ingestor:
            ingestor.close()

print("Neo4j Service file loaded.")