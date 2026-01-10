import os
import csv
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(script_dir, '..', '..', '..') 
CSV_FILE = os.path.join(PROJECT_ROOT, 'products.csv')

# Initialize variables GLOBALLY first 
graph = None
neo4j_qa_chain = None
neo4j_available = False

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

try:
    logger.info(f"Attempting to connect to Neo4j at {NEO4J_URI}...")
    
    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD
    )
    graph.refresh_schema()
    logger.info("Neo4j schema refreshed for service.")
    
    # --- 1. QA PROMPT ---
    QA_TEMPLATE_TEXT = """
    You are a helpful AI sales assistant for SLT Lifestore.
    Use the provided context to answer the user's question.

    **CRITICAL RULES FOR LINKS:**
    1. **NEVER invent a URL.** Only use URLs provided in the context.
    2. If a product has a URL, format it as: [Product Name](Actual URL) - Rs. Price
    3. If no URL exists, just list the name and price.
    4. Do NOT use 'example.com'.

    Information:
    {context}
    
    Question: {question}
    Helpful Answer:
    """
    QA_PROMPT = PromptTemplate(input_variables=["context", "question"], template=QA_TEMPLATE_TEXT)

    # --- 2. UPDATED CYPHER PROMPT ---
    CYPHER_GENERATION_TEMPLATE = """
    You are an expert Cypher query generator.
    
    **Schema:**
    Node types: (:Product), (:Category)
    Properties: Product(name, price, url, sku), Category(name)
    
    **Indexes:** 'product_name_index' on (:Product).name

    **SEARCH RULES (CRITICAL):**
    1. **Specific Search:** If the user asks for a specific item (e.g. "Router", "Camera"), use fuzzy search:
       `CALL db.index.fulltext.queryNodes("product_name_index", "term~") YIELD node AS p RETURN p.name, p.price, p.url LIMIT 10`
    
    2. **Broad/Reset Search:** If the user asks "What **other** products do you have?", "What **else** do you sell?", or "List **all** products", you MUST ignore previous specific filters.
       Use a broad match: 
       `MATCH (p:Product) RETURN p.name, p.price, p.url LIMIT 10`
    
    3. **Category Exclusion:** If the user says "Products other than routers":
       `MATCH (p:Product) WHERE NOT toLower(p.name) CONTAINS 'router' RETURN p.name, p.price, p.url LIMIT 10`

    4. **Return Fields:** Always return `p.name`, `p.price`, and `p.url`.

    **Examples:**
    Q: "Do you have routers?"
    Cypher: CALL db.index.fulltext.queryNodes("product_name_index", "router~") YIELD node AS p RETURN p.name, p.price, p.url LIMIT 10

    Q: "What else do you sell?" (User wants to see NON-routers now)
    Cypher: MATCH (p:Product) RETURN p.name, p.price, p.url LIMIT 10

    Q: "{question}"
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
    logger.info("Neo4j QA Chain service initialized.")
    neo4j_available = True

except Exception as e:
    logger.warning(f"Neo4j connection failed. The app will run without Graph features.")
    logger.error(f"Error details: {e}", exc_info=True)
    neo4j_available = False

class Neo4jIngestor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()
    def close(self):
        self.driver.close()
    
    def setup_constraints(self):
        with self.driver.session(database="neo4j") as session:
            # 1. Unique Constraints
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.sku IS UNIQUE")
            
            logger.info("Creating Fulltext Search Index on Product Names...")
            session.run("CREATE FULLTEXT INDEX product_name_index IF NOT EXISTS FOR (p:Product) ON EACH [p.name]")

    def clear_database(self):
        with self.driver.session(database="neo4j") as session:
            session.run("MATCH (n) DETACH DELETE n")
            
    def ingest_data(self, csv_file_path):
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
            logger.info(f"Reading from: {csv_file_path}") 
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    session.run(ingest_query, row=row)
                    count += 1
        return count

def run_graph_query(question: str) -> str:
    """Runs the QA chain for a given question."""
    if not neo4j_available or neo4j_qa_chain is None:
        return "Sorry, product database is currently unavailable (Connection Error)."
    try:
        result = neo4j_qa_chain.invoke({"query": question})
        return result.get('result', "Error: No result found.")
    except Exception as e:
        logger.error(f"Error running graph query: {e}", exc_info=True)
        return f"Error: {str(e)}"

def run_neo4j_ingestion() -> int:
    """Clears and re-loads the Neo4j database."""
    logger.info("Neo4j Service: Received ingestion request.")
    
    ingestor = None
    try:
        ingestor = Neo4jIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        logger.info("Clearing Neo4j database...")
        ingestor.clear_database()
        
        logger.info("Setting up constraints & indexes...")
        ingestor.setup_constraints()
        
        logger.info(f"Ingesting data from {CSV_FILE}...")
        if not os.path.exists(CSV_FILE):
             logger.error(f"CSV file not found at {CSV_FILE}")
             return 0

        processed_count = ingestor.ingest_data(CSV_FILE)
        logger.info(f"Neo4j ingestion complete. Processed {processed_count} rows.")
        
        if graph:
            logger.info("Refreshing Graph Schema for LLM...")
            graph.refresh_schema()
            logger.info("Schema Refreshed!")
        else:
            logger.warning("Skipping Schema refresh because 'graph' object is not initialized.")

        return processed_count
    finally:
        if ingestor:
            ingestor.close()

def run_clear_neo4j() -> str:
    """
    Connects to Neo4j and deletes all data.
    """
    logger.info("Neo4j Service: Received CLEAR request.")
    ingestor = None
    try:
        ingestor = Neo4jIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        ingestor.clear_database()
        
        if graph:
             graph.refresh_schema()
             
        return "Graph database cleared successfully."
    except Exception as e:
        logger.error(f"Error clearing Neo4j: {e}", exc_info=True)
        raise e
    finally:
        if ingestor:
            ingestor.close()

logger.info("Neo4j Service file loaded.")