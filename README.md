# AI-Enterprise-Agent

AI-powered enterprise assistant for knowledge and product intelligence. It combines a Neo4j graph database for structured product data with a Chroma DB vector store for unstructured web content, all orchestrated by a LangGraph agent.

---

## 🚀 Option 1: Docker 

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