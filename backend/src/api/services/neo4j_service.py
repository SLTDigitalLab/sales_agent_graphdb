import os
import csv
from sqlalchemy import text
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# IMPORT LOGGER
from src.utils.logging_config import get_logger

# IMPORT SQL DATABASE (For seeding)
from src.api.db.sessions import SessionLocal
from src.api.db.models import Product, Order, OrderItem

logger = get_logger(__name__)

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- PATH FIX ---
# Current file: /app/src/api/services/neo4j_service.py
# We want: /app/data/products.csv
current_dir = os.path.dirname(os.path.abspath(__file__)) # services
api_dir = os.path.dirname(current_dir)                    # api
src_dir = os.path.dirname(api_dir)                        # src
app_dir = os.path.dirname(src_dir)                        # app (Project Root)

CSV_PATH = os.path.join(app_dir, 'data', 'products.csv')

# Initialize variables
graph = None
neo4j_qa_chain = None
neo4j_available = False
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

try:
    logger.info(f"Attempting to connect to Neo4j at {NEO4J_URI}...")
    graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASSWORD)
    graph.refresh_schema()
    
    # --- PROMPTS ---
    QA_TEMPLATE_TEXT = """
    You are a helpful AI sales assistant for SLT Lifestore.
    Use the provided context to answer the user's question.
    **CRITICAL RULES FOR LINKS:**
    1. **NEVER invent a URL.** Only use URLs provided in the context.
    2. If a product has a URL, format it as: [Product Name](Actual URL) - Rs. Price
    3. If no URL exists, just list the name and price.
    Information:
    {context}
    Question: {question}
    Helpful Answer:
    """
    QA_PROMPT = PromptTemplate(input_variables=["context", "question"], template=QA_TEMPLATE_TEXT)

    CYPHER_GENERATION_TEMPLATE = """
    You are an expert Cypher query generator.
    **Schema:**
    Node types: (:Product), (:Category)
    Properties: Product(name, price, url, sku, image_url), Category(name)
    **Indexes:** 'product_name_index' on (:Product).name
    **SEARCH RULES:**
    1. Specific: `CALL db.index.fulltext.queryNodes("product_name_index", "term~") YIELD node AS p RETURN p.name, p.price, p.url LIMIT 10`
    2. Broad: `MATCH (p:Product) RETURN p.name, p.price, p.url LIMIT 10`
    3. Return Fields: Always return `p.name`, `p.price`, and `p.url`.
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
    neo4j_available = True
    logger.info("Neo4j Service Initialized.")

except Exception as e:
    logger.warning(f"Neo4j connection failed: {e}")
    neo4j_available = False

class Neo4jIngestor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    def close(self):
        self.driver.close()
    
    def setup_constraints(self):
        with self.driver.session(database="neo4j") as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.sku IS UNIQUE")
            session.run("CREATE FULLTEXT INDEX product_name_index IF NOT EXISTS FOR (p:Product) ON EACH [p.name]")

    def clear_database(self):
        with self.driver.session(database="neo4j") as session:
            session.run("MATCH (n) DETACH DELETE n")
            
    def ingest_csv(self, file_path):
        if not os.path.exists(file_path):
            logger.error(f"CSV not found at {file_path}")
            return 0

        ingest_query = """
        MERGE (c:Category {name: $category})
        MERGE (p:Product {sku: $sku})
        ON CREATE SET 
            p.name = $name, 
            p.price = toFloat($price),
            p.url = $url,
            p.image_url = $image_url
        MERGE (p)-[:IN_CATEGORY]->(c)
        """
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            with self.driver.session(database="neo4j") as session:
                for row in reader:
                    try:
                        params = {
                            "category": row.get('category_name', 'Uncategorized'),
                            "sku": row['sku'],
                            "name": row['product_name'],
                            "price": float(row.get('price', 0)),
                            "url": row.get('url', ''),
                            "image_url": row.get('image_url', '')
                        }
                        session.run(ingest_query, **params)
                        count += 1
                    except Exception as e:
                        logger.error(f"Neo4j Row Error: {e}")
        return count

def seed_sql_db(file_path):
    """
    Wipes and Reseeds the PostgreSQL Database from the CSV.
    Uses TRUNCATE ... RESTART IDENTITY to reset IDs to 1.
    """
    logger.info("SQL: Starting Wipe & Reseed...")
    if not os.path.exists(file_path):
        logger.error(f"SQL: CSV file missing at {file_path}")
        return 0

    db = SessionLocal()
    try:
        # 1. Wipe Data (Cascade deletes orders)
        logger.info("SQL: Truncating tables...")
        db.execute(text("TRUNCATE TABLE order_items, orders, products RESTART IDENTITY CASCADE"))
        
        # 2. Seed Data
        logger.info("SQL: Seeding from CSV...")
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                product = Product(
                    sku=row['sku'],
                    name=row['product_name'],
                    price=float(row.get('price', 0)),
                    category=row.get('category_name'),
                    product_url=row.get('url'),
                    image_url=row.get('image_url'),
                    description=row.get('description'),
                    stock_quantity=50 # Default stock
                )
                db.add(product)
                count += 1
        
        db.commit()
        logger.info(f"SQL: Successfully seeded {count} products.")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"SQL Seed Failed: {e}")
        raise e
    finally:
        db.close()

def run_master_ingestion() -> dict:
    """
    MASTER SYNC FUNCTION:
    1. Reads products.csv
    2. Wipes & Seeds SQL (Supabase)
    3. Wipes & Seeds Neo4j (AuraDB)
    """
    logger.info("--- STARTING MASTER DATA INGESTION ---")
    logger.info(f"Looking for CSV at: {CSV_PATH}")
    
    if not os.path.exists(CSV_PATH):
        return {"error": f"products.csv not found at {CSV_PATH}. Run scraper first."}

    stats = {"sql_added": 0, "neo4j_added": 0}

    # Step 1: SQL Sync
    try:
        stats["sql_added"] = seed_sql_db(CSV_PATH)
    except Exception as e:
        return {"error": f"SQL Sync failed: {str(e)}"}

    # Step 2: Neo4j Sync
    ingestor = None
    try:
        ingestor = Neo4jIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        ingestor.clear_database()
        ingestor.setup_constraints()
        stats["neo4j_added"] = ingestor.ingest_csv(CSV_PATH)
        
        if graph: graph.refresh_schema()
        
    except Exception as e:
        return {"error": f"Neo4j Sync failed: {str(e)}", "partial_stats": stats}
    finally:
        if ingestor: ingestor.close()

    logger.info("--- MASTER INGESTION COMPLETE ---")
    return stats

# Helper for QA
def run_graph_query(question: str) -> str:
    if not neo4j_available: return "Graph DB unavailable."
    try:
        return neo4j_qa_chain.invoke({"query": question}).get('result', "No result.")
    except Exception as e:
        return f"Error: {str(e)}"