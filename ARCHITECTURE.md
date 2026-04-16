# AI Enterprise Agent: System Architecture

## 1. Architecture Overview
The AI Enterprise Agent is a sophisticated e-commerce ecosystem that bridges the gap between structured data (Neo4j, PostgreSQL) and unstructured web content (Chroma DB). To ensure enterprise-grade speed and safety, the architecture incorporates a high-speed Semantic Cache and strict AI Guardrails.

### System Architecture Flow
1. **User Input** → React Frontend
2. **Security Layer** → Input Guardrails (Safety & Relevance check)
3. **Fast Path** → Semantic Cache (ChromaDB) → *If Hit, return instant response.*
4. **Intelligent Core (If Cache Miss)** → LangGraph Agent (GPT-4o-mini)
5. **Background Processes** → Scraper Runner → Data Layer
6. **Data Layer** → Neo4j (Product Graph), ChromaDB (Vector Search & Cache), PostgreSQL (Operations)

### Core Technology Stack
* **Orchestration:** LangGraph (State Machine Agent)
* **API Layer:** FastAPI (Asynchronous Python)
* **Frontend:** React 18 (Vite, Tailwind CSS)
* **Graph DB (Neo4j):** Product hierarchies, specs, and relationships
* **Vector DB (Chroma):** Semantic embeddings for RAG and Semantic Response Caching
* **Relational DB (PostgreSQL):** ACID-compliant storage for Users, Inventory, and Orders
* **Safety & Compliance:** Custom Guardrails for input sanitization and output verification

---

## 2. Backend & Agent Logic
The backend centers on a LangGraph state machine that manages the reasoning cycle. 

### LangGraph Workflow
* **Input Guardrails:** Evaluates the user's raw input to block malicious prompts or unsafe requests.
* **Rewrite:** Formulates a standalone search query based on Redis chat history.
* **Semantic Cache Check:** Compares the standalone query against a ChromaDB cache using a strict similarity threshold (0.85). If a semantic match is found, the system bypasses the LLM and instantly returns the cached response.
* **Intent Router:** Classifies intent into: `graph_db`, `vector_db`, `order_action`, or `general_chat`.
* **Tool Execution:**
  * `query_neo4j`: Retrieves precise technical specs.
  * `query_vector`: Fetches company context/social sentiment.
  * `prepare_order`: Verifies inventory in PostgreSQL and triggers the UI form signal.
* **Synthesis:** Combines data into a natural language response.
* **Output Guardrails:** Verifies the synthesized response to ensure no hallucinations.
* **Cache Update:** Saves the successfully validated standalone query and its final answer to the Semantic Cache.

---

## 3. Frontend & Intelligent UI
The React-based interface is designed for "Contextual Commerce," where the UI reacts to the Agent's reasoning.

* **Message Interception:** The UI scans for signals like `[SHOW_ORDER_FORM]` to render interactive components directly in the chat thread.
* **Product Canvas:** A side-panel that visualizes product specs and live pricing automatically.
* **Admin Dashboard:** A separate route for CRUD operations on products and order status management.

---

## 4. Database Schema
The system uses a Tri-Database Architecture to manage different data types efficiently.

### 1. PostgreSQL (Business & Transactions)
Handles structured data requiring ACID compliance.
* `customers`: User profiles and authentication.
* `products`: Master inventory list (SKU, name, base_price, stock_level).
* `orders`: Transaction records (Pending, Shipped, Delivered).
* `order_items`: Junction table for line items and historical prices.

### 2. Neo4j (Product Graph)
Maps complex relationships and technical hierarchies.
* **Nodes:** `(:Product)`, `(:Category)`, `(:Specification)`
* **Relationships:** `[:BELONGS_TO]`, `[:HAS_SPEC]`, `[:COMPATIBLE_WITH]`

### 3. Chroma DB (Knowledge & Cache Vector Store)
* **Collection 1: `slt_knowledge_base`**
  * *Data Points:* Fragments of text from Website, LinkedIn, TikTok.
* **Collection 2: `semantic_response_cache`**
  * *Data Points:* Standalone user queries and validated AI-generated responses.

---

## 5. Ingestion Pipeline & Data Sync Flow
A unified pipeline (`main_scraper.py`) synchronizes all databases.

1. **Extraction:** Scrapes Website, LinkedIn, and TikTok.
2. **Structural Mapping:** Converts product tables into Cypher queries for Neo4j.
3. **Vectorization:** Fragments text and generates embeddings for Chroma DB.
4. **Inventory Sync:** Populates PostgreSQL with master SKU and stock data.
5. **Cache Invalidation:** Performs a physical reset of the ChromaDB Semantic Cache folder during data ingestion to ensure users never receive stale data.

---

## 6. Specific Models & Technical Logic
* **Main Reasoning Engine:** OpenAI's `gpt-4o-mini`.
* **Embedding Model:** OpenAI's `text-embedding-3-small`.
* **Guardrails:** OpenAI Moderation API.
* **Redis:** Used as a lightning-fast, temporary storage for the chat history (`RedisChatMessageHistory`) with a 24-hour TTL to prevent memory bloating.