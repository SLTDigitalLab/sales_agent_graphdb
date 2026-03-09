# AI-Enterprise-Agent

An intelligent e-commerce ecosystem powered by a LangGraph agent. It synchronizes Neo4j (product hierarchies), Chroma DB (multi-channel web context), and PostgreSQL (business operations) to deliver automated product intelligence and guided ordering.

✨ Core Features
1. Data Intelligence & Ingestion
Multi-Source Scraper: Automated extraction of product specs from target websites.
Knowledge Graph (Neo4j): Structured ingestion of product relationships and hierarchies.
Social RAG (Chroma DB): Vector indexing of Web, LinkedIn, and TikTok content for company context.

2. Conversational E-Commerce
Product Discovery: AI-driven queries for product details and comparisons.
Company Insights: Real-time answers regarding company background and social presence.
Guided Ordering: Seamless chat-to-order flow with automated intent detection.

3. Order & User Management
Secure Auth: Integrated registration and sign-in system for customers.
Relational Storage (PostgreSQL): Management of users, inventory, and order history.
Smart Notifications: Dual-email triggers for both customer and company upon order.

4. Admin Command Center
Inventory CRUD: Tools to add, update, or delete products in the catalog.
Order Oversight: Centralized dashboard to monitor all incoming customer orders.
Status Control: Live tracking and updating of order progress (e.g., Pending to Shipped).

---

## 🚀 Option 1: Docker (Recommended)

This is the easiest way to run the application. It guarantees the environment works exactly as intended without installing dependencies locally.

### 1. Prerequisites
* **Docker Desktop** (Installed and running).
* **Git**.

### 2. Setup & Run
1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd AI-Enterprise-Agent
    ```

2.  **Configure Environment Variables:**
    * Create a file named `.env` in the **root folder** with API keys, etc.

3.  **Launch the App:**
    Run the following command in the project root:
    ```bash
    docker-compose up
    ```
    *(This may take a few minutes the first time to build the images).*

### 3. Access the Application
Once the logs settle, the application is live:

* **Chat Interface:** [http://localhost:3000](http://localhost:3000)
* **Admin Dashboard:** [http://localhost:3000/admin](http://localhost:3000/admin)
* **Backend API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Stopping the App
Press `Ctrl+C` in the terminal, or run:
```bash
docker-compose down
```

## 🚀 Option 2: Manual Setup 


### 1. Prerequisites

* **Python:** Requires **Python 3.10 or newer**. 

### 2. Environment Setup

1.  **Clone the repository**

2.  **Create and activate a virtual environment:**
    ```bash
    # Create the environment
    python -m venv venv

    # Activate on macOS/Linux
    source venv/bin/activate

    # Activate on Windows
    .venv\Scripts\activate
    ```

3.  **Install all required packages:**
    Use the `requirements.txt` file to install the exact versions of all dependencies for the project.
    ```bash
    pip install -r requirements.txt
    ```
## Execution 

Once the environment is set up, follow these steps to run the application:

4.  **Run the backend server:**
    Start the main application backend, which houses the LangGraph agent and API services.
    ```bash
    uvicorn src.main:api --reload --port 8000
    ```
    The backend API and Swagger UI will be available at `http://localhost:8000`.

5.  **Access the Admin Dashboard:**
    Acess the Admin Dashboard to controll scraping and data ingection.
    
    The Admin Dashboard will be available at `http://localhost:5173/admin`.
    
6.  **Run the chat application:**
    Navigate to the `frontend` directory and start the development server.
    ```bash
    cd frontend
    npm install 
    npm run dev
    ```
    The frontend will typically be available at **http://localhost:5173**.